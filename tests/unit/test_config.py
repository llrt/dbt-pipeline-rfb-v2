from __future__ import annotations

from pathlib import Path

from rfb_pipeline.config import carregar_config


def test_carregar_config_usa_padroes_sem_overrides(tmp_path: Path) -> None:
    config = carregar_config(env={"DATA_ROOT": str(tmp_path / "data")})

    assert config.data_root == (tmp_path / "data").resolve()
    assert config.max_taxa_rejeito == 0.0001
    assert config.duckdb_memory_limit == "8GB"
    assert config.duckdb_threads == 4


def test_carregar_config_le_overrides_do_ambiente(tmp_path: Path) -> None:
    env = {
        "DATA_ROOT": str(tmp_path / "data"),
        "RFB_MAX_TAXA_REJEITO": "0.05",
        "DUCKDB_MEMORY_LIMIT": "2GB",
        "DUCKDB_THREADS": "8",
    }

    config = carregar_config(env=env)

    assert config.max_taxa_rejeito == 0.05
    assert config.duckdb_memory_limit == "2GB"
    assert config.duckdb_threads == 8


def test_carregar_config_data_root_s3_preserva_uri_e_nao_falha() -> None:
    config = carregar_config(env={"DATA_ROOT": "s3://meu-bucket/prefixo"})

    assert config.data_root_uri == "s3://meu-bucket/prefixo"


def test_config_dirs_derivados_de_data_root(tmp_path: Path) -> None:
    config = carregar_config(env={"DATA_ROOT": str(tmp_path)})

    assert config.raw_dir == tmp_path / "raw"
    assert config.manifests_dir == tmp_path / "_manifests"
    assert config.rejeitos_dir == tmp_path / "raw" / "_rejeitos"
    assert config.gold_dir == tmp_path / "gold"
    assert config.downloads_dir("2026-09") == tmp_path / "_downloads" / "2026-09"
