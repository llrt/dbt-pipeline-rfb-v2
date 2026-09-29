"""Download das tabelas da Base dos Dados (municipio, cnae_2, populacao, pib)."""

from __future__ import annotations

import shutil
import time
from collections.abc import Callable
from pathlib import Path

import httpx

from rfb_pipeline.cliente_rfb import baixar_com_retentativas
from rfb_pipeline.configuracao import Configuracao
from rfb_pipeline.esquemas import TABELAS_BD


def baixar_tabelas_bd(
    configuracao: Configuracao,
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

    cliente_http = http if http is not None else httpx.Client(timeout=configuracao.tempo_limite_s)
    try:
        for nome, tabela in TABELAS_BD.items():
            destino = destino_dir / f"{nome}.csv.gz"
            if origem_local is not None:
                origem = origem_local / "bd" / f"{nome}.csv.gz"
                shutil.copyfile(origem, destino)
            else:
                caminho_remoto = f"{tabela.dataset}/{tabela.tabela}/{tabela.tabela}.csv.gz"
                url = f"{configuracao.bd_base_url}{caminho_remoto}"
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
            resultado[nome] = destino
    finally:
        if http is None:
            cliente_http.close()

    return resultado
