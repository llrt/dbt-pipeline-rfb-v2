"""Armazenamento remoto S3/Tigris: sync de `raw/`/`gold/` e secret DuckDB (ADR-0007).

A ingestão (EL) sempre lê/escreve localmente (`config.data_root`, ver `config.py`); este módulo
só entra em jogo quando `DATA_ROOT` é `s3://...`, para publicar o que já foi gravado localmente
(`rfb sync`, via boto3, como o `subir_arquivos_tigris.py` original) e para gerar o SQL de
`CREATE SECRET` que o DuckDB usa ao ler/escrever no bucket.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError

from rfb_pipeline.config import Config, CredenciaisS3, ler_credenciais_s3
from rfb_pipeline.errors import ErroIngestao

__all__ = ["sincronizar", "sql_create_secret"]

_CODIGOS_NAO_ENCONTRADO = {"404", "NoSuchKey", "NotFound"}


def sql_create_secret(config: Config, *, nome: str = "s3_secret") -> str:
    """SQL `CREATE SECRET` para o DuckDB ler/escrever no bucket S3/Tigris de `DATA_ROOT`.

    Credenciais vêm de `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/`AWS_ENDPOINT_URL_S3`
    (validadas em `carregar_config`); `REGION` é sempre `'auto'`; `URL_STYLE` vem de
    `S3_URL_STYLE` (padrão `vhost`); `USE_SSL` segue o esquema do endpoint.
    """
    if config.data_root_s3 is None:
        raise ErroIngestao("DATA_ROOT não é s3://; não há secret S3 a criar")
    creds = ler_credenciais_s3()
    return (
        f"CREATE OR REPLACE SECRET {nome} ("
        "TYPE s3, "
        f"KEY_ID '{creds.access_key_id}', "
        f"SECRET '{creds.secret_access_key}', "
        f"ENDPOINT '{creds.endpoint_sem_esquema}', "
        f"REGION '{creds.region}', "
        f"URL_STYLE '{creds.url_style}', "
        f"USE_SSL {'true' if creds.usa_ssl else 'false'}"
        ")"
    )


def _parse_s3_uri(uri: str) -> tuple[str, str]:
    sem_esquema = uri.removeprefix("s3://")
    bucket, _, prefixo = sem_esquema.partition("/")
    return bucket, prefixo.rstrip("/")


def _ja_sincronizado(s3: Any, bucket: str, chave: str, arquivo: Path) -> bool:
    """Verifica se o objeto já está no bucket com o mesmo tamanho (e MD5, quando aplicável)."""
    try:
        cabecalho = s3.head_object(Bucket=bucket, Key=chave)
    except ClientError as exc:
        codigo = exc.response.get("Error", {}).get("Code")
        if codigo in _CODIGOS_NAO_ENCONTRADO:
            return False
        raise
    if cabecalho["ContentLength"] != arquivo.stat().st_size:
        return False
    etag = cabecalho.get("ETag", "").strip('"')
    if not etag or "-" in etag:
        # upload multipart: ETag não é o MD5 simples do conteúdo; confia no tamanho batendo.
        return bool(etag)
    md5_local = hashlib.md5(arquivo.read_bytes(), usedforsecurity=False).hexdigest()
    return etag == md5_local


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

    Pula objetos cujo tamanho e ETag (MD5, quando não é upload multipart) já conferem no
    bucket, evitando reenviar o que não mudou. Retorna as chaves efetivamente enviadas.
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
            if not arquivo.is_file():
                continue
            relativa = arquivo.relative_to(config.data_root).as_posix()
            chave = f"{prefixo}/{relativa}" if prefixo else relativa
            if _ja_sincronizado(s3, bucket, chave, arquivo):
                continue
            s3.upload_file(str(arquivo), bucket, chave)
            enviados.append(chave)
    return enviados
