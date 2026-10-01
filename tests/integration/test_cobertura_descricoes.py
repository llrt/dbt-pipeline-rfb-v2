"""RBP-09: ≥ 98 % das colunas reais (catálogo do warehouse) de modelos e seeds têm `description`.

Gera `catalog.json` com `dbt docs generate` sobre o `warehouse.duckdb` de `RAIZ_DADOS` (criado
pelo `make ci`), num diretório temporário, e o compara com as descrições do manifesto.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

TRANSFORM = Path(__file__).resolve().parents[2] / "transform"
MINIMO = 0.98

pytestmark = pytest.mark.skipif(
    "RAIZ_DADOS" not in os.environ, reason="rode via make ci (exporta RAIZ_DADOS)"
)


def test_colunas_reais_de_modelos_e_seeds_tem_descricao(tmp_path: Path) -> None:
    env = os.environ | {"DBT_PROFILES_DIR": str(TRANSFORM)}
    env.pop("CAMINHO_DUCKDB", None)
    resultado = subprocess.run(
        ["uv", "run", "dbt", "docs", "generate", "--target", "ci",
         "--target-path", str(tmp_path), "--log-path", str(tmp_path / "logs")],
        cwd=TRANSFORM, env=env, capture_output=True, text=True, check=False,
    )  # fmt: skip
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    catalogo = json.loads((tmp_path / "catalog.json").read_text(encoding="utf-8"))
    manifesto = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))

    total, sem_descricao = 0, []
    for unique_id, no in catalogo["nodes"].items():
        declarado = manifesto["nodes"].get(unique_id)
        if declarado is None or declarado["resource_type"] not in ("model", "seed"):
            continue  # tabelas de `store_failures` e afins não são documentáveis
        colunas = {nome.lower(): c for nome, c in declarado["columns"].items()}
        for nome in no["columns"]:
            total += 1
            if not colunas.get(nome.lower(), {}).get("description", "").strip():
                sem_descricao.append(f"{declarado['name']}.{nome}")
    assert total > 0
    cobertura = 1 - len(sem_descricao) / total
    assert cobertura >= MINIMO, (
        f"cobertura de descrições {cobertura:.1%} < {MINIMO:.0%}; faltam: {sem_descricao}"
    )
