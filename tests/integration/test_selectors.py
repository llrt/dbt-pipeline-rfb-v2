"""RBP-14: `transform/selectors.yml` seleciona o que o nome promete (usado pelo `rfb pipeline`)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

TRANSFORM = Path(__file__).resolve().parents[2] / "transform"


def _listar(tmp_path: Path, seletor: str, *tipos: str) -> set[str]:
    env = os.environ | {"RAIZ_DADOS": str(tmp_path), "DBT_PROFILES_DIR": str(TRANSFORM)}
    env.pop("CAMINHO_DUCKDB", None)
    resultado = subprocess.run(
        ["uv", "run", "dbt", "ls", "--target", "ci", "--selector", seletor, "--output", "name",
         "--log-path", str(tmp_path / "logs"),
         *[arg for t in tipos for arg in ("--resource-type", t)]],
        cwd=TRANSFORM, env=env, capture_output=True, text=True, check=False,
    )  # fmt: skip
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    return {
        linha.strip() for linha in resultado.stdout.splitlines() if linha.strip().isidentifier()
    }


def test_backfill_constroi_e_testa_o_resumo_e_o_que_ele_le(tmp_path: Path) -> None:
    """R4-02: o backfill roda os testes de `+fct_resumo_mensal` antes de a partição ir ao gold."""
    nos = _listar(tmp_path, "backfill_resumo_mensal")
    assert {"fct_resumo_mensal", "fct_estabelecimentos", "stg_rfb__estabelecimentos"} <= nos
    assert "mart_dinamica_mercado" not in nos
    testes = _listar(tmp_path, "backfill_resumo_mensal", "test")
    assert {
        "unique_fct_estabelecimentos_cnpj_completo",
        "not_null_stg_rfb__estabelecimentos__data_referencia",
        "fct_estabelecimentos_reconciliacao",
        "fct_resumo_mensal_reconciliacao",
        "fct_resumo_mensal_relacionamentos_mes",
    } <= testes
    # os que comparam com o gold corrente divergem por definição no backfill
    assert not testes & {
        "fct_resumo_mensal_gold_corrente",
        "fct_resumo_mensal_integridade_historica",
    }
    # cautious: nada de testes de marts fora da linhagem do resumo
    assert not {n for n in testes if "mart_" in n or "bh_empresas" in n}


@pytest.mark.parametrize(
    ("seletor", "presente", "ausente"),
    [
        ("original", "bh_empresas", "mart_dinamica_mercado"),
        ("adicao", "mart_dinamica_mercado", "bh_empresas"),
        ("incremento_enriquecimento_bd", "stg_bd__censo_2022_municipio", "stg_rfb__empresas"),
    ],
)
def test_seletores_de_escopo(tmp_path: Path, seletor: str, presente: str, ausente: str) -> None:
    nos = _listar(tmp_path, seletor, "model")
    assert presente in nos
    assert ausente not in nos
