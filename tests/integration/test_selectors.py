"""RBP-14: `transform/selectors.yml` seleciona o que o nome promete (usado pelo `make ci`)."""

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


def test_ci_mes_antigo_tem_o_resumo_e_o_que_ele_le_sem_testes(tmp_path: Path) -> None:
    nos = _listar(tmp_path, "ci_mes_antigo")
    assert {"fct_resumo_mensal", "fct_estabelecimentos", "stg_rfb__estabelecimentos"} <= nos
    assert not {n for n in nos if n.startswith(("not_null_", "unique_", "test_"))}
    assert "mart_dinamica_mercado" not in nos


def test_ci_resumo_mes_antigo_so_testa_o_resumo(tmp_path: Path) -> None:
    nos = _listar(tmp_path, "ci_resumo_mes_antigo", "test")
    assert nos
    assert not {n for n in nos if "mart_" in n or "bh_empresas" in n or "stg_" in n}


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
