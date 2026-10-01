"""`rfb pipeline` (T28) e `rfb atualizar` (T36): ordem, backfill, estado, no-op e retenção.

O dbt é substituído por um executor falso (registra os comandos) e a ingestão por um stub; a
integração com dbt real roda no `make ci` (`tests/integration/test_atualizar.py`).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from rfb_pipeline import cli, orquestracao
from rfb_pipeline.configuracao import Configuracao, carregar_configuracao
from rfb_pipeline.erros import ErroIngestao, MesIncompletoErro
from rfb_pipeline.esquemas import ARQUIVOS_ESPERADOS_MES
from rfb_pipeline.orquestracao import (
    Estado,
    OpcoesPipeline,
    PipelineErro,
    aplicar_retencao,
    atualizar,
    executar_pipeline,
    gravar_estado,
    ler_estado,
)


class ExecutorFalso:
    """Registra cada chamada ao dbt; falha (código 1) se o 1º argumento estiver em `falhar`."""

    def __init__(self, falhar: Sequence[str] = ()) -> None:
        self.chamadas: list[tuple[list[str], dict[str, str]]] = []
        self.falhar = set(falhar)

    def __call__(self, argumentos: Sequence[str], ambiente: Mapping[str, str]) -> int:
        self.chamadas.append((list(argumentos), dict(ambiente)))
        if argumentos[0] in self.falhar:
            return 1
        if "RFB_RAIZ_SERIE" in ambiente and argumentos[0] == "build":
            # como o dbt: o backfill grava a partição do resumo em `RFB_RAIZ_SERIE`
            mes = json.loads(argumentos[argumentos.index("--vars") + 1])["mes_referencia"]
            pasta = Path(ambiente["RFB_RAIZ_SERIE"]) / "fct_resumo_mensal" / f"mes_referencia={mes}"
            pasta.mkdir(parents=True)
            (pasta / "data_0.parquet").write_text(f"novo {mes}")
        return 0

    @property
    def comandos(self) -> list[list[str]]:
        return [a for a, _ in self.chamadas]

    def meses(self) -> list[str]:
        return [
            json.loads(a[a.index("--vars") + 1])["mes_referencia"]
            for a in self.comandos
            if "--vars" in a and a[0] in {"build"}
        ]


@pytest.fixture(autouse=True)
def _sem_motherduck(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MOTHERDUCK_TOKEN", raising=False)
    monkeypatch.delenv("MOTHERDUCK_BANCO", raising=False)


@pytest.fixture
def ingeridos(monkeypatch: pytest.MonkeyPatch) -> list[str | None]:
    """Substitui a ingestão: registra o mês pedido e devolve-o (ou 2026-09 se nenhum)."""
    pedidos: list[str | None] = []

    def _stub(_configuracao: Configuracao, mes: str | None, _opcoes: OpcoesPipeline) -> str:
        pedidos.append(mes)
        return mes or "2026-09"

    monkeypatch.setattr(orquestracao, "_ingerir_mes", _stub)
    return pedidos


def _config(tmp_path: Path, **env: str) -> Configuracao:
    return carregar_configuracao({"RAIZ_DADOS": str(tmp_path / "dados"), **env})


def _opcoes(**kw) -> OpcoesPipeline:
    return OpcoesPipeline(saida_relatorio=None, **kw)


# ---------------------------------------------------------------------------- pipeline


def test_mes_corrente_roda_freshness_e_build_com_o_mes_e_grava_estado(
    tmp_path: Path, ingeridos: list
) -> None:
    configuracao = _config(tmp_path)
    executor = ExecutorFalso()
    (resultado,) = executar_pipeline(configuracao, ["2026-09"], _opcoes(), executor=executor)
    assert executor.comandos == [
        ["source", "freshness"],
        ["build", "--vars", '{"mes_referencia": "2026-09"}'],
    ]
    assert resultado.modo == "corrente"
    assert set(resultado.tempos_s) >= {"ingestao", "freshness", "dbt_build", "publicar"}
    assert ler_estado(configuracao).mes_referencia == "2026-09"
    assert configuracao.gold_dir.is_dir()  # P11: o COPY do DuckDB não cria gold/
    _, ambiente = executor.chamadas[0]
    assert ambiente["RAIZ_DADOS"] == str(configuracao.raiz_dados)
    assert "RFB_EXTERNAL_ROOT" not in ambiente


@pytest.mark.parametrize("etapa", ["source", "build"])
def test_falha_do_dbt_sai_com_erro_e_nao_grava_estado(
    tmp_path: Path, ingeridos: list, etapa: str
) -> None:
    configuracao = _config(tmp_path)
    gravar_estado(configuracao, Estado("2026-08", None, "x"))
    executor = ExecutorFalso(falhar=[etapa])
    with pytest.raises(PipelineErro, match="falhou"):
        executar_pipeline(configuracao, ["2026-09"], _opcoes(), executor=executor)
    assert ler_estado(configuracao).mes_referencia == "2026-08"
    if etapa == "source":  # freshness com erro: não chega ao build
        assert [c[0] for c in executor.comandos] == ["source"]


def test_meses_sao_processados_do_mais_antigo_ao_mais_novo(tmp_path: Path, ingeridos: list) -> None:
    configuracao = _config(tmp_path)
    executor = ExecutorFalso()
    resultados = executar_pipeline(
        configuracao, ["2026-09", "2026-08"], _opcoes(), executor=executor
    )
    assert ingeridos == ["2026-08", "2026-09"]
    assert executor.meses() == ["2026-08", "2026-09"]
    assert [r.modo for r in resultados] == ["corrente", "corrente"]
    assert ler_estado(configuracao).mes_referencia == "2026-09"


def _particao_gold(configuracao: Configuracao, mes: str) -> Path:
    return configuracao.gold_dir / "fct_resumo_mensal" / f"mes_referencia={mes}"


def test_mes_anterior_ao_gold_corrente_vira_backfill_so_do_resumo(
    tmp_path: Path, ingeridos: list
) -> None:
    configuracao = _config(tmp_path)
    gravar_estado(configuracao, Estado("2026-09", "2026-09-12", "x"))
    antiga = _particao_gold(configuracao, "2026-08")
    antiga.mkdir(parents=True)
    (antiga / "data_0.parquet").write_text("antigo")
    (antiga / "data_1.parquet").write_text("sobra do antigo")
    executor = ExecutorFalso()
    (resultado,) = executar_pipeline(configuracao, ["2026-08"], _opcoes(), executor=executor)
    assert resultado.modo == "backfill"
    (build,) = executor.chamadas  # R4-02: um build só, com os testes (nada de `dbt test` depois)
    assert build[0][:3] == ["build", "--selector", orquestracao.SELETOR_BACKFILL]
    raiz_temporaria = Path(build[1]["RFB_EXTERNAL_ROOT"])
    assert raiz_temporaria.parent.parent == configuracao.raiz_dados / "_tmp"
    assert build[1]["CAMINHO_DUCKDB"].startswith(str(raiz_temporaria.parent))
    assert Path(build[1]["RFB_RAIZ_SERIE"]).parent == raiz_temporaria.parent
    assert build[1]["RAIZ_DADOS"] == str(configuracao.raiz_dados)  # histórico de DQ ao gold real
    assert "--target-path" in build[0]
    assert not raiz_temporaria.parent.exists()  # temporário removido
    # a partição testada substitui a antiga inteira (sem sobras de arquivos antigos)
    assert sorted(p.name for p in antiga.iterdir()) == ["data_0.parquet"]
    assert (antiga / "data_0.parquet").read_text() == "novo 2026-08"
    assert ler_estado(configuracao).mes_referencia == "2026-09"  # gold corrente intacto
    assert set(resultado.tempos_s) >= {"dbt_build_backfill", "mover_particao"}


def test_backfill_que_falha_nao_toca_a_particao_do_gold(tmp_path: Path, ingeridos: list) -> None:
    """R4-02: teste error no build do backfill -> a partição do gold fica como estava."""
    configuracao = _config(tmp_path)
    gravar_estado(configuracao, Estado("2026-09", None, "x"))
    antiga = _particao_gold(configuracao, "2026-08")
    antiga.mkdir(parents=True)
    (antiga / "data_0.parquet").write_text("antigo")
    with pytest.raises(PipelineErro, match="backfill"):
        executar_pipeline(
            configuracao, ["2026-08"], _opcoes(), executor=ExecutorFalso(falhar=["build"])
        )
    assert (antiga / "data_0.parquet").read_text() == "antigo"
    assert not list((configuracao.raiz_dados / "_tmp").glob("backfill-*"))


def test_backfill_sem_particao_gravada_e_erro(tmp_path: Path, ingeridos: list) -> None:
    """R4-04 (D04): o dbt gravou a partição fora de `RFB_RAIZ_SERIE` -> erro, não sucesso calado."""
    configuracao = _config(tmp_path)
    gravar_estado(configuracao, Estado("2026-09", None, "x"))

    def _dbt_sem_particao(argumentos: Sequence[str], _ambiente: Mapping[str, str]) -> int:
        return 0

    with pytest.raises(PipelineErro, match="sem gravar a partição"):
        executar_pipeline(configuracao, ["2026-08"], _opcoes(), executor=_dbt_sem_particao)
    assert not _particao_gold(configuracao, "2026-08").exists()


def test_backfill_e_mes_novo_na_mesma_chamada(tmp_path: Path, ingeridos: list) -> None:
    configuracao = _config(tmp_path)
    gravar_estado(configuracao, Estado("2026-09", None, "x"))
    executor = ExecutorFalso()
    resultados = executar_pipeline(
        configuracao, ["2026-10", "2026-08"], _opcoes(), executor=executor
    )
    assert [(r.mes_referencia, r.modo) for r in resultados] == [
        ("2026-08", "backfill"),
        ("2026-10", "corrente"),
    ]
    assert ler_estado(configuracao).mes_referencia == "2026-10"


def test_reprocessar_o_mes_corrente_nao_e_backfill(tmp_path: Path, ingeridos: list) -> None:
    configuracao = _config(tmp_path)
    gravar_estado(configuracao, Estado("2026-09", None, "x"))
    (resultado,) = executar_pipeline(configuracao, ["2026-09"], _opcoes(), executor=ExecutorFalso())
    assert resultado.modo == "corrente"


def test_sem_ingestao_exige_mes(tmp_path: Path) -> None:
    with pytest.raises(PipelineErro, match="--mes"):
        executar_pipeline(_config(tmp_path), None, _opcoes(ingerir=False), executor=ExecutorFalso())


def test_sem_ingestao_usa_o_raw_existente(tmp_path: Path, ingeridos: list) -> None:
    executor = ExecutorFalso()
    executar_pipeline(_config(tmp_path), ["2025-02"], _opcoes(ingerir=False), executor=executor)
    assert ingeridos == []
    assert executor.meses() == ["2025-02"]


def test_s3_sincroniza_o_raw_e_usa_o_target_s3(
    tmp_path: Path, ingeridos: list, monkeypatch: pytest.MonkeyPatch
) -> None:
    configuracao = _config(
        tmp_path,
        RAIZ_DADOS="s3://balde/prefixo",
        RAIZ_DADOS_LOCAL=str(tmp_path / "local"),
        AWS_ACCESS_KEY_ID="id",
        AWS_SECRET_ACCESS_KEY="segredo",
        AWS_ENDPOINT_URL_S3="https://s3.exemplo",
    )
    sincronizados: list[Configuracao] = []
    monkeypatch.setattr(orquestracao, "sincronizar", lambda c: sincronizados.append(c) or [])
    monkeypatch.setenv("MOTHERDUCK_TOKEN", "t")
    monkeypatch.setenv("MOTHERDUCK_BANCO", "rfb")
    publicados: list = []
    monkeypatch.setattr(orquestracao, "publicar_motherduck", lambda *a, **k: publicados.append(1))
    executor = ExecutorFalso()
    executar_pipeline(configuracao, ["2026-09"], _opcoes(), executor=executor)
    assert sincronizados == [configuracao]
    assert all(a[a.index("--target") + 1] == "s3" for a in executor.comandos)
    _, ambiente = executor.chamadas[0]
    assert ambiente["RAIZ_DADOS"] == "s3://balde/prefixo"
    assert ambiente["RAIZ_DADOS_LOCAL"] == str(tmp_path / "local")
    assert publicados == []  # a publicação lê gold local: pulada em s3


def test_publica_no_motherduck_so_quando_configurado(
    tmp_path: Path, ingeridos: list, monkeypatch: pytest.MonkeyPatch
) -> None:
    chamadas: list = []
    monkeypatch.setattr(
        orquestracao, "publicar_motherduck", lambda c, tabelas=None: chamadas.append(tabelas)
    )
    configuracao = _config(tmp_path)
    executar_pipeline(configuracao, ["2026-09"], _opcoes(), executor=ExecutorFalso())
    assert chamadas == []
    monkeypatch.setenv("MOTHERDUCK_TOKEN", "t")
    monkeypatch.setenv("MOTHERDUCK_BANCO", "rfb")
    executar_pipeline(configuracao, ["2026-09"], _opcoes(), executor=ExecutorFalso())
    executar_pipeline(configuracao, ["2026-08"], _opcoes(), executor=ExecutorFalso())
    assert chamadas == [None, ["fct_resumo_mensal"]]  # completo; backfill só o resumo
    executar_pipeline(configuracao, ["2026-09"], _opcoes(publicar=False), executor=ExecutorFalso())
    assert len(chamadas) == 2


def test_relatorio_e_gerado_no_caminho_pedido(
    tmp_path: Path, ingeridos: list, monkeypatch: pytest.MonkeyPatch
) -> None:
    gerados: list = []
    monkeypatch.setattr(
        orquestracao,
        "gerar_relatorio",
        lambda c, saida, target: gerados.append((saida, target)) or saida,
    )
    opcoes = OpcoesPipeline(saida_relatorio=tmp_path / "r.md", target="ci")
    executar_pipeline(_config(tmp_path), ["2026-09"], opcoes, executor=ExecutorFalso())
    assert gerados == [(tmp_path / "r.md", "ci")]


def test_falha_do_relatorio_nao_grava_estado(
    tmp_path: Path, ingeridos: list, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _falha(*_a, **_k):
        raise ErroIngestao("analysis falhou")

    monkeypatch.setattr(orquestracao, "gerar_relatorio", _falha)
    configuracao = _config(tmp_path)
    with pytest.raises(ErroIngestao):
        executar_pipeline(
            configuracao,
            ["2026-09"],
            OpcoesPipeline(saida_relatorio=tmp_path / "r.md"),
            executor=ExecutorFalso(),
        )
    assert ler_estado(configuracao) is None


# ---------------------------------------------------------------------------- gold misto (R4-03)


def _marcador(configuracao: Configuracao) -> Path:
    return configuracao.raiz_dados / orquestracao.ARQUIVO_EM_ANDAMENTO


def test_marcador_existe_durante_o_build_e_sai_no_sucesso(tmp_path: Path, ingeridos: list) -> None:
    configuracao = _config(tmp_path)
    vistos: list[tuple[str, bool]] = []
    executor = ExecutorFalso()

    def _dbt(argumentos: Sequence[str], ambiente: Mapping[str, str]) -> int:
        vistos.append((argumentos[0], _marcador(configuracao).is_file()))
        return executor(argumentos, ambiente)

    executar_pipeline(configuracao, ["2026-09"], _opcoes(), executor=_dbt)
    assert vistos == [("source", False), ("build", True)]
    assert not _marcador(configuracao).exists()
    orquestracao.verificar_gold_consistente(configuracao, "relatorio")  # não levanta


def test_build_que_falha_deixa_o_marcador_e_relatorio_e_publicar_recusam(
    tmp_path: Path, ingeridos: list, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    configuracao = _config(tmp_path)
    gravar_estado(configuracao, Estado("2026-08", None, "x"))
    with pytest.raises(PipelineErro, match="dbt build"):
        executar_pipeline(
            configuracao, ["2026-09"], _opcoes(), executor=ExecutorFalso(falhar=["build"])
        )
    assert json.loads(_marcador(configuracao).read_text())["mes_referencia"] == "2026-09"
    assert ler_estado(configuracao).mes_referencia == "2026-08"

    monkeypatch.setenv("RAIZ_DADOS", str(configuracao.raiz_dados))
    monkeypatch.setattr(cli, "gerar_relatorio", lambda *a, **k: pytest.fail("gerou relatório"))
    assert cli.main(["relatorio", "--saida", str(tmp_path / "r.md")]) == 1
    assert "rfb relatorio recusado: o gold pode estar misto" in capsys.readouterr().err
    monkeypatch.setenv("MOTHERDUCK_TOKEN", "t")
    monkeypatch.setenv("MOTHERDUCK_BANCO", "rfb")
    nao_publica = lambda *a, **k: pytest.fail("publicou")  # noqa: E731
    monkeypatch.setattr(orquestracao, "publicar_motherduck", nao_publica)
    with pytest.raises(ErroIngestao, match="rfb publicar recusado"):
        orquestracao._publicar_se_configurado(configuracao, ["fct_resumo_mensal"])

    # rodar o mesmo mês de novo até concluir tira o gold do estado misto
    executar_pipeline(configuracao, ["2026-09"], _opcoes(publicar=False), executor=ExecutorFalso())
    assert not _marcador(configuracao).exists()
    assert ler_estado(configuracao).mes_referencia == "2026-09"


def test_backfill_em_s3_envia_a_particao_movida_ao_bucket(
    tmp_path: Path, ingeridos: list, monkeypatch: pytest.MonkeyPatch
) -> None:
    configuracao = _config(
        tmp_path,
        RAIZ_DADOS="s3://balde/prefixo",
        RAIZ_DADOS_LOCAL=str(tmp_path / "local"),
        AWS_ACCESS_KEY_ID="id",
        AWS_SECRET_ACCESS_KEY="segredo",
        AWS_ENDPOINT_URL_S3="https://s3.exemplo",
    )
    gravar_estado(configuracao, Estado("2026-09", None, "x"))
    particoes_ao_sincronizar: list[list[str]] = []

    def _sincronizar(c: Configuracao) -> list:
        particoes_ao_sincronizar.append(
            sorted(p.name for p in (c.gold_dir / "fct_resumo_mensal").glob("*"))
        )
        return []

    monkeypatch.setattr(orquestracao, "sincronizar", _sincronizar)
    executar_pipeline(configuracao, ["2026-08"], _opcoes(), executor=ExecutorFalso())
    # 1ª: o raw após a ingestão (antes do build); 2ª: a partição testada, já no gold local
    assert particoes_ao_sincronizar == [[], ["mes_referencia=2026-08"]]


# ---------------------------------------------------------------------------- atualizar


def _origem(tmp_path: Path, meses: dict[str, bool]) -> Path:
    """Origem local só com nomes de zip: `{mês: completo?}` (incompleto = sem `Simples.zip`)."""
    origem = tmp_path / "origem"
    for mes, completo in meses.items():
        pasta = origem / "rfb" / mes
        pasta.mkdir(parents=True)
        for nome in ARQUIVOS_ESPERADOS_MES:
            if completo or nome != "Simples.zip":
                (pasta / nome).touch()
    return origem


def test_atualizar_processa_o_mes_completo_mais_recente_e_grava_estado(
    tmp_path: Path, ingeridos: list
) -> None:
    configuracao = _config(tmp_path)
    gravar_estado(configuracao, Estado("2026-08", None, "x"))
    origem = _origem(tmp_path, {"2026-08": True, "2026-09": True})
    executor = ExecutorFalso()
    resultado = atualizar(configuracao, _opcoes(origem_local=origem), executor=executor)
    assert resultado.mes_referencia == "2026-09"
    assert ingeridos == ["2026-09"]
    assert executor.meses() == ["2026-09"]
    assert ler_estado(configuracao).mes_referencia == "2026-09"


def test_atualizar_sem_mes_novo_e_no_op(
    tmp_path: Path, ingeridos: list, capsys: pytest.CaptureFixture[str]
) -> None:
    configuracao = _config(tmp_path)
    gravar_estado(configuracao, Estado("2026-09", None, "x"))
    origem = _origem(tmp_path, {"2026-09": True})
    executor = ExecutorFalso()
    assert atualizar(configuracao, _opcoes(origem_local=origem), executor=executor) is None
    assert "nenhum mês novo" in capsys.readouterr().out
    assert ingeridos == [] and executor.comandos == []


def test_atualizar_ignora_mes_incompleto_e_usa_o_anterior_completo(
    tmp_path: Path, ingeridos: list
) -> None:
    configuracao = _config(tmp_path)
    gravar_estado(configuracao, Estado("2026-08", None, "x"))
    origem = _origem(tmp_path, {"2026-08": True, "2026-09": True, "2026-10": False})
    resultado = atualizar(configuracao, _opcoes(origem_local=origem), executor=ExecutorFalso())
    assert resultado.mes_referencia == "2026-09"


def test_atualizar_so_com_mes_incompleto_falha(tmp_path: Path, ingeridos: list) -> None:
    origem = _origem(tmp_path, {"2026-10": False})
    with pytest.raises(MesIncompletoErro):
        atualizar(_config(tmp_path), _opcoes(origem_local=origem), executor=ExecutorFalso())


def test_atualizar_com_falha_do_dbt_sai_nao_zero_sem_estado_nem_retencao(
    tmp_path: Path, ingeridos: list, monkeypatch: pytest.MonkeyPatch
) -> None:
    configuracao = _config(tmp_path, RFB_MESES_RETIDOS="1")
    gravar_estado(configuracao, Estado("2026-08", None, "x"))
    antigo = configuracao.raw_dir / "rfb" / "empresas" / "mes_referencia=2026-08"
    antigo.mkdir(parents=True)
    (configuracao.raw_dir / "rfb" / "empresas" / "mes_referencia=2026-09").mkdir()
    origem = _origem(tmp_path, {"2026-09": True})
    monkeypatch.setattr(orquestracao, "executar_dbt", ExecutorFalso(falhar=["build"]))
    monkeypatch.setattr(cli, "carregar_configuracao", lambda: configuracao)
    codigo = cli.main(["atualizar", "--origem-local", str(origem), "--sem-relatorio"])
    assert codigo == 1
    assert ler_estado(configuracao).mes_referencia == "2026-08"
    assert antigo.is_dir()


# ---------------------------------------------------------------------------- retenção


def _particoes(configuracao: Configuracao, meses: list[str]) -> None:
    for entidade in ("empresas", "estabelecimentos"):
        for mes in meses:
            pasta = configuracao.raw_dir / "rfb" / entidade / f"mes_referencia={mes}"
            pasta.mkdir(parents=True)
            (pasta / "part-0.parquet").touch()
    for mes in meses:
        baixados = configuracao.baixados_dir(mes)
        baixados.mkdir(parents=True)
        (baixados / "Empresas0.zip").touch()


def _meses_raw(configuracao: Configuracao) -> list[str]:
    return sorted(
        {
            p.name.removeprefix("mes_referencia=")
            for p in (configuracao.raw_dir / "rfb").glob("*/mes_referencia=*")
        }
    )


def test_retencao_mantem_os_ultimos_meses_e_apaga_zips_do_mes_processado(tmp_path: Path) -> None:
    configuracao = _config(tmp_path)
    _particoes(configuracao, ["2026-07", "2026-08", "2026-09"])
    aplicar_retencao(configuracao, "2026-09")
    assert _meses_raw(configuracao) == ["2026-08", "2026-09"]
    assert sorted(p.name for p in (configuracao.raiz_dados / "_baixados").iterdir()) == ["2026-08"]


def test_retencao_configuravel_e_manter_zips(tmp_path: Path) -> None:
    configuracao = _config(tmp_path, RFB_MESES_RETIDOS="1", RFB_MANTER_ZIPS="true")
    _particoes(configuracao, ["2026-08", "2026-09"])
    aplicar_retencao(configuracao, "2026-09")
    assert _meses_raw(configuracao) == ["2026-09"]
    assert [p.name for p in (configuracao.raiz_dados / "_baixados").iterdir()] == ["2026-09"]


def test_atualizar_aplica_retencao_apos_sucesso(tmp_path: Path, ingeridos: list) -> None:
    configuracao = _config(tmp_path, RFB_MESES_RETIDOS="1")
    _particoes(configuracao, ["2026-08", "2026-09"])
    gravar_estado(configuracao, Estado("2026-08", None, "x"))
    origem = _origem(tmp_path, {"2026-09": True})
    atualizar(configuracao, _opcoes(origem_local=origem), executor=ExecutorFalso())
    assert _meses_raw(configuracao) == ["2026-09"]
    assert not configuracao.baixados_dir("2026-09").exists()


# ---------------------------------------------------------------------------- estado e CLI


def test_estado_invalido_e_erro_claro(tmp_path: Path) -> None:
    configuracao = _config(tmp_path)
    caminho = configuracao.raiz_dados / orquestracao.ARQUIVO_ESTADO
    caminho.parent.mkdir(parents=True)
    caminho.write_text("{}", encoding="utf-8")
    with pytest.raises(ErroIngestao, match="estado inválido"):
        ler_estado(configuracao)


def test_cli_pipeline_rejeita_mes_mal_formado(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["pipeline", "--mes", "2026-9", "--sem-relatorio"]) == 1
    assert "--mes inválido" in capsys.readouterr().err
