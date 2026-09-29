"""`bh_empresas` no Parquet de `gold/` contra o cenário de fixtures da spec (Original AC 2–7).

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

COLUNAS = [
    "cnpj_raiz",
    "cnpj_completo",
    "nome",
    "natureza_juridica",
    "porte",
    "cnae_principal",
    "desc_cnae_principal",
    "grupo_cnae_principal",
    "cnaes_secundarios",
    "municipio",
    "microrregiao_municipio",
    "mesorregiao_municipio",
    "uf",
    "situacao",
    "idade_atual",
]


@pytest.fixture(scope="module")
def linhas() -> dict[str, dict[str, object]]:
    parquet = Path(os.environ["RAIZ_DADOS"]) / "gold" / "bh_empresas.parquet"
    assert parquet.is_file(), f"{parquet} não existe; rode `make ci`"
    with duckdb.connect() as con:
        relacao = con.sql(f"select * from read_parquet('{parquet}')")
        assert relacao.columns == COLUNAS
        registros = relacao.fetchall()
    por_cnpj = {r[1]: dict(zip(COLUNAS, r, strict=True)) for r in registros}
    assert len(por_cnpj) == len(registros), "cnpj_completo repetido em bh_empresas"
    return por_cnpj


def test_doze_linhas_sem_k_l_m(linhas: dict[str, dict[str, object]]) -> None:
    assert len(linhas) == 12
    raizes = {linha["cnpj_raiz"] for linha in linhas.values()}
    assert raizes.isdisjoint({"13131313", "14141414", "15151515"})


def test_linha_a(linhas: dict[str, dict[str, object]]) -> None:
    a = linhas["11111111000191"]
    assert a["cnpj_raiz"] == "11111111"
    assert a["nome"] == "TINTAS FUNDÃO"
    assert a["porte"] == "MICRO"
    assert a["situacao"] == "ATIVA"
    assert a["idade_atual"] == 3.9
    assert a["municipio"] == "FUNDÃO"
    assert a["microrregiao_municipio"] == "LINHARES"
    assert a["mesorregiao_municipio"] == "LITORAL NORTE ESPÍRITO-SANTENSE"
    assert a["uf"] == "ES"
    assert a["cnae_principal"] == "4741500"


def test_linha_e(linhas: dict[str, dict[str, object]]) -> None:
    e = linhas["55555555000191"]
    assert e["nome"] == "TINTAS CAPIXABA"
    assert e["porte"] is None
    assert e["situacao"] == "INATIVA"
    assert e["idade_atual"] is None


def test_cnae_com_zero_a_esquerda_linha_n(linhas: dict[str, dict[str, object]]) -> None:
    assert linhas["16161616000184"]["cnae_principal"] == "0111301"
