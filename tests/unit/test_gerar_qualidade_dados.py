from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import gerar_qualidade_dados  # noqa: E402


def _teste(nome: str, arquivo: str, severidade: str, escopo: str, coluna: str | None) -> dict:
    return {
        "resource_type": "test",
        "package_name": "rfb",
        "name": nome,
        "original_file_path": arquivo,
        "column_name": coluna,
        "config": {"severity": severidade},
        "meta": {"escopo": escopo},
        "depends_on": {"nodes": ["model.rfb.dim_x"]},
        "test_metadata": {"name": "not_null", "kwargs": {"model": "m", "column_name": coluna}},
    }


def test_catalogo_lista_testes_por_etapa_com_severidade_e_escopo() -> None:
    manifesto = {
        "nodes": {
            "a": _teste(
                "not_null_dim_x_id", "models/marts/core/_core.yml", "ERROR", "adicao", "id"
            ),
            "b": _teste(
                "n_b", "models/staging/rfb/_rfb__sources.yml", "warn", "original", "codigo"
            ),
            "terceiros": {"resource_type": "test", "package_name": "dbt_utils", "name": "x"},
        },
        "unit_tests": {"u": {"name": "test_u", "model": "dim_x", "meta": {"escopo": "adicao"}}},
    }
    texto = gerar_qualidade_dados.gerar(manifesto)
    assert "| `dim_x.id` | `not_null` | error | adicao | — |" in texto
    assert "### Core (Depois)" in texto and "### Fontes (Antes)" in texto
    assert "| `test_u` |" in texto.replace("`dim_x` | `test_u`", "`test_u`")
    assert "dbt_utils" not in texto
