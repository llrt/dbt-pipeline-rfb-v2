# ruff: noqa: E501
"""Fixture `consultar`: consulta os marts Parquet de `RAIZ_DADOS/gold` (testes novos)."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import duckdb
import pytest

TRANSFORM = Path(__file__).resolve().parents[2] / "transform"


def _consultar(sql: str) -> list[tuple]:
    """Executa `sql` com `{nome}` substituído pelo `read_parquet` do mart em `gold/`."""
    gold = Path(os.environ["RAIZ_DADOS"]) / "gold"

    class _Tabelas(dict):
        def __missing__(self, nome: str) -> str:
            arquivo = gold / f"{nome}.parquet"
            assert arquivo.is_file(), f"{arquivo} não existe; rode `make ci`"
            return f"read_parquet('{arquivo}')"

    with duckdb.connect() as con:
        return con.execute(sql.format_map(_Tabelas())).fetchall()


@pytest.fixture
def consultar():
    """Devolve a função de consulta aos marts de `gold/`."""
    return _consultar


@pytest.fixture(scope="session")
def manifesto_e_catalogo(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    """Caminhos do `manifest.json` e do `catalog.json` gerados por `dbt docs generate` (uma vez por sessão).

    Roda sobre o `warehouse.duckdb` de `RAIZ_DADOS` (criado pelo `make ci`), num diretório temporário,
    para não tocar em `transform/target`. Usado pelos testes de cobertura de descrições e do dicionário.
    """
    if "RAIZ_DADOS" not in os.environ:
        pytest.skip("rode via make ci (exporta RAIZ_DADOS)")
    alvo = tmp_path_factory.mktemp("dbt_docs")
    env = os.environ | {"DBT_PROFILES_DIR": str(TRANSFORM)}
    env.pop("CAMINHO_DUCKDB", None)
    resultado = subprocess.run(
        ["uv", "run", "dbt", "docs", "generate", "--target", "ci", "--no-partial-parse",
         "--target-path", str(alvo), "--log-path", str(alvo / "logs")],
        cwd=TRANSFORM, env=env, capture_output=True, text=True, check=False,
    )  # fmt: skip
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert json.loads((alvo / "catalog.json").read_text(encoding="utf-8"))["nodes"]
    return alvo / "manifest.json", alvo / "catalog.json"
