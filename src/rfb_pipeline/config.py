"""Configuração do pipeline: diretórios, URLs de origem e limiares de qualidade."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

DATA_ROOT_PADRAO = "./data"


@dataclass(frozen=True)
class Config:
    data_root: Path
    data_root_uri: str
    webdav_url: str = "https://arquivos.receitafederal.gov.br/public.php/webdav/"
    webdav_token: str = "YggdBLfdninEJX9"
    bd_base_url: str = "https://storage.googleapis.com/basedosdados-public/one-click-download/"
    hosts_permitidos: tuple[str, ...] = (
        "arquivos.receitafederal.gov.br",
        "storage.googleapis.com",
    )
    max_taxa_rejeito: float = 0.0001
    timeout_s: float = 60.0
    tentativas: int = 3
    duckdb_memory_limit: str = "8GB"
    duckdb_threads: int = 4

    @property
    def raw_dir(self) -> Path:
        return self.data_root / "raw"

    def downloads_dir(self, mes: str) -> Path:
        return self.data_root / "_downloads" / mes

    @property
    def manifests_dir(self) -> Path:
        return self.data_root / "_manifests"

    @property
    def rejeitos_dir(self) -> Path:
        return self.raw_dir / "_rejeitos"

    @property
    def gold_dir(self) -> Path:
        return self.data_root / "gold"


def carregar_config(env: Mapping[str, str] | None = None) -> Config:
    """Monta a `Config` a partir de variáveis de ambiente.

    Quando `env` é `None`, carrega `.env` (via python-dotenv) e lê `os.environ`.
    """
    if env is None:
        load_dotenv()
        env = os.environ

    data_root_bruto = env.get("DATA_ROOT", DATA_ROOT_PADRAO)
    if data_root_bruto.startswith("s3://"):
        data_root_uri = data_root_bruto
        data_root = Path(data_root_bruto)
    else:
        data_root = Path(data_root_bruto).resolve()
        data_root_uri = str(data_root)

    overrides: dict[str, object] = {}
    if "RFB_MAX_TAXA_REJEITO" in env:
        overrides["max_taxa_rejeito"] = float(env["RFB_MAX_TAXA_REJEITO"])
    if "DUCKDB_MEMORY_LIMIT" in env:
        overrides["duckdb_memory_limit"] = env["DUCKDB_MEMORY_LIMIT"]
    if "DUCKDB_THREADS" in env:
        overrides["duckdb_threads"] = int(env["DUCKDB_THREADS"])

    return Config(data_root=data_root, data_root_uri=data_root_uri, **overrides)
