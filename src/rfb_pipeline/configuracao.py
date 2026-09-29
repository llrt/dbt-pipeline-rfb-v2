"""Configuração do pipeline: diretórios, URLs de origem e limiares de qualidade."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from rfb_pipeline.erros import ConfiguracaoInvalidaErro, CredenciaisS3FaltandoErro

RAIZ_DADOS_PADRAO = "./data"
_VARS_S3_OBRIGATORIAS = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_ENDPOINT_URL_S3")


@dataclass(frozen=True)
class CredenciaisS3:
    """Credenciais e endpoint S3/Tigris lidos do ambiente (ARCHITECTURE.md §4.4, ADR-0007)."""

    access_key_id: str
    secret_access_key: str
    endpoint_url: str
    url_style: str = "vhost"
    regiao: str = "auto"

    @property
    def endpoint_sem_esquema(self) -> str:
        return self.endpoint_url.removeprefix("https://").removeprefix("http://")

    @property
    def usa_ssl(self) -> bool:
        return not self.endpoint_url.startswith("http://")


def ler_credenciais_s3(env: Mapping[str, str] | None = None) -> CredenciaisS3:
    """Lê e valida `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/`AWS_ENDPOINT_URL_S3` do ambiente.

    Levanta `CredenciaisS3FaltandoErro`, citando cada variável faltante, se alguma das três
    estiver ausente ou vazia. `S3_URL_STYLE` (padrão `vhost`) é opcional.
    """
    if env is None:
        env = os.environ
    faltando = [v for v in _VARS_S3_OBRIGATORIAS if not env.get(v)]
    if faltando:
        raise CredenciaisS3FaltandoErro(faltando)
    return CredenciaisS3(
        access_key_id=env["AWS_ACCESS_KEY_ID"],
        secret_access_key=env["AWS_SECRET_ACCESS_KEY"],
        endpoint_url=env["AWS_ENDPOINT_URL_S3"],
        url_style=env.get("S3_URL_STYLE", "vhost"),
    )


@dataclass(frozen=True)
class Configuracao:
    raiz_dados: Path
    raiz_dados_uri: str
    raiz_dados_s3: str | None = None
    webdav_url: str = "https://arquivos.receitafederal.gov.br/public.php/webdav/"
    webdav_token: str = "YggdBLfdninEJX9"
    bd_base_url: str = "https://storage.googleapis.com/basedosdados-public/one-click-download/"
    hosts_permitidos: tuple[str, ...] = (
        "arquivos.receitafederal.gov.br",
        "storage.googleapis.com",
    )
    max_taxa_rejeito: float = 0.0001
    tempo_limite_s: float = 60.0
    tentativas: int = 3
    max_retomadas: int = 50
    tempo_limite_total_s: float = 3600.0
    velocidade_minima_bps: float = 50 * 1024
    janela_lentidao_s: float = 60.0
    duckdb_memory_limit: str = "8GB"
    duckdb_threads: int = 4

    @property
    def raw_dir(self) -> Path:
        return self.raiz_dados / "raw"

    def baixados_dir(self, mes: str) -> Path:
        return self.raiz_dados / "_downloads" / mes

    @property
    def manifestos_dir(self) -> Path:
        return self.raiz_dados / "_manifests"

    @property
    def rejeitos_dir(self) -> Path:
        return self.raw_dir / "_rejeitos"

    @property
    def gold_dir(self) -> Path:
        return self.raiz_dados / "gold"


_SOBRESCRITAS_NUMERICAS: tuple[tuple[str, str, type], ...] = (
    ("RFB_MAX_TAXA_REJEITO", "max_taxa_rejeito", float),
    ("RFB_VELOCIDADE_MINIMA_BPS", "velocidade_minima_bps", float),
    ("RFB_JANELA_LENTIDAO_S", "janela_lentidao_s", float),
    ("RFB_MAX_RETOMADAS", "max_retomadas", int),
    ("RFB_TIMEOUT_TOTAL_S", "tempo_limite_total_s", float),
    ("DUCKDB_THREADS", "duckdb_threads", int),
)


def _texto(env: Mapping[str, str], variavel: str) -> str | None:
    """Valor da variável, ou `None` se ausente ou vazia (variável vazia = padrão)."""
    valor = env.get(variavel)
    if valor is None or not valor.strip():
        return None
    return valor.strip()


def carregar_configuracao(env: Mapping[str, str] | None = None) -> Configuracao:
    """Monta a `Configuracao` a partir de variáveis de ambiente.

    Quando `env` é `None`, carrega `.env` (via python-dotenv) e lê `os.environ`. Variável vazia
    equivale a ausente (usa o padrão), para que `cp .env.example .env` não quebre nada.

    Quando `DATA_ROOT` é `s3://...` (ADR-0007), a ingestão (EL) continua lendo/escrevendo em um
    diretório **local**, `DATA_ROOT_LOCAL` (padrão `./data`): `configuracao.raiz_dados` sempre
    aponta para esse diretório local, e `configuracao.raiz_dados_s3` guarda a URI remota (usada por
    `rfb sincronizar` e pelo secret do DuckDB). Credenciais S3 são validadas já aqui, cedo,
    citando as variáveis faltantes.
    """
    if env is None:
        load_dotenv()
        env = os.environ

    raiz_dados_bruto = _texto(env, "DATA_ROOT") or RAIZ_DADOS_PADRAO
    if raiz_dados_bruto.startswith("s3://"):
        ler_credenciais_s3(env)
        raiz_dados_s3 = raiz_dados_bruto.rstrip("/")
        raiz_dados = Path(_texto(env, "DATA_ROOT_LOCAL") or RAIZ_DADOS_PADRAO).resolve()
        raiz_dados_uri = raiz_dados_s3
    else:
        raiz_dados_s3 = None
        raiz_dados = Path(raiz_dados_bruto).resolve()
        raiz_dados_uri = str(raiz_dados)

    sobrescritas: dict[str, object] = {}
    for variavel, campo, tipo in _SOBRESCRITAS_NUMERICAS:
        valor = _texto(env, variavel)
        if valor is not None:
            try:
                sobrescritas[campo] = tipo(valor)
            except ValueError:
                raise ConfiguracaoInvalidaErro(
                    variavel, valor, "número inteiro" if tipo is int else "número"
                ) from None
    memoria = _texto(env, "DUCKDB_MEMORY_LIMIT")
    if memoria is not None:
        sobrescritas["duckdb_memory_limit"] = memoria

    return Configuracao(
        raiz_dados=raiz_dados,
        raiz_dados_uri=raiz_dados_uri,
        raiz_dados_s3=raiz_dados_s3,
        **sobrescritas,
    )
