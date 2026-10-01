"""Raiz duplicada nas Empresas de ponta a ponta (R4-05, Fix 7 da R4).

A raiz de B (22222222) tem uma linha "fantasma" (sem razão social, natureza 0000, como a raiz
08314885 do extrato real de 2026-09) antes da linha boa: a fonte avisa, o staging fica com uma linha
por raiz, B sai uma vez no gold e a paridade (que emula a dedup) continua verde. Lê `RAIZ_DADOS` do
ambiente, exportado pelo `make ci`.
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pytest
from test_bh_empresas import _status_dos_testes

pytestmark = pytest.mark.skipif(
    "RAIZ_DADOS" not in os.environ, reason="rode via make ci (exporta RAIZ_DADOS)"
)


def _raw_empresas(onde: str, colunas: str) -> list[tuple]:
    raw = Path(os.environ["RAIZ_DADOS"]) / "raw" / "rfb" / "empresas"
    with duckdb.connect() as con:
        return con.sql(
            f"select {colunas} from read_parquet('{raw}/*/*.parquet') "
            f"where _mes_referencia = '2026-09' and {onde}"
        ).fetchall()


def test_raiz_duplicada_no_raw_vira_uma_linha_no_staging() -> None:
    """R4-05 (Fix 7): o raw tem 2 linhas da raiz de B; o staging, 1 (a boa), e B sai uma vez."""
    raw_b = _raw_empresas("cnpj_raiz = '22222222'", "coalesce(razao_social, ''), natureza_jur")
    assert sorted(raw_b) == [("", "0000"), ("COLORIR TINTAS", "2062")]
    banco = Path(os.environ["RAIZ_DADOS"]) / "warehouse.duckdb"
    with duckdb.connect(str(banco), read_only=True) as con:
        (schema,) = con.sql(
            "select table_schema from information_schema.tables "
            "where table_name = 'stg_rfb__empresas'"
        ).fetchone()
        por_raiz = con.sql(
            f"select cnpj_raiz, count(*) from {schema}.stg_rfb__empresas "
            "group by all having count(*) > 1"
        ).fetchall()
        b = con.sql(
            f"select razao_social, natureza_juridica_codigo from {schema}.stg_rfb__empresas "
            "where cnpj_raiz = '22222222'"
        ).fetchall()
        (raizes,) = con.sql(f"select count(*) from {schema}.stg_rfb__empresas").fetchone()
    assert por_raiz == []
    assert b == [("COLORIR TINTAS", "2062")]
    assert raizes == 15


def test_raiz_duplicada_avisa_na_fonte_e_b_sai_uma_vez_no_gold(consultar) -> None:
    (unicidade,) = [
        s
        for nome, s in _status_dos_testes().items()
        if nome.startswith("dbt_utils_source_unique_combination_of_columns_rfb_empresas")
    ]
    # a raiz de B duplicada em cada mês retido (2026-08 e 2026-09): aviso; o erro é acima de 100
    assert unicidade == ("warn", 2)
    assert consultar("select count(*) from {bh_empresas} where cnpj_raiz = '22222222'") == [(1,)]
    assert _status_dos_testes()["paridade_bh_empresas"] == ("pass", 0)
