"""`rfb atualizar`/`rfb pipeline` sobre as fixtures de dois meses (UPD-01 AC 1–5 e 8, P22).

O `make ci` roda, nesta ordem e com dbt real: `rfb pipeline --mes 2026-08` (corrente) -> `rfb
atualizar` (processa 2026-09) -> `rfb atualizar` (no-op, log em `.tmp/ci/atualizar-noop.log`) ->
`rfb pipeline --mes 2026-08` (backfill, log em `.tmp/ci/backfill.log`; antes dele o `make ci`
apaga a partição 2026-08 do resumo, para provar que o backfill a regrava, R4-04). Os testes de
falha do dbt e de retenção usam ingestão real das fixtures num `RAIZ_DADOS` temporário e um dbt
falso (o caminho de falha não precisa do dbt de verdade).
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path

import duckdb
import pytest

from rfb_pipeline import cli
from rfb_pipeline.configuracao import carregar_configuracao
from rfb_pipeline.orquestracao import (
    Estado,
    OpcoesPipeline,
    PipelineErro,
    atualizar,
    gravar_estado,
    ler_estado,
)

pytestmark = pytest.mark.skipif(
    "RAIZ_DADOS" not in os.environ, reason="rode via make ci (exporta RAIZ_DADOS)"
)

RAIZ_REPO = Path(__file__).resolve().parents[2]
CI = RAIZ_REPO / ".tmp" / "ci"
FIXTURES = CI / "fixtures"


def _raiz() -> Path:
    return Path(os.environ["RAIZ_DADOS"])


def _contar(sql: str) -> int:
    with duckdb.connect() as con:
        return con.execute(sql).fetchone()[0]


# ---------------------------------------------------------------------------- fluxo do make ci


def test_ac1_mes_novo_processado_e_registrado_no_estado() -> None:
    estado = json.loads((_raiz() / "_estado" / "ultima_execucao.json").read_text("utf-8"))
    assert estado["mes_referencia"] == "2026-09"
    assert estado["data_referencia"] == "2026-09-12"
    assert estado["concluido_em"]


def test_ac2_segunda_chamada_e_no_op_sem_baixar_nem_rodar_dbt() -> None:
    log = (CI / "atualizar-noop.log").read_text("utf-8")
    assert "nenhum mês novo" in log
    assert "etapa" not in log and "$ dbt" not in log


def test_ac8_p22_backfill_grava_so_o_resumo_e_mantem_o_gold_corrente() -> None:
    log = (CI / "backfill.log").read_text("utf-8")
    assert "2026-08 [backfill] concluído" in log
    gold = _raiz() / "gold"
    # a fato detalhada continua sendo a de 2026-09 (16 estabelecimentos; 2026-08 tem 15)
    assert (
        _contar(f"select count(*) from read_parquet('{gold}/fct_estabelecimentos.parquet')") == 16
    )
    meses = sorted(p.name for p in (gold / "fct_resumo_mensal").iterdir())
    assert meses == ["mes_referencia=2026-08", "mes_referencia=2026-09"]
    # R4-04: a partição 2026-08 foi apagada antes do backfill; ele a regravou com os 15
    # estabelecimentos do mês (a fato detalhada, de 2026-09, segue com 16)
    serie = f"read_parquet('{gold}/fct_resumo_mensal/*/*.parquet', hive_partitioning=true)"
    assert (
        _contar(f"select sum(qtd_estabelecimentos) from {serie} where mes_referencia = '2026-08'")
        == 15
    )
    assert (
        _contar(f"select sum(qtd_estabelecimentos) from {serie} where mes_referencia = '2026-09'")
        == 16
    )
    assert not list((_raiz() / "_tmp").glob("backfill-*"))  # temporários removidos
    assert ler_estado(carregar_configuracao({"RAIZ_DADOS": str(_raiz())})).mes_referencia == (
        "2026-09"
    )


def test_p22_teste_de_gold_corrente_passou_no_ultimo_build_completo() -> None:
    with duckdb.connect(str(_raiz() / "warehouse.duckdb"), read_only=True) as con:
        status = con.execute(
            "select status from main.dq_historico_testes "
            "where nome_teste = 'fct_resumo_mensal_gold_corrente' order by executado_em"
        ).fetchall()
    assert status == [("pass",), ("pass",)]  # builds completos de 2026-08 e de 2026-09


def test_p22_gold_atrasado_dispara_o_aviso(tmp_path: Path) -> None:
    """O teste de gold corrente acusa resumo com mês mais novo que o build (mês antigo por cima)."""
    from rfb_pipeline.relatorio import DIR_TRANSFORM

    compilado = next(
        (DIR_TRANSFORM / "target" / "compiled" / "rfb" / "tests").glob(
            "fct_resumo_mensal_gold_corrente.sql"
        )
    ).read_text("utf-8")
    with duckdb.connect(str(_raiz() / "warehouse.duckdb"), read_only=True) as con:
        assert con.execute(compilado).fetchall() == []
        atrasado = compilado.replace(
            "max(_mes_referencia)", "min('2026-08')"
        )  # simula o gold corrente em 2026-08 com a série já em 2026-09
        assert con.execute(atrasado).fetchall() == [("2026-09", "2026-08")]


# ---------------------------------------------------------------------------- falha e retenção


class _Dbt:
    def __init__(self, falhar: str | None = None) -> None:
        self.falhar = falhar
        self.comandos: list[list[str]] = []

    def __call__(self, argumentos: Sequence[str], _ambiente: Mapping[str, str]) -> int:
        self.comandos.append(list(argumentos))
        return 1 if argumentos[0] == self.falhar else 0


def _raiz_com_agosto(tmp_path: Path, **env: str):
    configuracao = carregar_configuracao({"RAIZ_DADOS": str(tmp_path / "dados"), **env})
    cli.ingerir(configuracao, mes="2026-08", origem_local=FIXTURES, permitir_incompleto=True)
    gravar_estado(configuracao, Estado("2026-08", "2026-08-10", "x"))
    return configuracao


def _meses_raw(configuracao) -> list[str]:
    return sorted(
        {
            p.name.removeprefix("mes_referencia=")
            for p in (configuracao.raw_dir / "rfb").glob("*/mes_referencia=*")
        }
    )


def _opcoes() -> OpcoesPipeline:
    return OpcoesPipeline(
        origem_local=FIXTURES, permitir_incompleto=True, saida_relatorio=None, publicar=False
    )


def test_ac4_falha_do_dbt_nao_grava_estado_nem_aplica_retencao(tmp_path: Path) -> None:
    configuracao = _raiz_com_agosto(tmp_path, RFB_MESES_RETIDOS="1")
    with pytest.raises(PipelineErro, match="dbt build"):
        atualizar(configuracao, _opcoes(), executor=_Dbt(falhar="build"))
    assert ler_estado(configuracao).mes_referencia == "2026-08"
    assert _meses_raw(configuracao) == ["2026-08", "2026-09"]


def test_ac5_retencao_apos_sucesso(tmp_path: Path) -> None:
    configuracao = _raiz_com_agosto(tmp_path, RFB_MESES_RETIDOS="1")
    dbt = _Dbt()
    resultado = atualizar(configuracao, _opcoes(), executor=dbt)
    assert resultado.mes_referencia == "2026-09"
    assert [c[0] for c in dbt.comandos] == ["source", "build"]
    assert ler_estado(configuracao).mes_referencia == "2026-09"
    assert _meses_raw(configuracao) == ["2026-09"]
    assert not configuracao.baixados_dir("2026-09").exists()
    assert not configuracao.baixados_dir("2026-08").exists()  # fora da janela de 1 mês


def test_ac5_retencao_padrao_mantem_dois_meses_e_manter_zips(tmp_path: Path) -> None:
    configuracao = _raiz_com_agosto(tmp_path, RFB_MANTER_ZIPS="true")
    atualizar(configuracao, _opcoes(), executor=_Dbt())
    assert _meses_raw(configuracao) == ["2026-08", "2026-09"]
    assert configuracao.baixados_dir("2026-09").is_dir()
