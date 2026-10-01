"""Série mensal `fct_resumo_mensal` (BI-02 AC 8, UPD-02): uma partição Parquet por mês.

Lê `RAIZ_DADOS` do ambiente — `make ci` processa 2026-08 (build do mês antigo) e depois 2026-09.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import duckdb
import pytest

pytestmark = pytest.mark.skipif(
    "RAIZ_DADOS" not in os.environ, reason="rode via make ci (exporta RAIZ_DADOS)"
)

RAIZ = Path(os.environ.get("RAIZ_DADOS", "."))
TRANSFORM = Path(__file__).resolve().parents[2] / "transform"
LEITURA = "read_parquet('{gold}/fct_resumo_mensal/*/*.parquet', hive_partitioning = true)"


def _consultar(sql: str, gold: Path | None = None) -> list[tuple]:
    gold = gold or RAIZ / "gold"
    sql = sql.replace("{resumo}", LEITURA.format(gold=gold))
    for dim in ("dim_municipio", "dim_cnae"):
        sql = sql.replace("{" + dim + "}", f"read_parquet('{gold}/{dim}.parquet')")
    with duckdb.connect() as con:
        return con.execute(sql).fetchall()


def test_ha_uma_particao_por_mes_processado() -> None:
    particoes = sorted(p.name for p in (RAIZ / "gold" / "fct_resumo_mensal").iterdir())
    assert particoes == ["mes_referencia=2026-08", "mes_referencia=2026-09"]


def test_serra_4741500_ativa_ausente_em_agosto_e_um_em_setembro() -> None:
    linhas = _consultar(
        "select r.mes_referencia, sum(r.qtd_estabelecimentos) from {resumo} r "
        "join {dim_municipio} m using (sk_municipio) join {dim_cnae} c using (sk_cnae) "
        "where m.nome_municipio = 'Serra' and c.codigo_subclasse = '4741500' "
        "and r.sk_situacao_cadastral = 2 group by 1 order by 1"
    )
    assert linhas == [("2026-09", 1)]  # ausente em 2026-08 (a filial só aparece em 2026-09)


def test_soma_de_setembro_e_quinze_e_a_de_agosto_catorze() -> None:
    linhas = _consultar(
        "select mes_referencia, sum(qtd_estabelecimentos), min(sk_mes_referencia) from {resumo} "
        "group by 1 order by 1"
    )
    assert linhas == [("2026-08", 14, 20260801), ("2026-09", 15, 20260901)]


def test_reprocessar_sem_warehouse_preserva_a_particao_antiga(tmp_path: Path) -> None:
    """Apagar `warehouse.duckdb` e rodar 2026-09 de novo mantém a partição 2026-08 intacta."""
    copia = tmp_path / "dados"
    shutil.copytree(RAIZ, copia, ignore=shutil.ignore_patterns("_tmp"))
    (copia / "warehouse.duckdb").unlink(missing_ok=True)
    antiga = copia / "gold" / "fct_resumo_mensal" / "mes_referencia=2026-08" / "data_0.parquet"
    antes = antiga.read_bytes()
    env = {**os.environ, "RAIZ_DADOS": str(copia), "DBT_PROFILES_DIR": str(TRANSFORM)}
    env.pop("CAMINHO_DUCKDB", None)
    subprocess.run(
        [
            "uv", "run", "dbt", "build", "--target", "ci", "--select", "+fct_resumo_mensal",
            "--exclude", "resource_type:test resource_type:unit_test",
            "--vars", "{mes_referencia: 2026-09}", "--target-path", str(tmp_path / "target"),
        ],
        cwd=TRANSFORM, env=env, check=True, capture_output=True,
    )  # fmt: skip
    assert antiga.read_bytes() == antes
    linhas = _consultar(
        "select mes_referencia, sum(qtd_estabelecimentos) from {resumo} group by 1 order by 1",
        gold=copia / "gold",
    )
    assert linhas == [("2026-08", 14), ("2026-09", 15)]


def test_exposure_do_power_bi_depende_de_todas_as_dimensoes_e_fatos() -> None:
    manifesto = TRANSFORM / "target" / "manifest.json"
    if not manifesto.is_file():
        pytest.skip("rode `dbt build` antes")
    exposicoes = json.loads(manifesto.read_text(encoding="utf-8"))["exposures"]
    (exposicao,) = exposicoes.values()
    assert exposicao["type"] == "dashboard"
    modelos = {n.split(".")[-1] for n in exposicao["depends_on"]["nodes"]}
    assert modelos >= {
        "dim_data", "dim_municipio", "dim_cnae", "dim_natureza_juridica", "dim_porte",
        "dim_situacao_cadastral", "fct_estabelecimentos", "fct_resumo_mensal",
    }  # fmt: skip
