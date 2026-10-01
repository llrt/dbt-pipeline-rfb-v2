"""Fixture `consultar`: consulta os marts Parquet de `RAIZ_DADOS/gold` (testes de integração novos)."""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pytest


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
