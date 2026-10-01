"""`agg_empresas` no Parquet de `gold/` contra o cenário de fixtures da spec (Original AC 8–9).

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
    "municipio",
    "microrregiao_municipio",
    "mesorregiao_municipio",
    "uf",
    "cnae_principal",
    "desc_cnae_principal",
    "grupo_cnae_principal",
    "natureza_juridica",
    "porte",
    "situacao",
    "qtd_empresas",
    "media_idade",
]


def _gold(nome: str) -> str:
    parquet = Path(os.environ["RAIZ_DADOS"]) / "gold" / f"{nome}.parquet"
    assert parquet.is_file(), f"{parquet} não existe; rode `make ci`"
    return str(parquet)


@pytest.fixture(scope="module")
def fundao_tintas() -> list[dict[str, object]]:
    with duckdb.connect() as con:
        relacao = con.sql(f"select * from read_parquet('{_gold('agg_empresas')}')")
        assert relacao.columns == COLUNAS
        registros = con.execute(
            f"select * from read_parquet('{_gold('agg_empresas')}') "
            "where cnae_principal = '4741500' and municipio = 'FUNDÃO' and uf = 'ES'"
        ).fetchall()
    return [dict(zip(COLUNAS, r, strict=True)) for r in registros]


def test_fundao_4741500_ativa_micro_com_idade_3_9(fundao_tintas: list[dict[str, object]]) -> None:
    ativas = [r for r in fundao_tintas if r["situacao"] == "ATIVA"]
    assert len(ativas) == 1
    assert ativas[0]["porte"] == "MICRO"
    assert ativas[0]["qtd_empresas"] == 1
    assert ativas[0]["media_idade"] == 3.9


def test_fundao_4741500_inativas_somam_4_sem_idade(fundao_tintas: list[dict[str, object]]) -> None:
    inativas = [r for r in fundao_tintas if r["situacao"] == "INATIVA"]
    assert sum(r["qtd_empresas"] for r in inativas) == 4
    assert all(r["media_idade"] is None for r in inativas)


def test_soma_de_qtd_empresas_reconcilia_com_bh_empresas() -> None:
    with duckdb.connect() as con:
        total_agg = con.execute(
            f"select sum(qtd_empresas) from read_parquet('{_gold('agg_empresas')}')"
        ).fetchone()[0]
        total_bh = con.execute(
            f"select count(*) from read_parquet('{_gold('bh_empresas')}')"
        ).fetchone()[0]
    assert total_agg == total_bh == 12
