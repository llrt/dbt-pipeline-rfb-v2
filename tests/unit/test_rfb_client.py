from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from rfb_pipeline.config import Config
from rfb_pipeline.errors import (
    DownloadError,
    ErroIngestao,
    HostNaoPermitidoError,
    MesInexistenteError,
    TamanhoDivergenteError,
)
from rfb_pipeline.rfb_client import (
    ArquivoRemoto,
    ClienteRFB,
    VelocidadeBaixaError,
    WebDAVIndisponivelError,
    baixar_com_retry,
)

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

    def test_taxa_abaixo_do_minimo_aborta_e_retoma_com_range(self, tmp_path: Path) -> None:
        conteudo_completo = b"0123456789" * 5  # 50 bytes
        primeira_parte = conteudo_completo[:10]
        segunda_parte = conteudo_completo[10:]
        destino = tmp_path / "Empresas0.zip"
        chamadas = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            chamadas["n"] += 1
            if chamadas["n"] == 1:
                assert "range" not in request.headers
                return httpx.Response(200, content=primeira_parte)
            assert request.headers.get("range") == f"bytes={len(primeira_parte)}-"
            return httpx.Response(
                206,
                content=segunda_parte,
                headers={
                    "Content-Range": (
                        f"bytes {len(primeira_parte)}-{len(conteudo_completo) - 1}/"
                        f"{len(conteudo_completo)}"
                    )
                },
            )

        http = httpx.Client(transport=httpx.MockTransport(handler))
        # 1a tentativa: inicio_janela=0.0, agora=100.0 apos escrever o unico chunk (10 B em
        # 100s = 0.1 B/s, abaixo do minimo) -> aborta com progresso (10 B gravados).
        # 2a tentativa (retomada via Range): inicio_janela=100.0, agora=100.0 -> sem estouro
        # de janela, conclui com sucesso.
        relogios = iter([0.0, 100.0, 100.0, 100.0])

        resultado = baixar_com_retry(
            http,
            "https://arquivos.receitafederal.gov.br/Empresas0.zip",
            destino,
            tamanho_esperado=len(conteudo_completo),
            tentativas=3,
            hosts_permitidos=("arquivos.receitafederal.gov.br",),
            dormir=lambda _s: None,
            velocidade_minima_bps=1000.0,
            janela_lentidao_s=60.0,
            relogio=lambda: next(relogios),
        )

        assert resultado.read_bytes() == conteudo_completo
        assert chamadas["n"] == 2

    def test_tentativas_sem_progresso_nao_conta_quando_ha_avanco(self, tmp_path: Path) -> None:
        """Cada tentativa avança 1 byte e aborta por lentidão; o progresso reseta o contador, então
        a ingestão continua tentando além do limite de `tentativas` enquanto houver avanço."""
        destino = tmp_path / "Empresas0.zip"
        chamadas = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            chamadas["n"] += 1
            offset = int(
                request.headers.get("range", "bytes=0-").removeprefix("bytes=").rstrip("-")
            )
            return httpx.Response(200 if offset == 0 else 206, content=b"x")

        http = httpx.Client(transport=httpx.MockTransport(handler))
        # A janela sempre estoura (agora - inicio >= janela) com taxa abaixo do mínimo, então
        # toda tentativa levanta VelocidadeBaixaError -- mas grava 1 byte antes de abortar, o
        # que reseta o contador de tentativas sem progresso a cada vez. Com `tentativas=2` isso
        # ultrapassaria o limite se o contador não fosse resetado; o relógio se esgota primeiro,
        # provando que o laço não parou em 2 tentativas.
        relogios = iter([0.0, 100.0] * 4)

        with pytest.raises(StopIteration):
            baixar_com_retry(
                http,
                "https://arquivos.receitafederal.gov.br/Empresas0.zip",
                destino,
                tamanho_esperado=None,
                tentativas=2,
                hosts_permitidos=("arquivos.receitafederal.gov.br",),
                dormir=lambda _s: None,
                velocidade_minima_bps=1000.0,
                janela_lentidao_s=60.0,
                relogio=lambda: next(relogios),
            )

        assert chamadas["n"] > 2

    def test_velocidade_baixa_error_mensagem(self) -> None:
        erro = VelocidadeBaixaError(taxa_bps=100.0, minima_bps=1000.0, janela_s=60.0)
        assert "100" in str(erro)
        assert "1000" in str(erro)


