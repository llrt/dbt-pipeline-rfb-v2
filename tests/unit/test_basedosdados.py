from __future__ import annotations

import base64
import gzip
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from rfb_pipeline.basedosdados import baixar_tabelas_bd
from rfb_pipeline.configuracao import Configuracao
from rfb_pipeline.erros import BaixaArquivoErro
from rfb_pipeline.esquemas import TABELAS_BD

BD_HOST = "basedosdados.org"
CONTEUDO_GZ = gzip.compress(b"a,b\n1,2\n")


def _configuracao() -> Configuracao:
    return Configuracao(raiz_dados=Path("/tmp/nao-usado"), raiz_dados_uri="/tmp/nao-usado")


def test_baixa_todas_as_tabelas(tmp_path: Path) -> None:
    urls_chamadas = []

    def handler(request: httpx.Request) -> httpx.Response:
        urls_chamadas.append(str(request.url))
        return httpx.Response(200, content=CONTEUDO_GZ)

    http = httpx.Client(transport=httpx.MockTransport(handler))
    destino_dir = tmp_path / "bd"

    resultado = baixar_tabelas_bd(_configuracao(), destino_dir, http=http)

    assert set(resultado) == set(TABELAS_BD)
    for nome, caminho in resultado.items():
        assert caminho == destino_dir / f"{nome}.csv.gz"
        assert caminho.read_bytes() == CONTEUDO_GZ
    assert len(urls_chamadas) == len(TABELAS_BD)
    assert all(
        url.startswith(f"https://{BD_HOST}/api/tables/downloadTable?") for url in urls_chamadas
    )


def _decodificar(url: str) -> dict[str, str]:
    consulta = parse_qs(urlsplit(url).query)
    return {k: base64.b64decode(v[0]).decode() for k, v in consulta.items()}


def test_url_leva_dataset_tabela_true_e_free_em_base64(tmp_path: Path) -> None:
    urls_chamadas = []

    def handler(request: httpx.Request) -> httpx.Response:
        urls_chamadas.append(str(request.url))
        return httpx.Response(200, content=CONTEUDO_GZ)

    http = httpx.Client(transport=httpx.MockTransport(handler))
    baixar_tabelas_bd(_configuracao(), tmp_path / "bd", http=http)

    decodificadas = [_decodificar(u) for u in urls_chamadas]
    assert {"p": "br_ibge_populacao", "q": "municipio", "d": "true", "s": "free"} in decodificadas
    # base64 literal (não só ida e volta) de "br_ibge_populacao"
    assert any("p=YnJfaWJnZV9wb3B1bGFjYW8=" in u for u in urls_chamadas)


def test_erro_500_da_api_vira_falha_de_download(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"message": "Error downloading the file"})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(BaixaArquivoErro):
        baixar_tabelas_bd(_configuracao(), tmp_path / "bd", http=http, dormir=lambda _s: None)
    assert list((tmp_path / "bd").glob("*")) == []


def test_conteudo_nao_gzip_e_recusado(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b'{"message": "ok mas nao e gzip"}')

    http = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(BaixaArquivoErro, match="não é gzip"):
        baixar_tabelas_bd(_configuracao(), tmp_path / "bd", http=http)
    assert list((tmp_path / "bd").glob("*.csv.gz")) == []


def test_host_legado_nao_e_permitido() -> None:
    assert "storage.googleapis.com" not in _configuracao().hosts_permitidos
    assert BD_HOST in _configuracao().hosts_permitidos


def test_falha_persistente_nao_deixa_arquivo_parcial(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("falha de rede", request=request)

    http = httpx.Client(transport=httpx.MockTransport(handler))
    destino_dir = tmp_path / "bd"

    with pytest.raises(BaixaArquivoErro):
        baixar_tabelas_bd(_configuracao(), destino_dir, http=http, dormir=lambda _s: None)

    arquivos_parciais = list(destino_dir.glob("*.part"))
    assert arquivos_parciais == []
    arquivos_finais = list(destino_dir.glob("*.csv.gz"))
    assert arquivos_finais == []


def test_origem_local_copia_em_vez_de_baixar(tmp_path: Path) -> None:
    origem_local = tmp_path / "fixtures"
    (origem_local / "bd").mkdir(parents=True)
    conteudos = {nome: f"{nome}-conteudo".encode() for nome in TABELAS_BD}
    for nome, conteudo in conteudos.items():
        (origem_local / "bd" / f"{nome}.csv.gz").write_bytes(conteudo)

    def falha_se_chamado(request: httpx.Request) -> httpx.Response:
        raise AssertionError("não deveria acessar a rede quando origem_local é fornecida")

    http = httpx.Client(transport=httpx.MockTransport(falha_se_chamado))
    destino_dir = tmp_path / "bd_destino"

    resultado = baixar_tabelas_bd(
        _configuracao(), destino_dir, http=http, origem_local=origem_local
    )

    for nome, conteudo in conteudos.items():
        assert resultado[nome].read_bytes() == conteudo
