from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from rfb_pipeline.config import Config
from rfb_pipeline.errors import (
    DownloadError,
    HostNaoPermitidoError,
    MesInexistenteError,
    TamanhoDivergenteError,
)
from rfb_pipeline.rfb_client import ArquivoRemoto, ClienteRFB, baixar_com_retry

WEBDAV_URL = "https://arquivos.receitafederal.gov.br/public.php/webdav/"


def _config(**overrides: object) -> Config:
    base = dict(data_root=Path("/tmp/nao-usado"), data_root_uri="/tmp/nao-usado")
    base.update(overrides)
    return Config(**base)


def _multistatus(entries: list[tuple[str, int | None]]) -> str:
    partes = ['<?xml version="1.0" encoding="utf-8"?>', '<d:multistatus xmlns:d="DAV:">']
    for href, tamanho in entries:
        prop = (
            "<d:resourcetype><d:collection/></d:resourcetype>"
            if tamanho is None
            else (f"<d:getcontentlength>{tamanho}</d:getcontentlength>")
        )
        partes.append(
            f"<d:response><d:href>{href}</d:href><d:propstat><d:prop>{prop}</d:prop>"
            "<d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>"
        )
    partes.append("</d:multistatus>")
    return "".join(partes)


def _sem_chamadas(request: httpx.Request) -> httpx.Response:
    raise AssertionError(f"não deveria ter feito requisição: {request.url}")


class TestListarMeses:
    def test_lista_apenas_pastas_yyyy_mm_ordenadas(self, tmp_path: Path) -> None:
        xml = _multistatus(
            [
                ("/public.php/webdav/", None),
                ("/public.php/webdav/2026-08/", None),
                ("/public.php/webdav/2025-12/", None),
                ("/public.php/webdav/2026-09/", None),
                ("/public.php/webdav/leiame.txt", 10),
            ]
        )

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "PROPFIND"
            assert str(request.url) == WEBDAV_URL
            return httpx.Response(207, text=xml)

        http = httpx.Client(transport=httpx.MockTransport(handler))
        cliente = ClienteRFB(_config(), http=http)

        assert cliente.listar_meses() == ["2025-12", "2026-08", "2026-09"]

    def test_mes_mais_recente_e_o_ultimo_ordenado(self, tmp_path: Path) -> None:
        xml = _multistatus(
            [
                ("/public.php/webdav/2025-12/", None),
                ("/public.php/webdav/2026-09/", None),
            ]
        )
        http = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(207, text=xml)))
        cliente = ClienteRFB(_config(), http=http)

        assert cliente.mes_mais_recente() == "2026-09"


class TestListarArquivos:
    def test_mes_inexistente_levanta_erro_com_disponiveis(self, tmp_path: Path) -> None:
        xml_raiz = _multistatus([("/public.php/webdav/2026-09/", None)])
        http = httpx.Client(
            transport=httpx.MockTransport(lambda r: httpx.Response(207, text=xml_raiz))
        )
        cliente = ClienteRFB(_config(), http=http)

        with pytest.raises(MesInexistenteError) as exc_info:
            cliente.listar_arquivos("2020-01")

        assert exc_info.value.mes == "2020-01"
        assert exc_info.value.disponiveis == ["2026-09"]
        assert "2026-09" in str(exc_info.value)

    def test_socios_nunca_e_listado(self, tmp_path: Path) -> None:
        xml_raiz = _multistatus([("/public.php/webdav/2026-09/", None)])
        xml_mes = _multistatus(
            [
                ("/public.php/webdav/2026-09/", None),
                ("/public.php/webdav/2026-09/Empresas0.zip", 1000),
                ("/public.php/webdav/2026-09/Socios0.zip", 999999),
                ("/public.php/webdav/2026-09/Socios1.zip", 999999),
            ]
        )

        def handler(request: httpx.Request) -> httpx.Response:
            if str(request.url) == WEBDAV_URL:
                return httpx.Response(207, text=xml_raiz)
            return httpx.Response(207, text=xml_mes)

        http = httpx.Client(transport=httpx.MockTransport(handler))
        cliente = ClienteRFB(_config(), http=http)

        arquivos = cliente.listar_arquivos("2026-09")

        assert arquivos == [ArquivoRemoto(nome="Empresas0.zip", tamanho=1000)]
        assert all(not a.nome.startswith("Socios") for a in arquivos)