HOSTS = ("arquivos.receitafederal.gov.br",)
URL_ZIP = "https://arquivos.receitafederal.gov.br/Empresas0.zip"


def _baixar(http: httpx.Client, destino: Path, **kw: object) -> Path:
    args: dict[str, object] = dict(
        tamanho_esperado=None,
        tentativas=3,
        hosts_permitidos=HOSTS,
        dormir=lambda _s: None,
    )
    args.update(kw)
    return baixar_com_retry(http, URL_ZIP, destino, **args)


class TestResiliencia:
    def test_um_byte_por_conexao_para_no_teto_de_retomadas(self, tmp_path: Path) -> None:
        """R1-01: servidor gotejante (1 byte e derruba) gerava retomadas sem fim."""
        chamadas = {"n": 0}
        sonos: list[float] = []

        def handler(request: httpx.Request) -> httpx.Response:
            chamadas["n"] += 1

            class _Cai(httpx.SyncByteStream):
                def __iter__(self):
                    yield b"x"
                    raise httpx.ReadError("conexão derrubada")

            return httpx.Response(206 if "range" in request.headers else 200, stream=_Cai())

        http = httpx.Client(transport=httpx.MockTransport(handler))
        with pytest.raises(DownloadError) as exc_info:
            _baixar(
                http, tmp_path / "Empresas0.zip", tentativas=3, max_retomadas=7, dormir=sonos.append
            )

        assert chamadas["n"] == 7
        assert "7 retomadas" in str(exc_info.value)
        assert URL_ZIP in str(exc_info.value)
        assert len(sonos) == 6  # espera após cada tentativa com progresso, exceto a última
        assert all(s > 0 for s in sonos)
        assert not (tmp_path / "Empresas0.zip.part").exists()

    def test_teto_de_tempo_total_entre_tentativas(self, tmp_path: Path) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("fora do ar", request=request)

        http = httpx.Client(transport=httpx.MockTransport(handler))
        relogio_total = iter([0.0, 10.0, 20.0, 5000.0])

        with pytest.raises(DownloadError) as exc_info:
            _baixar(
                http,
                tmp_path / "Empresas0.zip",
                tentativas=100,
                timeout_total_s=100.0,
                relogio_total=lambda: next(relogio_total),
            )

        assert "tempo total" in str(exc_info.value)
        assert URL_ZIP in str(exc_info.value)

    def test_teto_de_tempo_total_durante_o_stream(self, tmp_path: Path) -> None:
        http = httpx.Client(
            transport=httpx.MockTransport(lambda r: httpx.Response(200, content=b"abc"))
        )
        relogio_total = iter([0.0, 999.0])

        with pytest.raises(DownloadError, match="tempo total"):
            _baixar(
                http,
                tmp_path / "Empresas0.zip",
                timeout_total_s=10.0,
                relogio_total=lambda: next(relogio_total),
            )

    def test_backoff_tambem_apos_tentativa_com_progresso(self, tmp_path: Path) -> None:
        conteudo = b"0123456789"
        chamadas = {"n": 0}
        sonos: list[float] = []

        def handler(request: httpx.Request) -> httpx.Response:
            chamadas["n"] += 1
            offset = int(request.headers.get("range", "bytes=0-").removeprefix("bytes=")[:-1])
            if chamadas["n"] < 3:

                class _Cai(httpx.SyncByteStream):
                    def __iter__(self):
                        yield conteudo[offset : offset + 3]
                        raise httpx.ReadError("cai")

                return httpx.Response(206 if offset else 200, stream=_Cai())
            return httpx.Response(206, content=conteudo[offset:])

        http = httpx.Client(transport=httpx.MockTransport(handler))
        destino = tmp_path / "Empresas0.zip"
        _baixar(http, destino, tamanho_esperado=len(conteudo), dormir=sonos.append)

        assert destino.read_bytes() == conteudo
        assert sonos == [1.0, 1.0]

    def test_erro_http_permanente_nao_e_repetido(self, tmp_path: Path) -> None:
        chamadas = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            chamadas["n"] += 1
            return httpx.Response(404)

        http = httpx.Client(transport=httpx.MockTransport(handler))
        with pytest.raises(DownloadError, match="Empresas0.zip"):
            _baixar(http, tmp_path / "Empresas0.zip")
        assert chamadas["n"] == 1


