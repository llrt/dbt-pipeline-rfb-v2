"""Target dbt `s3` (R1-08): banco e temporários locais, fontes/gold em `s3://` (ADR-0007).

Sem credenciais reais: usa chaves fictícias. O que o teste afirma é o *profile* — o
`warehouse.duckdb` nasce em `DATA_ROOT_LOCAL` (nunca em `s3://...`), `external_root` aponta
para o bucket e credenciais ausentes são nomeadas — e não que o bucket exista. Se o
`INSTALL httpfs` falhar por falta de rede/cache, o teste é pulado.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
TRANSFORM = RAIZ / "transform"
DBT = Path(sys.executable).parent / "dbt"

pytestmark = pytest.mark.skipif(not DBT.exists(), reason="dbt não encontrado no venv")


def _dbt_debug(env_extra: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("AWS_", "DATA_ROOT", "DBT_"))}
    env["DBT_PROFILES_DIR"] = str(TRANSFORM)
    env.update(env_extra)
    return subprocess.run(
        [str(DBT), "debug", "--target", "s3"],
        cwd=TRANSFORM,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_debug_s3_banco_local_e_gold_no_bucket(tmp_path: Path) -> None:
    local = tmp_path / "local"
    local.mkdir()
    resultado = _dbt_debug(
        {
            "DATA_ROOT": "s3://bucket/x",
            "DATA_ROOT_LOCAL": str(local),
            "AWS_ACCESS_KEY_ID": "id-ficticio",
            "AWS_SECRET_ACCESS_KEY": "segredo-ficticio",
            "AWS_ENDPOINT_URL_S3": "https://fly.storage.tigris.dev",
        }
    )
    saida = resultado.stdout + resultado.stderr

    if resultado.returncode != 0 and "httpfs" in saida:
        pytest.skip("extensão httpfs indisponível (sem rede/cache)")
    assert "IO Error" not in saida
    assert "Cannot open file" not in saida
    assert resultado.returncode == 0, saida
    assert f"path: {local}/warehouse.duckdb" in saida
    assert "external_root: s3://bucket/x/gold" in saida
    assert (local / "warehouse.duckdb").is_file()


def test_debug_s3_sem_credenciais_nomeia_a_variavel(tmp_path: Path) -> None:
    resultado = _dbt_debug({"DATA_ROOT": "s3://bucket/x", "DATA_ROOT_LOCAL": str(tmp_path)})
    saida = resultado.stdout + resultado.stderr

    assert resultado.returncode != 0
    assert "AWS_ACCESS_KEY_ID" in saida