class TestBaixarComRetry:
    def test_host_fora_da_allowlist_e_recusado(self, tmp_path: Path) -> None:
        http = httpx.Client(transport=httpx.MockTransport(_sem_chamadas))

        with pytest.raises(HostNaoPermitidoError):
            baixar_com_retry(
                http,
                "https://host-nao-permitido.example.com/arquivo.zip",
                tmp_path / "arquivo.zip",
                tamanho_esperado=10,
                tentativas=3,
                hosts_permitidos=("arquivos.receitafederal.gov.br",),
                dormir=lambda _s: None,
            )

    def test_tamanho_divergente_apaga_arquivo_e_leva_erro(self, tmp_path: Path) -> None:
        conteudo = b"conteudo-menor"
        http = httpx.Client(
            transport=httpx.MockTransport(lambda r: httpx.Response(200, content=conteudo))
        )
        destino = tmp_path / "Empresas0.zip"

        with pytest.raises(TamanhoDivergenteError) as exc_info:
            baixar_com_retry(
                http,
                "https://arquivos.receitafederal.gov.br/x.zip",
                destino,
                tamanho_esperado=len(conteudo) + 100,
                tentativas=1,
                hosts_permitidos=("arquivos.receitafederal.gov.br",),
                dormir=lambda _s: None,
            )

        assert exc_info.value.esperado == len(conteudo) + 100
        assert exc_info.value.obtido == len(conteudo)
        assert not destino.exists()
        assert not (tmp_path / "Empresas0.zip.part").exists()

    def test_tres_falhas_leva_download_error_citando_arquivo(self, tmp_path: Path) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("falha de rede", request=request)

        http = httpx.Client(transport=httpx.MockTransport(handler))
        sonos = []

        with pytest.raises(DownloadError) as exc_info:
            baixar_com_retry(
                http,
                "https://arquivos.receitafederal.gov.br/Empresas0.zip",
                tmp_path / "Empresas0.zip",
                tamanho_esperado=None,
                tentativas=3,
                hosts_permitidos=("arquivos.receitafederal.gov.br",),
                dormir=sonos.append,
            )

        assert "Empresas0.zip" in str(exc_info.value)
        assert sonos == [1, 2]  # backoff exponencial entre as 3 tentativas
        assert not (tmp_path / "Empresas0.zip.part").exists()

    def test_sucesso_apos_duas_falhas(self, tmp_path: Path) -> None:
        conteudo = b"conteudo-final"
        chamadas = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            chamadas["n"] += 1
            if chamadas["n"] < 3:
                raise httpx.ConnectError("falha de rede", request=request)
            return httpx.Response(200, content=conteudo)

        http = httpx.Client(transport=httpx.MockTransport(handler))
        destino = tmp_path / "Empresas0.zip"

        resultado = baixar_com_retry(
            http,
            "https://arquivos.receitafederal.gov.br/Empresas0.zip",
            destino,
            tamanho_esperado=len(conteudo),
            tentativas=3,
            hosts_permitidos=("arquivos.receitafederal.gov.br",),
            dormir=lambda _s: None,
        )

        assert resultado == destino
        assert destino.read_bytes() == conteudo
        assert chamadas["n"] == 3

    def test_retomada_com_range_quando_part_existe(self, tmp_path: Path) -> None:
        conteudo_completo = b"0123456789"
        destino = tmp_path / "Empresas0.zip"
        parcial = tmp_path / "Empresas0.zip.part"
        parcial.write_bytes(conteudo_completo[:4])

        def handler(request: httpx.Request) -> httpx.Response:
            range_header = request.headers.get("range")
            assert range_header == "bytes=4-"
            return httpx.Response(
                206,
                content=conteudo_completo[4:],
                headers={"Content-Range": f"bytes 4-9/{len(conteudo_completo)}"},
            )

        http = httpx.Client(transport=httpx.MockTransport(handler))

        resultado = baixar_com_retry(
            http,
            "https://arquivos.receitafederal.gov.br/Empresas0.zip",
            destino,
            tamanho_esperado=len(conteudo_completo),
            tentativas=1,
            hosts_permitidos=("arquivos.receitafederal.gov.br",),
            dormir=lambda _s: None,
        )

        assert resultado.read_bytes() == conteudo_completo
