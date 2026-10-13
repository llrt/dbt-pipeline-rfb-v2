# ruff: noqa: E501
"""RBP-09 / DIC: cobertura de `description` nas colunas reais do warehouse e das fontes raw.

- Fontes (raw RFB, Base dos Dados e observabilidade) e gold (`marts/`): **100 %** das colunas reais.
- Demais modelos (staging, intermediate, observabilidade) e seeds: ≥ 98 % (RBP-09).

As colunas reais vêm do `catalog.json` (`dbt docs generate` sobre o `warehouse.duckdb` de `RAIZ_DADOS`,
fixture `manifesto_e_catalogo`) e, nas fontes raw, do próprio Parquet em `RAIZ_DADOS/raw`.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import duckdb
import pytest

MINIMO_GERAL = 0.98

pytestmark = pytest.mark.skipif(
    "RAIZ_DADOS" not in os.environ, reason="rode via make ci (exporta RAIZ_DADOS)"
)


def _sem_descricao(declaradas: dict, reais: list[str], rotulo: str) -> list[str]:
    colunas = {nome.lower(): c for nome, c in declaradas.items()}
    return [
        f"{rotulo}.{c}"
        for c in reais
        if not colunas.get(c.lower(), {}).get("description", "").strip()
    ]


def test_colunas_reais_de_modelos_e_seeds_tem_descricao(manifesto_e_catalogo) -> None:
    manifesto = json.loads(manifesto_e_catalogo[0].read_text(encoding="utf-8"))
    catalogo = json.loads(manifesto_e_catalogo[1].read_text(encoding="utf-8"))

    total, sem_descricao, sem_descricao_gold = 0, [], []
    for unique_id, no in catalogo["nodes"].items():
        declarado = manifesto["nodes"].get(unique_id)
        if declarado is None or declarado["resource_type"] not in ("model", "seed"):
            continue  # tabelas de `store_failures` e afins não são documentáveis
        faltam = _sem_descricao(declarado["columns"], list(no["columns"]), declarado["name"])
        total += len(no["columns"])
        sem_descricao += faltam
        if "/marts/" in declarado["original_file_path"]:
            sem_descricao_gold += faltam
    assert total > 0
    assert not sem_descricao_gold, f"gold exige 100 % de descrições; faltam: {sem_descricao_gold}"
    cobertura = 1 - len(sem_descricao) / total
    assert cobertura >= MINIMO_GERAL, (
        f"cobertura de descrições {cobertura:.1%} < {MINIMO_GERAL:.0%}; faltam: {sem_descricao}"
    )


def test_colunas_reais_das_fontes_tem_descricao(manifesto_e_catalogo) -> None:
    """Fontes: 100 % das colunas do Parquet raw (incluindo as técnicas da ingestão) são descritas."""
    manifesto = json.loads(manifesto_e_catalogo[0].read_text(encoding="utf-8"))
    catalogo = json.loads(manifesto_e_catalogo[1].read_text(encoding="utf-8"))
    raiz = Path(os.environ["RAIZ_DADOS"])

    faltam: list[str] = []
    conferidas = 0
    for unique_id, fonte in manifesto["sources"].items():
        if fonte["package_name"] != "rfb":
            continue
        rotulo = f"{fonte['source_name']}.{fonte['name']}"
        localizacao = str((fonte.get("config") or {}).get("meta", {}).get("external_location", ""))
        raw = re.search(r"/(raw/[^'\"]+)['\"]", localizacao)
        if raw:
            with duckdb.connect() as con:
                reais = [
                    linha[0]
                    for linha in con.execute(
                        f"describe select * from read_parquet('{raiz / raw.group(1)}', hive_partitioning=false)"
                    ).fetchall()
                ]
        else:
            reais = list(catalogo["sources"].get(unique_id, {}).get("columns", {}))
        assert reais, f"fonte {rotulo} sem colunas reais (rode o make ci antes)"
        conferidas += len(reais)
        faltam += _sem_descricao(fonte["columns"], reais, rotulo)
    assert conferidas > 100
    assert not faltam, f"fontes exigem 100 % de descrições; faltam: {faltam}"
