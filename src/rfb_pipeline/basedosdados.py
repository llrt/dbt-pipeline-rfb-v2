"""Download das tabelas da Base dos Dados pela API `downloadTable` (ADR-0015)."""

from __future__ import annotations

import base64
import shutil
import time
from collections.abc import Callable
from pathlib import Path

import httpx

from rfb_pipeline.cliente_rfb import baixar_com_retentativas
from rfb_pipeline.configuracao import Configuracao
from rfb_pipeline.erros import BaixaArquivoErro
from rfb_pipeline.esquemas import TABELAS_BD, TabelaBD

_MAGIA_GZIP = b"\x1f\x8b"


def _b64(texto: str) -> str:
    return base64.b64encode(texto.encode("utf-8")).decode("ascii")


def url_download_bd(base_url: str, tabela: TabelaBD) -> str:
    """URL da API `downloadTable`: dataset, tabela, `true` e `free` em base64 (≤ 100 MB, grátis)."""
    return (
        f"{base_url}?p={_b64(tabela.dataset)}&q={_b64(tabela.tabela)}"
        f"&d={_b64('true')}&s={_b64('free')}"
    )


def baixar_tabelas_bd(
    configuracao: Configuracao,
    destino_dir: Path,
    http: httpx.Client | None = None,
    origem_local: Path | None = None,
    dormir: Callable[[float], None] = time.sleep,
) -> dict[str, Path]:
    """Baixa (ou copia de `origem_local`) todas as tabelas de `TABELAS_BD` da Base dos Dados.

    Retorna um dict `nome da tabela -> caminho do arquivo <nome>.csv.gz` em `destino_dir`.
    Com `origem_local`, copia `<origem_local>/bd/<nome>.csv.gz` em vez de baixar da rede.
    """
    destino_dir.mkdir(parents=True, exist_ok=True)
    resultado: dict[str, Path] = {}

    cliente_http = http if http is not None else httpx.Client(timeout=configuracao.tempo_limite_s)
    try:
        for nome, tabela in TABELAS_BD.items():
            destino = destino_dir / f"{nome}.csv.gz"
            if origem_local is not None:
                origem = origem_local / "bd" / f"{nome}.csv.gz"
                shutil.copyfile(origem, destino)
            else:
                url = url_download_bd(configuracao.bd_base_url, tabela)
                baixar_com_retentativas(
                    cliente_http,
                    url,
                    destino,
                    tamanho_esperado=None,
                    tentativas=configuracao.tentativas,
                    hosts_permitidos=configuracao.hosts_permitidos,
                    dormir=dormir,
                    max_retomadas=configuracao.max_retomadas,
                    tempo_limite_total_s=configuracao.tempo_limite_total_s,
                )
                _exigir_gzip(destino, url)
            resultado[nome] = destino
    finally:
        if http is None:
            cliente_http.close()

    return resultado


def _exigir_gzip(destino: Path, url: str) -> None:
    """A API pode responder 200 com corpo que não é gzip; recusa e não deixa o arquivo."""
    with destino.open("rb") as fh:
        cabecalho = fh.read(2)
    if cabecalho != _MAGIA_GZIP:
        destino.unlink(missing_ok=True)
        raise BaixaArquivoErro(destino.name, f"conteúdo não é gzip ({url})")
