"""Configuração do pipeline: diretórios, URLs de origem e limiares de qualidade."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from rfb_pipeline.errors import CredenciaisS3FaltandoError

DATA_ROOT_PADRAO = "./data"
_VARS_S3_OBRIGATORIAS = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_ENDPOINT_URL_S3")


@dataclass(frozen=True)
class CredenciaisS3:
    """Credenciais e endpoint S3/Tigris lidos do ambiente (ARCHITECTURE.md §4.4, ADR-0007)."""

    access_key_id: str
    secret_access_key: str
    endpoint_url: str
    url_style: str = "vhost"
    region: str = "auto"

    @property
    def endpoint_sem_esquema(self) -> str:
        return self.endpoint_url.removeprefix("https://").removeprefix("http://")

    @property
    def usa_ssl(self) -> bool:
        return not self.endpoint_url.startswith("http://")


def ler_credenciais_s3(env: Mapping[str, str] | None = None) -> CredenciaisS3:
    """Lê e valida `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/`AWS_ENDPOINT_URL_S3` do ambiente.

    Levanta `CredenciaisS3FaltandoError`, citando cada variável faltante, se alguma das três
    estiver ausente ou vazia. `S3_URL_STYLE` (padrão `vhost`) é opcional.
    """
    if env is None:
        env = os.environ
    faltando = [v for v in _VARS_S3_OBRIGATORIAS if not env.get(v)]
    if faltando:
        raise CredenciaisS3FaltandoError(faltando)
    return CredenciaisS3(
        access_key_id=env["AWS_ACCESS_KEY_ID"],
        secret_access_key=env["AWS_SECRET_ACCESS_KEY"],
        endpoint_url=env["AWS_ENDPOINT_URL_S3"],
        url_style=env.get("S3_URL_STYLE", "vhost"),
    )


@dataclass(frozen=True)
class Config:
    data_root: Path
    data_root_uri: str
    data_root_s3: str | None = None
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
    velocidade_minima_bps: float = 50 * 1024
    janela_lentidao_s: float = 60.0
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

    Quando `DATA_ROOT` é `s3://...` (ADR-0007), a ingestão (EL) continua lendo/escrevendo em um
    diretório **local**, `DATA_ROOT_LOCAL` (padrão `./data`): `config.data_root` sempre aponta
    para esse diretório local, e `config.data_root_s3` guarda a URI remota (usada por `rfb sync`
    e pelo secret do DuckDB). Credenciais S3 são validadas já aqui, cedo, citando as variáveis
    faltantes.
    """
    if env is None:
        load_dotenv()
        env = os.environ

    data_root_bruto = env.get("DATA_ROOT", DATA_ROOT_PADRAO)
    if data_root_bruto.startswith("s3://"):
        ler_credenciais_s3(env)
        data_root_s3 = data_root_bruto.rstrip("/")
        data_root = Path(env.get("DATA_ROOT_LOCAL", DATA_ROOT_PADRAO)).resolve()
        data_root_uri = data_root_s3
    else:
        data_root_s3 = None
        data_root = Path(data_root_bruto).resolve()
        data_root_uri = str(data_root)

    overrides: dict[str, object] = {}
    if "RFB_MAX_TAXA_REJEITO" in env:
        overrides["max_taxa_rejeito"] = float(env["RFB_MAX_TAXA_REJEITO"])
    if "RFB_VELOCIDADE_MINIMA_BPS" in env:
        overrides["velocidade_minima_bps"] = float(env["RFB_VELOCIDADE_MINIMA_BPS"])
    if "RFB_JANELA_LENTIDAO_S" in env:
        overrides["janela_lentidao_s"] = float(env["RFB_JANELA_LENTIDAO_S"])
    if "DUCKDB_MEMORY_LIMIT" in env:
        overrides["duckdb_memory_limit"] = env["DUCKDB_MEMORY_LIMIT"]
    if "DUCKDB_THREADS" in env:
        overrides["duckdb_threads"] = int(env["DUCKDB_THREADS"])

    return Config(
        data_root=data_root, data_root_uri=data_root_uri, data_root_s3=data_root_s3, **overrides
    )
