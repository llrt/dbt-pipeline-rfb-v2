"""R3-05: `DBT_THREADS` (nós do dbt) e `DUCKDB_THREADS` (motor DuckDB) são variáveis distintas."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

TRANSFORM = Path(__file__).resolve().parents[2] / "transform"


def _dbt(tmp_path: Path, *args: str, threads: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in ("DBT_THREADS", "DUCKDB_THREADS")}
    env |= {"RAIZ_DADOS": str(tmp_path), "DBT_PROFILES_DIR": str(TRANSFORM), **threads}
    env.pop("CAMINHO_DUCKDB", None)
    return subprocess.run(
        ["uv", "run", "dbt", *args, "--target", "ci", "--log-path", str(tmp_path / "logs")],
        cwd=TRANSFORM, env=env, capture_output=True, text=True, check=False,
    )  # fmt: skip


def test_dbt_debug_passa_com_as_duas_variaveis(tmp_path: Path) -> None:
    resultado = _dbt(tmp_path, "debug", threads={"DBT_THREADS": "2", "DUCKDB_THREADS": "2"})
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert "All checks passed" in resultado.stdout


@pytest.mark.parametrize(("dbt", "duckdb"), [("2", "3"), ("3", "2")])
def test_duckdb_threads_chega_ao_motor_e_dbt_threads_ao_dbt(
    tmp_path: Path, dbt: str, duckdb: str
) -> None:
    resultado = _dbt(
        tmp_path,
        "show", "--inline", "select current_setting('threads') as n",
        threads={"DBT_THREADS": dbt, "DUCKDB_THREADS": duckdb},
    )  # fmt: skip
    saida = resultado.stdout + resultado.stderr
    assert resultado.returncode == 0, saida
    assert f"Concurrency: {dbt} threads" in saida
    assert f"| {duckdb} |" in saida.replace("  ", " ")


def test_temp_directory_do_profile_chega_ao_motor(tmp_path: Path) -> None:
    """RBP-01: `temp_directory` no topo do profile é ignorado; vale em `config_options` (B8).

    Em `settings`, o dbt-duckdb reaplica `SET temp_directory` a cada cursor novo, e o DuckDB recusa
    ("Cannot switch temporary directory after the current one has been used") depois do 1º spill —
    observado no build real de 2026-09 com seleção parcial e 8 threads.
    """
    resultado = _dbt(
        tmp_path,
        "show", "--inline", "select current_setting('temp_directory') like '%/_tmp' as ok",
        threads={"DBT_THREADS": "2", "DUCKDB_THREADS": "2"},
    )  # fmt: skip
    saida = resultado.stdout + resultado.stderr
    assert resultado.returncode == 0, saida
    assert "| True |" in saida.replace("  ", " ")