class TestIfRange:
    def test_retomada_envia_if_range_com_o_validador_do_inicio_do_download(
        self, tmp_path: Path
    ) -> None:
        conteudo = b"0123456789"
        vistos: list[dict[str, str]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            vistos.append({k: v for k, v in request.headers.items() if k in ("range", "if-range")})
            if len(vistos) == 1:

                class _Cai(httpx.SyncByteStream):
                    def __iter__(self):
                        yield conteudo[:4]
                        raise httpx.ReadError("cai")

                return httpx.Response(200, headers={"ETag": '"v1"'}, stream=_Cai())
            return httpx.Response(206, content=conteudo[4:])

        http = httpx.Client(transport=httpx.MockTransport(handler))
        destino = tmp_path / "Empresas0.zip"
        _baixar(http, destino, tamanho_esperado=len(conteudo))

        assert vistos[0] == {}
        assert vistos[1] == {"range": "bytes=4-", "if-range": '"v1"'}
        assert destino.read_bytes() == conteudo
        assert not list(tmp_path.glob("*.validador"))

    def test_usa_last_modified_quando_etag_e_fraco(self, tmp_path: Path) -> None:
        lm = "Tue, 15 Sep 2026 10:00:00 GMT"
        vistos: list[str | None] = []

        def handler(request: httpx.Request) -> httpx.Response:
            vistos.append(request.headers.get("if-range"))
            if len(vistos) == 1:

                class _Cai(httpx.SyncByteStream):
                    def __iter__(self):
                        yield b"ab"
                        raise httpx.ReadError("cai")

                return httpx.Response(
                    200, headers={"ETag": 'W/"fraco"', "Last-Modified": lm}, stream=_Cai()
                )
            return httpx.Response(206, content=b"cd")

        http = httpx.Client(transport=httpx.MockTransport(handler))
        _baixar(http, tmp_path / "Empresas0.zip", tamanho_esperado=4)
        assert vistos == [None, lm]

    def test_200_a_pedido_com_range_reinicia_do_zero(self, tmp_path: Path) -> None:
        novo = b"CONTEUDO-NOVO"
        destino = tmp_path / "Empresas0.zip"
        (tmp_path / "Empresas0.zip.part").write_bytes(b"velho")
        (tmp_path / "Empresas0.zip.part.validador").write_text('"v1"', encoding="utf-8")

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.headers["if-range"] == '"v1"'
            return httpx.Response(200, headers={"ETag": '"v2"'}, content=novo)

        http = httpx.Client(transport=httpx.MockTransport(handler))
        _baixar(http, destino, tamanho_esperado=len(novo))

        assert destino.read_bytes() == novo

    def test_416_recomeca_do_zero(self, tmp_path: Path) -> None:
        conteudo = b"0123456789"
        (tmp_path / "Empresas0.zip.part").write_bytes(b"x" * 20)  # maior que o remoto
        chamadas = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            chamadas["n"] += 1
            if "range" in request.headers:
                return httpx.Response(416)
            return httpx.Response(200, content=conteudo)

        http = httpx.Client(transport=httpx.MockTransport(handler))
        destino = tmp_path / "Empresas0.zip"
        _baixar(http, destino, tamanho_esperado=None)

        assert destino.read_bytes() == conteudo
        assert chamadas["n"] == 2

    def test_part_ja_completo_nao_faz_requisicao(self, tmp_path: Path) -> None:
        (tmp_path / "Empresas0.zip.part").write_bytes(b"completo")
        http = httpx.Client(transport=httpx.MockTransport(_sem_chamadas))
        destino = tmp_path / "Empresas0.zip"
        _baixar(http, destino, tamanho_esperado=len(b"completo"))
        assert destino.read_bytes() == b"completo"


class TestPropfindResiliente:
    def test_propfind_repete_e_recupera(self) -> None:
        xml = _multistatus([("/public.php/webdav/2026-09/", None)])
        chamadas = {"n": 0}
        sonos: list[float] = []

        def handler(request: httpx.Request) -> httpx.Response:
            chamadas["n"] += 1
            if chamadas["n"] < 3:
                raise httpx.ConnectError("fora", request=request)
            return httpx.Response(207, text=xml)

        http = httpx.Client(transport=httpx.MockTransport(handler))
        cliente = ClienteRFB(_config(), http=http, dormir=sonos.append)

        assert cliente.listar_meses() == ["2026-09"]
        assert chamadas["n"] == 3
        assert sonos == [1.0, 2.0]

    def test_propfind_inacessivel_vira_erro_de_ingestao_com_url(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("[Errno 8] nodename nor servname", request=request)

        http = httpx.Client(transport=httpx.MockTransport(handler))
        cliente = ClienteRFB(_config(), http=http, dormir=lambda _s: None)

        with pytest.raises(WebDAVIndisponivelError) as exc_info:
            cliente.listar_meses()

        assert WEBDAV_URL in str(exc_info.value)
        assert isinstance(exc_info.value, ErroIngestao)

    def test_propfind_5xx_esgota_tentativas(self) -> None:
        chamadas = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            chamadas["n"] += 1
            return httpx.Response(503)

        http = httpx.Client(transport=httpx.MockTransport(handler))
        cliente = ClienteRFB(_config(tentativas=4), http=http, dormir=lambda _s: None)

        with pytest.raises(WebDAVIndisponivelError, match="503"):
            cliente.listar_meses()
        assert chamadas["n"] == 4

    def test_propfind_401_nao_e_repetido(self) -> None:
        chamadas = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            chamadas["n"] += 1
            return httpx.Response(401)

        http = httpx.Client(transport=httpx.MockTransport(handler))
        cliente = ClienteRFB(_config(), http=http, dormir=lambda _s: None)
        with pytest.raises(WebDAVIndisponivelError):
            cliente.listar_meses()
        assert chamadas["n"] == 1


class TestTamanhoAusente:
    def test_getcontentlength_ausente_vira_none_com_aviso(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        raiz = _multistatus([("/public.php/webdav/2026-09/", None)])
        mes = (
            '<d:multistatus xmlns:d="DAV:"><d:response><d:href>/public.php/webdav/2026-09/'
            "Empresas0.zip</d:href><d:propstat><d:prop/></d:propstat></d:response></d:multistatus>"
        )

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(207, text=raiz if str(request.url) == WEBDAV_URL else mes)

        cliente = ClienteRFB(_config(), http=httpx.Client(transport=httpx.MockTransport(handler)))

        assert cliente.listar_arquivos("2026-09") == [ArquivoRemoto("Empresas0.zip", None)]
        assert "Empresas0.zip" in capsys.readouterr().err

    def test_download_sem_tamanho_esperado_nao_checa_tamanho(self, tmp_path: Path) -> None:
        http = httpx.Client(
            transport=httpx.MockTransport(lambda r: httpx.Response(200, content=b"ab"))
        )
        destino = tmp_path / "Empresas0.zip"
        _baixar(http, destino, tamanho_esperado=None)
        assert destino.read_bytes() == b"ab"
