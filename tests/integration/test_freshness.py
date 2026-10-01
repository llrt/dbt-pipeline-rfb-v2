"""RBP-04 / spec STG AC 8: `dbt source freshness` roda sobre o raw e reage a `_ingerido_em`.

Copia o raw do `make ci` (`RAIZ_DADOS`) para um diretório temporário e envelhece `_ingerido_em` das
`estabelecimentos` (a fonte vale pelo maior valor entre as partições).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import duckdb
import pytest

TRANSFORM = Path(__file__).resolve().parents[2] / "transform"

pytestmark = pytest.mark.skipif(
    "RAIZ_DADOS" not in os.environ, reason="rode via make ci (exporta RAIZ_DADOS)"
)


def _freshness(tmp_path: Path, dias: int | None) -> subprocess.CompletedProcess[str]:
    raiz = tmp_path / "dados"
    shutil.copytree(Path(os.environ["RAIZ_DADOS"]) / "raw", raiz / "raw")
    if dias is not None:
        for arquivo in (raiz / "raw" / "rfb" / "estabelecimentos").rglob("*.parquet"):
            novo = arquivo.with_suffix(".novo")
            duckdb.sql(
                f"copy (select * replace ((current_timestamp - interval '{dias} days')::timestamp "
                f"as _ingerido_em) from read_parquet('{arquivo}')) to '{novo}' (format parquet)"
            )
            novo.replace(arquivo)
    env = os.environ | {"RAIZ_DADOS": str(raiz), "DBT_PROFILES_DIR": str(TRANSFORM)}
    env.pop("CAMINHO_DUCKDB", None)
    return subprocess.run(
        ["uv", "run", "dbt", "source", "freshness", "--target", "ci",
         "--log-path", str(tmp_path / "logs")],
        cwd=TRANSFORM, env=env, capture_output=True, text=True, check=False,
    )  # fmt: skip


def test_fonte_recem_ingerida_passa(tmp_path: Path) -> None:
    resultado = _freshness(tmp_path, None)
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert "WARN freshness of rfb.estabelecimentos" not in resultado.stdout


def test_ingestao_de_40_dias_avisa(tmp_path: Path) -> None:
    resultado = _freshness(tmp_path, 40)
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert "WARN freshness of rfb.estabelecimentos" in resultado.stdout


def test_ingestao_de_70_dias_e_erro(tmp_path: Path) -> None:
    resultado = _freshness(tmp_path, 70)
    assert resultado.returncode != 0, resultado.stdout + resultado.stderr
    assert "ERROR STALE freshness of rfb.estabelecimentos" in resultado.stdout


def test_extrato_desatualizado_so_existe_fora_do_target_ci(tmp_path: Path) -> None:
    env = os.environ | {"RAIZ_DADOS": str(tmp_path), "DBT_PROFILES_DIR": str(TRANSFORM)}

    def listar(target: str) -> str:
        return subprocess.run(
            ["uv", "run", "dbt", "ls", "--target", target, "--resource-type", "test",
             "--select", "extrato_desatualizado", "--log-path", str(tmp_path / "logs")],
            cwd=TRANSFORM, env=env, capture_output=True, text=True, check=False,
        ).stdout  # fmt: skip

    assert "rfb.extrato_desatualizado" in listar("dev")
    assert "rfb.extrato_desatualizado" not in listar("ci")
