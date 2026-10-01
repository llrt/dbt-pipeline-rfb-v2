"""RBP-07: `filtro_mes_referencia` aborta o `dbt compile` quando `mes_referencia` não é `AAAA-MM`."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

TRANSFORM = Path(__file__).resolve().parents[2] / "transform"


def _compilar(tmp_path: Path, mes: str) -> subprocess.CompletedProcess[str]:
    env = os.environ | {"RAIZ_DADOS": str(tmp_path), "DBT_PROFILES_DIR": str(TRANSFORM)}
    env.pop("CAMINHO_DUCKDB", None)
    return subprocess.run(
        ["uv", "run", "dbt", "compile", "--target", "ci", "--select", "stg_rfb__cnaes",
         "--vars", f"{{mes_referencia: '{mes}'}}", "--log-path", str(tmp_path / "logs")],
        cwd=TRANSFORM, env=env, capture_output=True, text=True, check=False,
    )  # fmt: skip


@pytest.mark.parametrize("mes", ["202610", "2026-9", "2026/09", "set-2026"])
def test_mes_referencia_fora_do_formato_aborta(tmp_path: Path, mes: str) -> None:
    resultado = _compilar(tmp_path, mes)
    saida = resultado.stdout + resultado.stderr
    assert resultado.returncode != 0, saida
    assert "var mes_referencia inválida" in saida


def test_mes_referencia_valido_compila(tmp_path: Path) -> None:
    resultado = _compilar(tmp_path, "2026-09")
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
