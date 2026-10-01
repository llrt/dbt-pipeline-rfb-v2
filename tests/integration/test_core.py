"""Modelo estrela (`gold/`) contra o cenário de fixtures da spec (CORE-01, BI-01).

Lê `RAIZ_DADOS` do ambiente — exportado por `make ci`, que roda `dbt build` antes do pytest.
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pytest

pytestmark = pytest.mark.skipif(
    "RAIZ_DADOS" not in os.environ, reason="rode via make ci (exporta RAIZ_DADOS)"
)


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


def test_dim_municipio_fundao_com_populacao_2024() -> None:
    linhas = _consultar(
        "select sk_municipio, nome_municipio, ano_populacao, populacao, sigla_uf, "
        "nome_microrregiao, latitude from {dim_municipio} where codigo_rfb = '5643'"
    )
    assert len(linhas) == 1
    sk, nome, ano, populacao, uf, microrregiao, latitude = linhas[0]
    assert (sk, nome, ano, populacao, uf) == (3202207, "Fundão", 2024, 20000, "ES")
    assert microrregiao == "Linhares"
    assert latitude == pytest.approx(-19.9687204052472)


def test_dim_municipio_tem_membro_nao_informado() -> None:
    linhas = _consultar(
        "select nome_municipio, nome_uf, populacao from {dim_municipio} where sk_municipio = -1"
    )
    assert linhas == [("NÃO INFORMADO", "NÃO INFORMADO", None)]


def test_dim_municipio_tem_os_oito_municipios_do_bd_mais_o_membro_nao_informado() -> None:
    (total,) = _consultar("select count(*) from {dim_municipio}")[0]
    assert total == 8 + 1
