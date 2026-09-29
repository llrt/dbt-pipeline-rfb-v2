from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from rfb_pipeline.basedosdados import baixar_tabelas_bd
from rfb_pipeline.configuracao import Config
from rfb_pipeline.erros import DownloadError

BD_HOST = "storage.googleapis.com"


def _config() -> Config:
    return Config(data_root=Path("/tmp/nao-usado"), data_root_uri="/tmp/nao-usado")


def test_baixa_as_quatro_tabelas(tmp_path: Path) -> None:
    urls_chamadas = []

    def handler(request: httpx.Request) -> httpx.Response:
        urls_chamadas.append(str(request.url))
        return httpx.Response(200, content=b"conteudo-gz")

    http = httpx.Client(transport=httpx.MockTransport(handler))
    destino_dir = tmp_path / "bd"

    resultado = baixar_tabelas_bd(_config(), destino_dir, http=http)

    assert set(resultado) == {"municipio", "cnae_2", "populacao", "pib"}
    for nome, caminho in resultado.items():
        assert caminho == destino_dir / f"{nome}.csv.gz"
        assert caminho.read_bytes() == b"conteudo-gz"
    assert len(urls_chamadas) == 4
    assert all(url.startswith(f"https://{BD_HOST}/") for url in urls_chamadas)


def test_falha_persistente_nao_deixa_arquivo_parcial(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("falha de rede", request=request)

    http = httpx.Client(transport=httpx.MockTransport(handler))
    destino_dir = tmp_path / "bd"

    with pytest.raises(DownloadError):
        baixar_tabelas_bd(_config(), destino_dir, http=http, dormir=lambda _s: None)

    arquivos_parciais = list(destino_dir.glob("*.part"))
    assert arquivos_parciais == []
    arquivos_finais = list(destino_dir.glob("*.csv.gz"))
    assert arquivos_finais == []


def test_origem_local_copia_em_vez_de_baixar(tmp_path: Path) -> None:
    origem_local = tmp_path / "fixtures"
    (origem_local / "bd").mkdir(parents=True)
    conteudos = {
        "municipio": b"municipio-conteudo",
        "cnae_2": b"cnae2-conteudo",
        "populacao": b"populacao-conteudo",
        "pib": b"pib-conteudo",
    }
    for nome, conteudo in conteudos.items():
        (origem_local / "bd" / f"{nome}.csv.gz").write_bytes(conteudo)

    def falha_se_chamado(request: httpx.Request) -> httpx.Response:
        raise AssertionError("não deveria acessar a rede quando origem_local é fornecida")

    http = httpx.Client(transport=httpx.MockTransport(falha_se_chamado))
    destino_dir = tmp_path / "bd_destino"

    resultado = baixar_tabelas_bd(_config(), destino_dir, http=http, origem_local=origem_local)

    for nome, conteudo in conteudos.items():
        assert resultado[nome].read_bytes() == conteudo
