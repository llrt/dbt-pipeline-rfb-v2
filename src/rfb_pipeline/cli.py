"""CLI de linha de comando do pipeline RFB/CNPJ.

`rfb ingerir` liga cliente WebDAV/BD, conversão e manifesto (T10). `rfb sincronizar` publica
raw/gold no S3/Tigris (T11). `rfb relatorio` gera o relatório do estudo de caso (T27).
`rfb pipeline` (T28) e `rfb atualizar` (T36) orquestram tudo (ver `orquestracao.py`).
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import time
from datetime import UTC, date, datetime
from pathlib import Path

import httpx

from rfb_pipeline.armazenamento import sincronizar
from rfb_pipeline.basedosdados import baixar_tabelas_bd
from rfb_pipeline.cliente_rfb import ArquivoRemoto, ClienteRFB
from rfb_pipeline.configuracao import Configuracao, carregar_configuracao
from rfb_pipeline.conversao import converter_entidade_rfb, converter_tabela_bd
from rfb_pipeline.erros import ErroIngestao, MesIncompletoErro, MesInexistenteErro
from rfb_pipeline.esquemas import (
    ENTIDADES_RFB,
    TABELAS_BD,
    EntidadeRFB,
    arquivos_faltantes,
    entidade_do_zip,
)
from rfb_pipeline.manifesto import (
    ArquivoManifesto,
    Manifesto,
    escrever_manifesto,
    ler_manifesto,
    precisa_reconverter,
    sha256_arquivo,
    trava_execucao,
)
from rfb_pipeline.orquestracao import (
    OpcoesPipeline,
    atualizar,
    executar_pipeline,
    verificar_gold_consistente,
)
from rfb_pipeline.publicacao import publicar_motherduck
from rfb_pipeline.relatorio import SAIDA_PADRAO, gerar_relatorio

_RE_MES = re.compile(r"^\d{4}-\d{2}$")


# ---------------------------------------------------------------------------- ingerir


def _aviso(mensagem: str) -> None:
    print(f"aviso: {mensagem}", file=sys.stderr)


def _limpar_residuos(configuracao: Configuracao) -> None:
    """Remove resíduos de execuções interrompidas. Só chamar com a trava de execução."""
    residuos: list[Path] = []
    if configuracao.raw_dir.is_dir():
        for padrao in (".tmp-*", ".old-*"):
            residuos.extend(configuracao.raw_dir.rglob(padrao))
    if configuracao.manifestos_dir.is_dir():
        residuos.extend(configuracao.manifestos_dir.glob(".tmp-*"))
    tmp_dir = configuracao.raiz_dados / "_tmp"
    if tmp_dir.is_dir():
        residuos.extend(tmp_dir.glob("extracao-*"))
    for residuo in residuos:
        if residuo.is_dir():
            shutil.rmtree(residuo, ignore_errors=True)
        else:
            residuo.unlink(missing_ok=True)


def _meses_disponiveis_local(origem_local: Path) -> list[str]:
    pasta = origem_local / "rfb"
    if not pasta.is_dir():
        return []
    return sorted(p.name for p in pasta.iterdir() if p.is_dir() and _RE_MES.match(p.name))


def _nomes_do_mes(mes: str, cliente: ClienteRFB | None, origem_local: Path | None) -> list[str]:
    if origem_local is not None:
        pasta = origem_local / "rfb" / mes
        return sorted(p.name for p in pasta.glob("*.zip"))
    return [a.nome for a in cliente.listar_arquivos(mes)]


def _resolver_mes(
    mes: str | None,
    cliente: ClienteRFB | None,
    origem_local: Path | None,
    *,
    permitir_incompleto: bool = False,
) -> str:
    """Escolhe o mês a ingerir, exigindo mês completo (ADR-0012) salvo `permitir_incompleto`.

    Sem `mes`: o mais recente **completo**, avisando os incompletos mais novos que foram ignorados
    (com `permitir_incompleto`, o mais recente, completo ou não). Com `mes`: falha listando os
    arquivos faltantes se ele estiver incompleto.
    """
    disponiveis = (
        _meses_disponiveis_local(origem_local)
        if origem_local is not None
        else cliente.listar_meses()
    )
    if mes is not None:
        if mes not in disponiveis:
            raise MesInexistenteErro(mes, disponiveis)
        faltantes = arquivos_faltantes(_nomes_do_mes(mes, cliente, origem_local))
        if faltantes and not permitir_incompleto:
            raise MesIncompletoErro(mes, faltantes)
        if faltantes:
            _aviso(f"mês {mes} incompleto (faltam {len(faltantes)} arquivo(s)); prosseguindo")
        return mes
    if not disponiveis:
        raise MesInexistenteErro("(mais recente)", disponiveis)
    if permitir_incompleto:
        return disponiveis[-1]
    ignorados: list[tuple[str, list[str]]] = []
    for candidato in reversed(disponiveis):
        faltantes = arquivos_faltantes(_nomes_do_mes(candidato, cliente, origem_local))
        if not faltantes:
            if ignorados:
                _aviso(
                    "meses incompletos ignorados: "
                    + ", ".join(f"{m} (faltam {len(f)})" for m, f in ignorados)
                    + f"; usando {candidato}"
                )
            return candidato
        ignorados.append((candidato, faltantes))
    raise MesIncompletoErro(*ignorados[0])


def _zips_locais_entidade(origem_local: Path, mes: str, entidade: EntidadeRFB) -> list[Path]:
    pasta = origem_local / "rfb" / mes
    return sorted(p for p in pasta.glob("*.zip") if entidade.padrao_zip.match(p.name))


def _baixar_entidades_remoto(
    cliente: ClienteRFB, mes: str, destino_dir: Path
) -> dict[str, list[Path]]:
    """Baixa os zips do mês (só entidades de `ENTIDADES_RFB`, nunca `Socios*`).

    Reaproveita um zip já baixado se o tamanho em disco confere com o anunciado pelo WebDAV.
    """
    por_entidade: dict[str, list[Path]] = {}
    for arquivo in cliente.listar_arquivos(mes):
        entidade = entidade_do_zip(arquivo.nome)
        if entidade is None:
            continue
        destino = destino_dir / arquivo.nome
        if (
            arquivo.tamanho is not None
            and destino.exists()
            and destino.stat().st_size == arquivo.tamanho
        ):
            caminho = destino
        else:
            caminho = cliente.baixar(mes, ArquivoRemoto(arquivo.nome, arquivo.tamanho), destino_dir)
        por_entidade.setdefault(entidade.nome, []).append(caminho)
    return por_entidade


def ingerir(
    configuracao: Configuracao,
    *,
    mes: str | None = None,
    origem_local: Path | None = None,
    forcar: bool = False,
    ingerido_em: datetime | None = None,
    permitir_incompleto: bool = False,
) -> Manifesto:
    """Executa a ingestão completa (RFB + Base dos Dados) e grava o manifesto do mês.

    Levanta `ErroIngestao` (ou subclasses) em qualquer falha; nesse caso a partição anterior de
    cada entidade permanece intacta e nada é gravado para as entidades ainda não convertidas. O
    manifesto é regravado a cada entidade concluída (`concluido_em` fica nulo até o fim). Uma
    segunda execução simultânea falha com "execução em andamento" (trava em `_estado/rfb.lock`).
    """
    with trava_execucao(configuracao):
        _limpar_residuos(configuracao)
        return _ingerir(
            configuracao,
            mes=mes,
            origem_local=origem_local,
            forcar=forcar,
            ingerido_em=ingerido_em,
            permitir_incompleto=permitir_incompleto,
        )


def _ingerir(
    configuracao: Configuracao,
    *,
    mes: str | None,
    origem_local: Path | None,
    forcar: bool,
    ingerido_em: datetime | None,
    permitir_incompleto: bool,
) -> Manifesto:
    ingerido_em = ingerido_em or datetime.now(UTC)

    cliente = ClienteRFB(configuracao) if origem_local is None else None
    mes_resolvido = _resolver_mes(
        mes, cliente, origem_local, permitir_incompleto=permitir_incompleto
    )

    manifesto_anterior = ler_manifesto(configuracao, mes_resolvido)
    data_referencia: date | None = None
    if manifesto_anterior is not None and manifesto_anterior.data_referencia:
        data_referencia = date.fromisoformat(manifesto_anterior.data_referencia)

    remotos_por_entidade: dict[str, list[Path]] | None = None
    if origem_local is None:
        remotos_por_entidade = _baixar_entidades_remoto(
            cliente, mes_resolvido, configuracao.baixados_dir(mes_resolvido)
        )

    entradas: list[ArquivoManifesto] = []
    pendentes = list(ENTIDADES_RFB)

    def _gravar_parcial() -> None:
        # entidades ainda não processadas mantêm as entradas do manifesto anterior
        herdadas = (
            [a for a in manifesto_anterior.arquivos if a.entidade in pendentes]
            if manifesto_anterior is not None
            else []
        )
        escrever_manifesto(
            configuracao,
            Manifesto(
                mes_referencia=mes_resolvido,
                data_referencia=data_referencia.isoformat() if data_referencia else None,
                iniciado_em=ingerido_em.isoformat(),
                concluido_em=None,
                arquivos=tuple(entradas + herdadas),
            ),
        )

    for entidade in ENTIDADES_RFB.values():
        inicio = time.monotonic()
        if origem_local is not None:
            zips = _zips_locais_entidade(origem_local, mes_resolvido, entidade)
        else:
            zips = remotos_por_entidade.get(entidade.nome, [])
        if not zips:
            raise ErroIngestao(
                f"nenhum zip encontrado para a entidade {entidade.nome!r} no mês {mes_resolvido!r}"
            )

        zips_atuais = [(p.name, p.stat().st_size, sha256_arquivo(p)) for p in zips]

        if not precisa_reconverter(
            configuracao,
            manifesto_anterior,
            entidade.nome,
            mes_resolvido,
            zips_atuais,
            forcar=forcar,
        ):
            reaproveitadas = manifesto_anterior.arquivos_da_entidade(entidade.nome)
            entradas.extend(reaproveitadas)
            linhas = sum(a.linhas_gravadas for a in reaproveitadas)
            rejeitadas = sum(a.linhas_rejeitadas for a in reaproveitadas)
            print(
                f"{entidade.nome}: pulada (sem mudanças) - {linhas} linhas, "
                f"{rejeitadas} rejeitadas, {time.monotonic() - inicio:.1f}s"
            )
            pendentes.remove(entidade.nome)
            continue

        resultados = converter_entidade_rfb(
            zips, entidade, mes_resolvido, configuracao, ingerido_em=ingerido_em
        )
        bytes_por_nome = {nome: b for nome, b, _ in zips_atuais}
        sha256_por_nome = {nome: s for nome, _, s in zips_atuais}
        for resultado in resultados:
            if resultado.data_referencia is not None:
                data_referencia = resultado.data_referencia
            else:
                _aviso(
                    f"{resultado.arquivo_origem}: sem data de referência no nome interno "
                    f"({resultado.arquivo_interno}); _data_referencia ficou NULL"
                )
            entradas.append(
                ArquivoManifesto(
                    nome=resultado.arquivo_origem,
                    bytes=bytes_por_nome[resultado.arquivo_origem],
                    sha256=sha256_por_nome[resultado.arquivo_origem],
                    entidade=resultado.entidade,
                    linhas_lidas=resultado.linhas + resultado.linhas_rejeitadas,
                    linhas_rejeitadas=resultado.linhas_rejeitadas,
                    parquet=tuple(
                        str(p.relative_to(configuracao.raiz_dados)) for p in resultado.parquet
                    ),
                )
            )
        linhas = sum(r.linhas for r in resultados)
        rejeitadas = sum(r.linhas_rejeitadas for r in resultados)
        print(
            f"{entidade.nome}: {linhas} linhas, {rejeitadas} rejeitadas, "
            f"{time.monotonic() - inicio:.1f}s"
        )
        pendentes.remove(entidade.nome)
        _gravar_parcial()

    if data_referencia is None:
        _aviso("nenhuma data de referência obtida; data_referencia do manifesto é nula")

    destino_bd = configuracao.baixados_dir(mes_resolvido) / "bd"
    caminhos_bd = baixar_tabelas_bd(configuracao, destino_bd, origem_local=origem_local)
    for nome_tabela, tabela in TABELAS_BD.items():
        inicio = time.monotonic()
        resultado = converter_tabela_bd(
            caminhos_bd[nome_tabela], tabela, configuracao, ingerido_em=ingerido_em
        )
        print(f"bd.{nome_tabela}: {resultado.linhas} linhas, {time.monotonic() - inicio:.1f}s")

    manifesto = Manifesto(
        mes_referencia=mes_resolvido,
        data_referencia=data_referencia.isoformat() if data_referencia else None,
        iniciado_em=ingerido_em.isoformat(),
        concluido_em=datetime.now(UTC).isoformat(),
        arquivos=tuple(entradas),
    )
    escrever_manifesto(configuracao, manifesto)
    return manifesto


def _cmd_ingerir(argumentos: argparse.Namespace) -> int:
    configuracao = carregar_configuracao()
    ingerir(
        configuracao,
        mes=argumentos.mes,
        origem_local=argumentos.origem_local,
        forcar=argumentos.forcar,
        permitir_incompleto=argumentos.permitir_incompleto,
    )
    return 0


def _cmd_sincronizar(_argumentos: argparse.Namespace) -> int:
    configuracao = carregar_configuracao()
    enviados = sincronizar(configuracao)
    for chave in enviados:
        print(f"enviado: {chave}")
    print(f"{len(enviados)} objeto(s) enviado(s)")
    return 0


def _cmd_publicar(argumentos: argparse.Namespace) -> int:
    configuracao = carregar_configuracao()
    tabelas = (
        [t.strip() for t in argumentos.tabelas.split(",") if t.strip()]
        if argumentos.tabelas
        else None
    )
    verificar_gold_consistente(configuracao, "publicar")  # R4-03
    publicar_motherduck(configuracao, tabelas=tabelas)
    return 0


def _opcoes_pipeline(argumentos: argparse.Namespace) -> OpcoesPipeline:
    return OpcoesPipeline(
        origem_local=argumentos.origem_local,
        permitir_incompleto=argumentos.permitir_incompleto,
        forcar=argumentos.forcar,
        ingerir=not getattr(argumentos, "sem_ingestao", False),
        target=argumentos.target,
        saida_relatorio=None if argumentos.sem_relatorio else argumentos.saida_relatorio,
        publicar=not argumentos.sem_publicar,
    )


def _cmd_pipeline(argumentos: argparse.Namespace) -> int:
    configuracao = carregar_configuracao()
    for mes in argumentos.mes or []:
        if not _RE_MES.match(mes):
            raise ErroIngestao(f"--mes inválido: {mes!r} (formato AAAA-MM)")
    executar_pipeline(configuracao, argumentos.mes, _opcoes_pipeline(argumentos))
    return 0


def _cmd_atualizar(argumentos: argparse.Namespace) -> int:
    configuracao = carregar_configuracao()
    atualizar(configuracao, _opcoes_pipeline(argumentos))
    return 0


def _cmd_relatorio(argumentos: argparse.Namespace) -> int:
    configuracao = carregar_configuracao()
    verificar_gold_consistente(configuracao, "relatorio")  # R4-03
    saida = gerar_relatorio(configuracao, saida=argumentos.saida, target=argumentos.target)
    print(f"relatório escrito em {saida}")
    return 0


def _argumentos_orquestracao(analisador: argparse.ArgumentParser) -> None:
    analisador.add_argument(
        "--origem-local",
        dest="origem_local",
        type=Path,
        default=None,
        help="Usa fixtures locais em vez da rede (layout <dir>/rfb, <dir>/bd).",
    )
    analisador.add_argument(
        "--permitir-incompleto",
        dest="permitir_incompleto",
        action="store_true",
        help="Aceita mês sem todos os arquivos esperados.",
    )
    analisador.add_argument(
        "--forcar", action="store_true", help="Reconverte mesmo se o manifesto não mudou."
    )
    analisador.add_argument(
        "--target", default=None, help="Target dbt (padrão: o do profile; `s3` com s3://)."
    )
    analisador.add_argument(
        "--saida-relatorio",
        dest="saida_relatorio",
        type=Path,
        default=SAIDA_PADRAO,
        help="Arquivo Markdown do relatório (padrão: docs/RELATORIO_ESTUDO_CASO.md).",
    )
    analisador.add_argument(
        "--sem-relatorio", dest="sem_relatorio", action="store_true", help="Não gera o relatório."
    )
    analisador.add_argument(
        "--sem-publicar",
        dest="sem_publicar",
        action="store_true",
        help="Não publica no MotherDuck mesmo se configurado.",
    )


def _construir_analisador() -> argparse.ArgumentParser:
    analisador = argparse.ArgumentParser(
        prog="rfb",
        description="Pipeline ELT RFB/CNPJ (dbt + DuckDB).",
    )
    sub = analisador.add_subparsers(dest="comando", required=True)

    p_ingerir = sub.add_parser("ingerir", help="Ingesta os dados RFB/BD para a camada raw.")
    p_ingerir.add_argument("--mes", default=None, help="Mês YYYY-MM (padrão: o mais recente).")
    p_ingerir.add_argument(
        "--origem-local",
        dest="origem_local",
        type=Path,
        default=None,
        help="Usa fixtures locais em vez de baixar da rede (layout <dir>/rfb, <dir>/bd).",
    )
    p_ingerir.add_argument(
        "--forcar", action="store_true", help="Reconverte mesmo se o manifesto não mudou."
    )
    p_ingerir.add_argument(
        "--permitir-incompleto",
        dest="permitir_incompleto",
        action="store_true",
        help="Aceita mês sem todos os arquivos esperados (Empresas0-9, Estabelecimentos0-9, ...).",
    )
    p_ingerir.set_defaults(func=_cmd_ingerir)

    p_sincronizar = sub.add_parser(
        "sincronizar", help="Sincroniza raw/ e gold/ a S3 (não implementado)."
    )
    p_sincronizar.set_defaults(func=_cmd_sincronizar)

    p_publicar = sub.add_parser(
        "publicar",
        help="Publica o gold no MotherDuck (só com MOTHERDUCK_TOKEN e MOTHERDUCK_BANCO).",
    )
    p_publicar.add_argument(
        "--destino", choices=["motherduck"], required=True, help="Destino da publicação."
    )
    p_publicar.add_argument(
        "--tabelas",
        default=None,
        help="Lista separada por vírgulas (padrão: todas as tabelas do gold).",
    )
    p_publicar.set_defaults(func=_cmd_publicar)

    p_pipeline = sub.add_parser(
        "pipeline",
        help="Ponta a ponta: ingestão, freshness, dbt build, relatório, publicação (T28).",
        description=(
            "Processa os meses do mais antigo ao mais novo. Um mês anterior ao gold corrente "
            "(_estado/ultima_execucao.json) roda como backfill: só a partição dele em "
            "gold/fct_resumo_mensal é gravada no gold."
        ),
    )
    p_pipeline.add_argument(
        "--mes",
        action="append",
        default=None,
        help="Mês AAAA-MM (repetível; padrão: o mais recente completo).",
    )
    p_pipeline.add_argument(
        "--sem-ingestao",
        dest="sem_ingestao",
        action="store_true",
        help="Usa o raw já presente em RAIZ_DADOS (exige --mes).",
    )
    _argumentos_orquestracao(p_pipeline)
    p_pipeline.set_defaults(func=_cmd_pipeline)

    p_atualizar = sub.add_parser(
        "atualizar",
        help="Atualização mensal: processa o mês completo mais recente se for novo (T36).",
        description=(
            "Compara o mês completo mais recente da origem com _estado/ultima_execucao.json; se "
            "for novo roda o pipeline e aplica a retenção (RFB_MESES_RETIDOS, RFB_MANTER_ZIPS); "
            "senão imprime 'nenhum mês novo' e sai com 0 sem baixar nada."
        ),
    )
    _argumentos_orquestracao(p_atualizar)
    p_atualizar.set_defaults(func=_cmd_atualizar)

    p_relatorio = sub.add_parser(
        "relatorio", help="Gera o relatório do estudo de caso (docs/RELATORIO_ESTUDO_CASO.md)."
    )
    p_relatorio.add_argument(
        "--saida", type=Path, default=SAIDA_PADRAO, help="Arquivo Markdown de saída."
    )
    p_relatorio.add_argument(
        "--target", default=None, help="Target dbt das analyses (padrão: o do profile)."
    )
    p_relatorio.set_defaults(func=_cmd_relatorio)

    return analisador


def main(argv: list[str] | None = None) -> int:
    argumentos = _construir_analisador().parse_args(argv)
    try:
        codigo = argumentos.func(argumentos)
    except ErroIngestao as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except httpx.HTTPError as exc:  # rede escapando dos clientes: sem traceback, com a URL
        try:
            url = str(exc.request.url)
        except RuntimeError:
            url = "(URL desconhecida)"
        print(f"erro de rede em {url}: {exc}", file=sys.stderr)
        return 1
    return codigo if codigo is not None else 0


if __name__ == "__main__":
    sys.exit(main())
