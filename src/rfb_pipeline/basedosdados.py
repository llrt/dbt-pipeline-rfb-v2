"""Download das tabelas da Base dos Dados (municipio, cnae_2, populacao, pib)."""

from __future__ import annotations

import shutil
import time
from collections.abc import Callable
from pathlib import Path

import httpx

from rfb_pipeline.config import Config
from rfb_pipeline.rfb_client import baixar_com_retry
from rfb_pipeline.schemas import TABELAS_BD


def baixar_tabelas_bd(
    config: Config,
    destino_dir: Path,
    http: httpx.Client | None = None,
    origem_local: Path | None = None,
    dormir: Callable[[float], None] = time.sleep,
) -> dict[str, Path]:
    """Baixa (ou copia de `origem_local`) as 4 tabelas da Base dos Dados.

    Retorna um dict `nome da tabela -> caminho do arquivo <nome>.csv.gz` em `destino_dir`.
    Com `origem_local`, copia `<origem_local>/bd/<nome>.csv.gz` em vez de baixar da rede.
    """
    destino_dir.mkdir(parents=True, exist_ok=True)
    resultado: dict[str, Path] = {}

    cliente_http = http if http is not None else httpx.Client(timeout=config.timeout_s)
    try:
        for nome, tabela in TABELAS_BD.items():
            destino = destino_dir / f"{nome}.csv.gz"
            if origem_local is not None:
                origem = origem_local / "bd" / f"{nome}.csv.gz"
                shutil.copyfile(origem, destino)
            else:
                url = f"{config.bd_base_url}{tabela.dataset}/{tabela.tabela}/{tabela.tabela}.csv.gz"
                baixar_com_retry(
                    cliente_http,
                    url,
                    destino,
                    tamanho_esperado=None,
                    tentativas=config.tentativas,
                    hosts_permitidos=config.hosts_permitidos,
                    dormir=dormir,
                )
            resultado[nome] = destino
    finally:
        if http is None:
            cliente_http.close()

    return resultado
