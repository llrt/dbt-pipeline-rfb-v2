"""Testes de DQ novos (DQ-01) contra o cenário de fixtures: falhas guardadas em `store_failures`.

Lê o `warehouse.duckdb` de `RAIZ_DADOS` (exportado por `make ci`, que roda `dbt build` antes).
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pytest

pytestmark = pytest.mark.skipif(
    "RAIZ_DADOS" not in os.environ, reason="rode via make ci (exporta RAIZ_DADOS)"
)

AUDITORIA = "main_dbt_test__audit"


def _falhas(tabela: str) -> list[tuple]:
    banco = Path(os.environ["RAIZ_DADOS"]) / "warehouse.duckdb"
    with duckdb.connect(str(banco), read_only=True) as con:
        return con.execute(f"select * from {AUDITORIA}.{tabela}").fetchall()


def test_cnpj_dv_valido_acusa_exatamente_o_estabelecimento_l() -> None:
    assert _falhas("cnpj_dv_valido_stg_rfb__estabelecimentos_cnpj_completo") == [
        ("14141414000155",)
    ]


def test_data_nao_futura_nao_acusa_nada_nas_fixtures() -> None:
    assert _falhas("data_nao_futura_stg_rfb__estabelecimentos_dat_inicio_atividade") == []
