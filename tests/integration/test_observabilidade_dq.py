"""Histórico de testes dbt (DQ-02): `dq_historico_testes` e `dq_resumo_execucao`.

Roda sobre o `warehouse.duckdb` de `RAIZ_DADOS` e o `manifest.json` do `make ci` (que roda
`dbt build` antes do pytest). O teste de acúmulo roda `dbt test` de novo, em subprocesso.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import duckdb
import pytest

RAIZ = Path(__file__).resolve().parents[2]
TRANSFORM = RAIZ / "transform"
MANIFESTO = TRANSFORM / "target" / "manifest.json"

pytestmark = pytest.mark.skipif(
    "RAIZ_DADOS" not in os.environ or not MANIFESTO.is_file(),
    reason="rode via make ci (exporta RAIZ_DADOS e gera o manifesto)",
)


def _consultar(sql: str) -> list[tuple]:
    banco = Path(os.environ["RAIZ_DADOS"]) / "warehouse.duckdb"
    with duckdb.connect(str(banco), read_only=True) as con:
        return con.execute(sql).fetchall()


def _testes_no_manifesto() -> int:
    manifesto = json.loads(MANIFESTO.read_text(encoding="utf-8"))
    nos = [
        n
        for n in manifesto["nodes"].values()
        if n["resource_type"] == "test" and n["package_name"] == "rfb"
    ]
    return len(nos) + len(manifesto.get("unit_tests", {}))


def test_build_completo_registra_uma_linha_por_teste() -> None:
    # O `make ci` roda antes um build parcial de 2026-08 (série mensal): o completo é o que
    # registrou mais testes.
    (primeira,) = _consultar(
        "select invocation_id from main.dq_historico_testes "
        "group by invocation_id order by count(*) desc, min(executado_em) limit 1"
    )
    (linhas, distintos) = _consultar(
        "select count(*), count(distinct nome_teste) from main.dq_historico_testes "
        f"where invocation_id = '{primeira[0]}'"
    )[0]
    assert linhas == distintos == _testes_no_manifesto()


def test_historico_guarda_status_severidade_e_escopo() -> None:
    # o `make ci` roda dois builds completos no mesmo warehouse (2026-08 e 2026-09): uma linha cada
    linhas = _consultar(
        "select status, falhas, severidade, escopo from main.dq_historico_testes "
        "where nome_teste = 'cnpj_dv_valido_stg_rfb__estabelecimentos_cnpj_completo'"
    )
    assert linhas == [("warn", 1, "warn", "adicao")] * 2


def _historico_no_gold() -> list[tuple]:
    gold = Path(os.environ["RAIZ_DADOS"]) / "gold" / "dq_historico_testes"
    with duckdb.connect() as con:
        return con.execute(
            "select invocation_id, count(*) from read_parquet("
            f"'{gold}/*/*.parquet', hive_partitioning = true) group by all"
        ).fetchall()


def test_historico_exportado_ao_gold_sobrevive_ao_warehouse() -> None:
    # RBP-12: cada execução com testes vira `gold/dq_historico_testes/invocation_id=<id>/`, com as
    # mesmas linhas do warehouse; o backfill (warehouse temporário, descartado) também fica no gold.
    no_gold = dict(_historico_no_gold())
    no_warehouse = dict(
        _consultar("select invocation_id, count(*) from main.dq_historico_testes group by all")
    )
    assert no_warehouse
    assert {i: no_gold.get(i) for i in no_warehouse} == no_warehouse
    assert set(no_gold) - set(no_warehouse), "a execução do backfill deveria estar só no gold"


def test_duas_execucoes_acumulam_e_o_resumo_reflete_cada_uma() -> None:
    antes = _consultar("select count(distinct invocation_id) from main.dq_historico_testes")[0][0]
    subprocess.run(
        ["uv", "run", "dbt", "test", "--target", "ci", "-s", "cnaes_sem_par_bd"],
        cwd=TRANSFORM,
        check=True,
        capture_output=True,
    )
    depois = _consultar("select count(distinct invocation_id) from main.dq_historico_testes")[0][0]
    assert depois == antes + 1
    resumos = _consultar(
        "select testes, avisos from main.dq_resumo_execucao order by executado_em desc"
    )
    assert len(resumos) == depois
    assert resumos[0] == (1, 1)  # a última execução rodou só `cnaes_sem_par_bd` (warn)
