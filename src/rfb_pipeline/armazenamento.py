"""Armazenamento remoto S3/Tigris: sync de `raw/`/`gold/` e secret DuckDB (ADR-0007).

A ingestão (EL) sempre lê/escreve localmente (`config.data_root`, ver `configuracao.py`);
este módulo só entra em jogo quando `DATA_ROOT` é `s3://...`, para publicar o que já foi
gravado localmente
(`rfb sync`, via boto3, como o `subir_arquivos_tigris.py` original). O secret S3 do DuckDB no
dbt vem do profile `s3` (`transform/profiles.yml`), não deste módulo (ADR-0007).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError

from rfb_pipeline.configuracao import Config, CredenciaisS3, ler_credenciais_s3
from rfb_pipeline.erros import ErroIngestao
from rfb_pipeline.manifesto import sha256_arquivo

__all__ = ["sincronizar"]

_CODIGOS_NAO_ENCONTRADO = {"404", "NoSuchKey", "NotFound"}
_METADADO_SHA256 = "sha256"  # gravado como cabeçalho x-amz-meta-sha256


def _parse_s3_uri(uri: str) -> tuple[str, str]:
    sem_esquema = uri.removeprefix("s3://")
    bucket, _, prefixo = sem_esquema.partition("/")
    return bucket, prefixo.rstrip("/")


def _ja_sincronizado(s3: Any, bucket: str, chave: str, arquivo: Path, sha256: str) -> bool:
    """Objeto já no bucket com o mesmo tamanho **e** o mesmo sha256 (metadado do objeto).

    O ETag não serve: em upload multipart (todo Parquet real, > 8 MB) não é o MD5 do conteúdo.
    Objeto sem o metadado `sha256` (ex.: enviado por outra ferramenta) é reenviado.
    """
    try:
        cabecalho = s3.head_object(Bucket=bucket, Key=chave)
    except ClientError as exc:
        codigo = exc.response.get("Error", {}).get("Code")
        if codigo in _CODIGOS_NAO_ENCONTRADO:
            return False
        raise
    if cabecalho["ContentLength"] != arquivo.stat().st_size:
        return False
    metadados = {k.lower(): v for k, v in cabecalho.get("Metadata", {}).items()}
    return metadados.get(_METADADO_SHA256) == sha256


def _cliente_s3(creds: CredenciaisS3) -> Any:
    return boto3.client(
        "s3",
        aws_access_key_id=creds.access_key_id,
        aws_secret_access_key=creds.secret_access_key,
        endpoint_url=creds.endpoint_url,
        region_name=creds.region,
    )


def sincronizar(config: Config, *, cliente_s3: Any | None = None) -> list[str]:
    """Envia `raw/` e `gold/` de `config.data_root` (local) para `config.data_root_s3`.

    Pula objetos cujo tamanho e sha256 (metadado `x-amz-meta-sha256`) já conferem no bucket.
    Ignora nomes ocultos (`.tmp-*`). Retorna as chaves efetivamente enviadas.
    """
    if config.data_root_s3 is None:
        raise ErroIngestao("DATA_ROOT não é s3://; nada para sincronizar")

    s3 = cliente_s3 if cliente_s3 is not None else _cliente_s3(ler_credenciais_s3())
    bucket, prefixo = _parse_s3_uri(config.data_root_s3)

    enviados: list[str] = []
    for subpasta in ("raw", "gold"):
        base_local = config.data_root / subpasta
        if not base_local.is_dir():
            continue
        for arquivo in sorted(base_local.rglob("*")):
            relativa = arquivo.relative_to(config.data_root).as_posix()
            if not arquivo.is_file() or any(p.startswith(".") for p in relativa.split("/")):
                continue  # resíduos de execução interrompida (.tmp-*, .old-*) não sobem
            chave = f"{prefixo}/{relativa}" if prefixo else relativa
            sha256 = sha256_arquivo(arquivo)
            if _ja_sincronizado(s3, bucket, chave, arquivo, sha256):
                continue
            s3.upload_file(
                str(arquivo), bucket, chave, ExtraArgs={"Metadata": {_METADADO_SHA256: sha256}}
            )
            enviados.append(chave)
    return enviados
