"""T42 (PUB-01): publica o gold das fixtures num `.duckdb` local e confere as contagens."""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pytest

from rfb_pipeline.publicacao import descobrir_datasets, publicar

pytestmark = pytest.mark.skipif(
    "RAIZ_DADOS" not in os.environ, reason="rode via make ci (exporta RAIZ_DADOS)"
)


def test_publicacao_local_tem_as_mesmas_contagens_do_gold(tmp_path: Path) -> None:
    gold = Path(os.environ["RAIZ_DADOS"]) / "gold"
    destino = tmp_path / "publicado.duckdb"
    publicadas = {t.nome: t.linhas for t in publicar(gold, str(destino), "rfb")}

    datasets = {d.nome: d for d in descobrir_datasets(gold)}
    assert set(publicadas) == set(datasets)
    assert "fct_resumo_mensal" in publicadas and "fct_estabelecimentos" in publicadas
    with duckdb.connect() as con:
        for nome, dataset in datasets.items():
            opcao = ", hive_partitioning = true" if dataset.particionado else ""
            esperado = con.execute(
                f"SELECT count(*) FROM read_parquet('{dataset.padrao}'{opcao})"
            ).fetchone()[0]
            assert publicadas[nome] == esperado, nome

    with duckdb.connect(str(destino), read_only=True) as con:
        meses = con.execute(
            "SELECT DISTINCT mes_referencia FROM fct_resumo_mensal ORDER BY 1"
        ).fetchall()
    assert [str(m[0]) for m in meses] == ["2026-08", "2026-09"]
