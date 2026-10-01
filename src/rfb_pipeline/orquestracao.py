"""Orquestração ponta a ponta: `rfb pipeline` (T28) e `rfb atualizar` (T36, ADR-0012).

Um mês passa por: ingestão -> (`sincronizar` do raw, se `s3://`) -> `dbt source freshness` ->
`dbt build --vars mes_referencia` -> relatório -> publicação no MotherDuck (se configurada) ->
estado em `RAIZ_DADOS/_estado/ultima_execucao.json`. O estado é gravado **só** quando todas as
etapas terminam bem, e é ele que diz qual mês está no gold "corrente".

Ordem dos meses (P22): o build de um mês regrava os marts `external` de `gold/` (dimensões, fatos,
marts), então um mês **mais antigo** que o do estado roda como *backfill*: os externals vão para um
`external_root` temporário, o `.duckdb` é temporário, a partição do mês de `fct_resumo_mensal` é
gravada noutra raiz temporária (`RFB_RAIZ_SERIE`) e, só depois de todos os testes de
`+fct_resumo_mensal` passarem, é movida para `gold/fct_resumo_mensal/` (R4-02). Vários meses numa
chamada são processados do mais antigo ao mais novo.

Gold misto (R4-03): os marts `external` são regravados um a um durante o `dbt build` do mês
corrente; se ele falhar no meio, parte do gold fica no mês novo e parte no antigo. O marcador
`_estado/em_andamento.json` é gravado antes do build e apagado só quando ele termina bem; enquanto
existir, `rfb relatorio` e `rfb publicar` recusam rodar (`verificar_gold_consistente`).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from rfb_pipeline.armazenamento import sincronizar
from rfb_pipeline.configuracao import Configuracao
from rfb_pipeline.erros import ErroIngestao
from rfb_pipeline.manifesto import trava_execucao
from rfb_pipeline.publicacao import ler_destino_motherduck, publicar_motherduck
from rfb_pipeline.relatorio import DIR_TRANSFORM, SAIDA_PADRAO, gerar_relatorio

ARQUIVO_ESTADO = Path("_estado") / "ultima_execucao.json"
ARQUIVO_EM_ANDAMENTO = Path("_estado") / "em_andamento.json"
SELETOR_BACKFILL = "backfill_resumo_mensal"
DATASET_SERIE = "fct_resumo_mensal"

# (argumentos do dbt, ambiente) -> código de saída. Injetável para testes sem dbt.
ExecutorDbt = Callable[[Sequence[str], Mapping[str, str]], int]


class PipelineErro(ErroIngestao):
    """Uma etapa do pipeline falhou (dbt, relatório, publicação)."""


@dataclass(frozen=True)
class Estado:
    """Último mês processado com sucesso por `rfb pipeline`/`rfb atualizar` (gold corrente)."""

    mes_referencia: str
    data_referencia: str | None
    concluido_em: str


@dataclass
class OpcoesPipeline:
    origem_local: Path | None = None
    permitir_incompleto: bool = False
    forcar: bool = False
    ingerir: bool = True
    target: str | None = None
    saida_relatorio: Path | None = SAIDA_PADRAO  # None = sem relatório
    publicar: bool = True


@dataclass
class ResultadoMes:
    mes_referencia: str
    modo: str  # "corrente" | "backfill" (durante a ingestão, ainda "ingestão")
    tempos_s: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------- estado


def ler_estado(configuracao: Configuracao) -> Estado | None:
    caminho = configuracao.raiz_dados / ARQUIVO_ESTADO
    if not caminho.is_file():
        return None
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        return Estado(
            mes_referencia=dados["mes_referencia"],
            data_referencia=dados.get("data_referencia"),
            concluido_em=dados["concluido_em"],
        )
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ErroIngestao(f"estado inválido em {caminho}: {exc}") from None


def gravar_estado(configuracao: Configuracao, estado: Estado) -> Path:
    """Grava o estado atomicamente (temp + rename)."""
    destino = configuracao.raiz_dados / ARQUIVO_ESTADO
    _gravar_json_atomico(destino, asdict(estado))
    return destino


# ---------------------------------------------------------------- gold em andamento (R4-03)


def _gravar_json_atomico(destino: Path, dados: dict) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(f".tmp-{destino.name}-{uuid.uuid4().hex}")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(destino)


def marcar_em_andamento(configuracao: Configuracao, mes: str) -> Path:
    """Marca o gold como em reconstrução (antes do `dbt build` do mês corrente)."""
    destino = configuracao.raiz_dados / ARQUIVO_EM_ANDAMENTO
    _gravar_json_atomico(
        destino, {"mes_referencia": mes, "iniciado_em": datetime.now(UTC).isoformat()}
    )
    return destino


def desmarcar_em_andamento(configuracao: Configuracao) -> None:
    (configuracao.raiz_dados / ARQUIVO_EM_ANDAMENTO).unlink(missing_ok=True)


def verificar_gold_consistente(configuracao: Configuracao, comando: str) -> None:
    """Recusa `rfb <comando>` enquanto um build do mês corrente não terminou bem (R4-03)."""
    marcador = configuracao.raiz_dados / ARQUIVO_EM_ANDAMENTO
    if not marcador.is_file():
        return
    try:
        mes = json.loads(marcador.read_text(encoding="utf-8")).get("mes_referencia", "?")
    except (json.JSONDecodeError, AttributeError):
        mes = "?"
    raise ErroIngestao(
        f"rfb {comando} recusado: o gold pode estar misto (o build de {mes} começou e não "
        f"terminou bem; marcador {marcador}). Rode `rfb pipeline --mes {mes}` de novo até concluir "
        '(ver docs/OPERACAO.md, "Gold misto")'
    )


# ---------------------------------------------------------------------------- dbt


def _executavel_dbt() -> str:
    ao_lado = Path(sys.executable).parent / "dbt"
    if ao_lado.is_file():
        return str(ao_lado)
    encontrado = shutil.which("dbt")
    if encontrado:
        return encontrado
    raise PipelineErro("executável `dbt` não encontrado; rode `make setup`")


def executar_dbt(argumentos: Sequence[str], ambiente: Mapping[str, str]) -> int:
    """Roda o dbt em `transform/`, com a saída no terminal (logs completos do dbt)."""
    comando = [_executavel_dbt(), *argumentos]
    print("$ dbt " + " ".join(argumentos), flush=True)
    return subprocess.run(comando, cwd=DIR_TRANSFORM, env=dict(ambiente), check=False).returncode


def _ambiente_dbt(configuracao: Configuracao, **extras: str) -> dict[str, str]:
    ambiente = {
        **os.environ,
        "RAIZ_DADOS": configuracao.raiz_dados_uri,
        "DBT_PROFILES_DIR": os.environ.get("DBT_PROFILES_DIR", str(DIR_TRANSFORM)),
    }
    if configuracao.raiz_dados_s3 is not None:
        ambiente["RAIZ_DADOS_LOCAL"] = str(configuracao.raiz_dados)
    ambiente.update(extras)
    return ambiente


def _target(configuracao: Configuracao, opcoes: OpcoesPipeline) -> list[str]:
    if opcoes.target:
        return ["--target", opcoes.target]
    if configuracao.raiz_dados_s3 is not None:
        return ["--target", "s3"]
    return []


def _vars(mes: str) -> list[str]:
    return ["--vars", json.dumps({"mes_referencia": mes})]


def _dbt_ou_falha(executor: ExecutorDbt, etapa: str, argumentos: list[str], ambiente) -> None:
    codigo = executor(argumentos, ambiente)
    if codigo != 0:
        raise PipelineErro(f"etapa {etapa!r} falhou (dbt saiu com código {codigo})")


# ---------------------------------------------------------------------------- pipeline


class _Cronometro:
    def __init__(self, resultado: ResultadoMes) -> None:
        self.resultado = resultado

    def medir(self, etapa: str, funcao: Callable[[], object]) -> object:
        mes, modo = self.resultado.mes_referencia, self.resultado.modo
        print(f"== {mes} [{modo}] etapa: {etapa}", flush=True)
        inicio = time.monotonic()
        try:
            return funcao()
        finally:
            duracao = time.monotonic() - inicio
            self.resultado.tempos_s[etapa] = round(duracao, 1)
            print(f"== etapa {etapa}: {duracao:.1f}s", flush=True)


def _ingerir_mes(configuracao: Configuracao, mes: str | None, opcoes: OpcoesPipeline) -> str:
    from rfb_pipeline.cli import ingerir  # import tardio: cli importa este módulo

    manifesto = ingerir(
        configuracao,
        mes=mes,
        origem_local=opcoes.origem_local,
        forcar=opcoes.forcar,
        permitir_incompleto=opcoes.permitir_incompleto,
    )
    return manifesto.mes_referencia


def _data_referencia_do_manifesto(configuracao: Configuracao, mes: str) -> str | None:
    from rfb_pipeline.manifesto import ler_manifesto

    manifesto = ler_manifesto(configuracao, mes)
    return manifesto.data_referencia if manifesto is not None else None


def _processar_corrente(
    configuracao: Configuracao,
    mes: str,
    opcoes: OpcoesPipeline,
    executor: ExecutorDbt,
    cron: _Cronometro,
) -> None:
    if configuracao.raiz_dados_s3 is None:
        # o COPY do DuckDB não cria o diretório de destino dos marts (P11)
        configuracao.gold_dir.mkdir(parents=True, exist_ok=True)
    ambiente = _ambiente_dbt(configuracao)
    target = _target(configuracao, opcoes)
    cron.medir(
        "freshness",
        lambda: _dbt_ou_falha(executor, "freshness", ["source", "freshness", *target], ambiente),
    )
    # R4-03: um build que falha no meio deixa o gold misto; o marcador só sai no sucesso
    marcar_em_andamento(configuracao, mes)
    cron.medir(
        "dbt_build",
        lambda: _dbt_ou_falha(executor, "dbt build", ["build", *target, *_vars(mes)], ambiente),
    )
    desmarcar_em_andamento(configuracao)
    if opcoes.saida_relatorio is not None:
        saida = opcoes.saida_relatorio
        cron.medir(
            "relatorio",
            lambda: gerar_relatorio(configuracao, saida=saida, target=opcoes.target),
        )
        print(f"relatório escrito em {saida}")
    if opcoes.publicar:
        cron.medir("publicar", lambda: _publicar_se_configurado(configuracao))
    gravar_estado(
        configuracao,
        Estado(
            mes_referencia=mes,
            data_referencia=_data_referencia_do_manifesto(configuracao, mes),
            concluido_em=datetime.now(UTC).isoformat(),
        ),
    )


def _processar_backfill(
    configuracao: Configuracao,
    mes: str,
    opcoes: OpcoesPipeline,
    executor: ExecutorDbt,
    cron: _Cronometro,
) -> None:
    """Mês mais antigo que o gold corrente: só a partição de `fct_resumo_mensal` vai ao gold.

    R4-02: o build roda com os testes de `+fct_resumo_mensal` (seletor `backfill_resumo_mensal`) e
    grava a partição em `RFB_RAIZ_SERIE` (temporária); ela só é movida para o gold depois do build
    terminar bem. Uma falha deixa a partição do gold como estava.
    """
    temporario = configuracao.raiz_dados / "_tmp" / f"backfill-{mes}-{uuid.uuid4().hex[:8]}"
    serie = temporario / "serie"
    (temporario / "gold").mkdir(parents=True, exist_ok=True)
    serie.mkdir(parents=True, exist_ok=True)
    configuracao.gold_dir.mkdir(parents=True, exist_ok=True)
    ambiente = _ambiente_dbt(
        configuracao,
        RFB_EXTERNAL_ROOT=str(temporario / "gold"),
        RFB_RAIZ_SERIE=str(serie),
        CAMINHO_DUCKDB=str(temporario / "warehouse.duckdb"),
    )
    # target-path próprio: o `transform/target/run_results.json` continua sendo o do mês corrente
    comuns = [*_target(configuracao, opcoes), *_vars(mes), "--target-path", str(temporario / "t")]
    try:
        cron.medir(
            "dbt_build_backfill",
            lambda: _dbt_ou_falha(
                executor, "dbt build (backfill)",
                ["build", "--selector", SELETOR_BACKFILL, *comuns], ambiente,
            ),
        )  # fmt: skip
        cron.medir("mover_particao", lambda: _mover_particao_ao_gold(configuracao, serie, mes))
    finally:
        shutil.rmtree(temporario, ignore_errors=True)
    if configuracao.raiz_dados_s3 is not None:
        cron.medir("sincronizar_particao", lambda: sincronizar(configuracao))
    if opcoes.publicar:
        cron.medir("publicar", lambda: _publicar_se_configurado(configuracao, [DATASET_SERIE]))


def _mover_particao_ao_gold(configuracao: Configuracao, serie: Path, mes: str) -> Path:
    """Troca `gold/fct_resumo_mensal/mes_referencia=<mês>` pela partição testada do backfill.

    Dois `rename` no mesmo disco (a raiz temporária fica em `RAIZ_DADOS/_tmp`): a partição antiga
    sai para o temporário e a nova entra no lugar. No modo `s3://` o destino é a cópia local do
    gold, enviada ao bucket em seguida pelo `sincronizar`.
    """
    nome = f"mes_referencia={mes}"
    nova = serie / DATASET_SERIE / nome
    if not any(nova.glob("*.parquet")):
        raise PipelineErro(
            f"backfill de {mes}: o dbt terminou sem gravar a partição em {nova} (esperada em "
            "RFB_RAIZ_SERIE; ver `raiz_serie` em fct_resumo_mensal)"
        )
    destino = configuracao.gold_dir / DATASET_SERIE / nome
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        shutil.move(destino, serie / f".anterior-{nome}")
    shutil.move(nova, destino)  # `rename` no mesmo disco
    print(f"partição {nome} movida para {destino}")
    return destino


def _publicar_se_configurado(configuracao: Configuracao, tabelas: list[str] | None = None) -> None:
    """Publica no MotherDuck só com `MOTHERDUCK_TOKEN`+`MOTHERDUCK_BANCO` (P25)."""
    if ler_destino_motherduck() is None:
        print("MotherDuck não configurado; nada publicado")
        return
    if configuracao.raiz_dados_s3 is not None:
        print("aviso: RAIZ_DADOS é s3://; publicação no MotherDuck pulada (lê o gold local)")
        return
    verificar_gold_consistente(configuracao, "publicar")
    publicar_motherduck(configuracao, tabelas=tabelas)


def executar_pipeline(
    configuracao: Configuracao,
    meses: Sequence[str] | None,
    opcoes: OpcoesPipeline,
    *,
    executor: ExecutorDbt | None = None,
) -> list[ResultadoMes]:
    """Processa os `meses` do mais antigo ao mais novo (P22); `None` = o mais recente completo.

    Cada mês mais antigo que o do estado roda como backfill. Levanta `ErroIngestao` (ou
    `PipelineErro`) na primeira falha, sem gravar estado para o mês que falhou.
    """
    if not meses and not opcoes.ingerir:
        raise PipelineErro("sem ingestão é preciso informar --mes")
    executor = executor or executar_dbt
    resultados: list[ResultadoMes] = []
    with trava_execucao(configuracao, "pipeline.lock"):
        fila: list[str | None] = sorted(set(meses)) if meses else [None]
        for pedido in fila:
            resultado = ResultadoMes(mes_referencia=pedido or "(mais recente)", modo="ingestão")
            cron = _Cronometro(resultado)
            mes = pedido
            if opcoes.ingerir:
                mes = cron.medir("ingestao", lambda p=pedido: _ingerir_mes(configuracao, p, opcoes))
                resultado.mes_referencia = mes
            if configuracao.raiz_dados_s3 is not None:
                cron.medir("sincronizar", lambda: sincronizar(configuracao))
            estado = ler_estado(configuracao)
            backfill = estado is not None and mes < estado.mes_referencia
            resultado.modo = "backfill" if backfill else "corrente"
            if backfill:
                print(
                    f"{mes} é anterior ao gold corrente ({estado.mes_referencia}): backfill "
                    "(só a partição de fct_resumo_mensal vai ao gold)"
                )
                _processar_backfill(configuracao, mes, opcoes, executor, cron)
            else:
                _processar_corrente(configuracao, mes, opcoes, executor, cron)
            total = sum(resultado.tempos_s.values())
            etapas = ", ".join(f"{k}={v:.1f}s" for k, v in resultado.tempos_s.items())
            print(f"pipeline {mes} [{resultado.modo}] concluído em {total:.1f}s ({etapas})")
            resultados.append(resultado)
    return resultados


# ---------------------------------------------------------------------------- atualizar


def aplicar_retencao(configuracao: Configuracao, mes_processado: str) -> list[Path]:
    """Mantém as partições raw dos `meses_retidos` meses mais recentes e apaga zips (ADR-0012).

    Apaga `_baixados/<mês>` do mês processado (salvo `manter_zips`) e de todo mês fora da janela.
    Devolve o que foi removido.
    """
    raiz_rfb = configuracao.raw_dir / "rfb"
    particoes = sorted(raiz_rfb.glob("*/mes_referencia=*")) if raiz_rfb.is_dir() else []
    meses = sorted({p.name.removeprefix("mes_referencia=") for p in particoes})
    retidos = set(meses[-configuracao.meses_retidos :])
    removidos: list[Path] = []
    for particao in particoes:
        if particao.name.removeprefix("mes_referencia=") not in retidos:
            shutil.rmtree(particao)
            removidos.append(particao)
    baixados = configuracao.raiz_dados / "_baixados"
    if baixados.is_dir():
        for pasta in sorted(baixados.iterdir()):
            fora_da_janela = pasta.name not in retidos
            processado = pasta.name == mes_processado and not configuracao.manter_zips
            if pasta.is_dir() and (fora_da_janela or processado):
                shutil.rmtree(pasta)
                removidos.append(pasta)
    for caminho in removidos:
        print(f"retenção: removido {caminho}")
    return removidos


def mes_mais_recente_completo(
    configuracao: Configuracao, origem_local: Path | None, permitir_incompleto: bool
) -> str:
    """Mês completo mais recente da origem (só listagem; nada é baixado)."""
    from rfb_pipeline.cli import _resolver_mes
    from rfb_pipeline.cliente_rfb import ClienteRFB

    cliente = ClienteRFB(configuracao) if origem_local is None else None
    return _resolver_mes(None, cliente, origem_local, permitir_incompleto=permitir_incompleto)


def atualizar(
    configuracao: Configuracao,
    opcoes: OpcoesPipeline,
    *,
    executor: ExecutorDbt | None = None,
) -> ResultadoMes | None:
    """Processa o mês completo mais recente se for mais novo que o estado; senão é no-op."""
    estado = ler_estado(configuracao)
    mes = mes_mais_recente_completo(configuracao, opcoes.origem_local, opcoes.permitir_incompleto)
    if estado is not None and mes <= estado.mes_referencia:
        print(f"nenhum mês novo (mais recente completo: {mes}; último processado: "
              f"{estado.mes_referencia})")  # fmt: skip
        return None
    print(f"mês novo: {mes} (último processado: "
          f"{estado.mes_referencia if estado else 'nenhum'})")  # fmt: skip
    (resultado,) = executar_pipeline(configuracao, [mes], opcoes, executor=executor)
    aplicar_retencao(configuracao, mes)
    return resultado
