"""Cliente WebDAV da RFB: listagem de meses/arquivos e baixa resiliente."""

from __future__ import annotations

import re
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx

from rfb_pipeline.configuracao import Configuracao
from rfb_pipeline.erros import (
    BaixaArquivoErro,
    ErroIngestao,
    HostNaoPermitidoErro,
    MesInexistenteErro,
    TamanhoDivergenteErro,
    WebDAVIndisponivelErro,
)

__all__ = [
    "ArquivoRemoto",
    "ClienteRFB",
    "BaixaArquivoErro",
    "ErroIngestao",
    "HostNaoPermitidoErro",
    "MesInexistenteErro",
    "TamanhoDivergenteErro",
    "VelocidadeBaixaErro",
    "WebDAVIndisponivelErro",
    "baixar_com_retentativas",
]

_DAV_NS = {"d": "DAV:"}
_MES_RE = re.compile(r"^\d{4}-\d{2}$")


class VelocidadeBaixaErro(Exception):
    """A taxa de baixa ficou abaixo do mínimo configurado por tempo demais.

    Levantada dentro de uma tentativa (não é um `ErroIngestao` de borda): o chamador de
    `baixar_com_retentativas` a trata como qualquer outra falha de tentativa, decidindo se houve
    progresso (bytes novos no `.part`) para resetar o contador de tentativas sem avanço.
    """

    def __init__(self, taxa_bps: float, minima_bps: float, janela_s: float) -> None:
        self.taxa_bps = taxa_bps
        super().__init__(
            f"taxa de baixa {taxa_bps:.0f} B/s abaixo do mínimo {minima_bps:.0f} B/s "
            f"por mais de {janela_s:.0f}s"
        )


class _PrazoExcedido(Exception):
    """O teto de tempo total da baixa foi atingido (interno a `baixar_com_retentativas`)."""


@dataclass(frozen=True)
class ArquivoRemoto:
    nome: str
    tamanho: int | None  # None: o servidor não anunciou `getcontentlength`


def _verificar_host_permitido(url: str, hosts_permitidos: tuple[str, ...]) -> None:
    host = urllib.parse.urlsplit(url).hostname or ""
    if host not in hosts_permitidos:
        raise HostNaoPermitidoErro(host, hosts_permitidos)


def _erro_permanente(exc: Exception) -> bool:
    """4xx (exceto timeout, 416 e limite de taxa) não melhora com nova tentativa."""
    if isinstance(exc, httpx.HTTPStatusError):
        codigo = exc.response.status_code
        return 400 <= codigo < 500 and codigo not in (408, 416, 425, 429)
    return False


def _validador(resposta: httpx.Response) -> str | None:
    """Validador forte para `If-Range`: ETag (não fraco) ou, na falta, Last-Modified."""
    etag = resposta.headers.get("etag")
    if etag and not etag.startswith("W/"):
        return etag
    return resposta.headers.get("last-modified")


def _baixar_uma_vez(
    http: httpx.Client,
    url: str,
    parcial: Path,
    *,
    auth,
    velocidade_minima_bps: float,
    janela_lentidao_s: float,
    relogio: Callable[[], float],
    prazo: Callable[[], bool] = lambda: False,
) -> None:
    caminho_validador = parcial.with_name(parcial.name + ".validador")
    headers: dict[str, str] = {}
    modo = "wb"
    if parcial.exists() and parcial.stat().st_size > 0:
        headers["Range"] = f"bytes={parcial.stat().st_size}-"
        modo = "ab"
        if caminho_validador.exists():
            headers["If-Range"] = caminho_validador.read_text(encoding="utf-8")

    with http.stream("GET", url, headers=headers, auth=auth) as resposta:
        if resposta.status_code == 416:
            # `.part` maior/igual ao arquivo remoto: começa de novo na próxima tentativa.
            parcial.unlink(missing_ok=True)
            caminho_validador.unlink(missing_ok=True)
        resposta.raise_for_status()
        if headers.get("Range") and resposta.status_code != 206:
            modo = "wb"  # sem suporte a Range ou validador mudou (arquivo republicado): do zero
        if modo == "wb":
            validador = _validador(resposta)
            if validador:
                caminho_validador.write_text(validador, encoding="utf-8")
            else:
                caminho_validador.unlink(missing_ok=True)
        inicio_janela = relogio()
        bytes_na_janela = 0
        with open(parcial, modo) as fh:
            for pedaco in resposta.iter_bytes():
                fh.write(pedaco)
                if prazo():
                    raise _PrazoExcedido
                bytes_na_janela += len(pedaco)
                agora = relogio()
                decorrido = agora - inicio_janela
                if decorrido >= janela_lentidao_s:
                    taxa = bytes_na_janela / decorrido
                    if taxa < velocidade_minima_bps:
                        raise VelocidadeBaixaErro(taxa, velocidade_minima_bps, janela_lentidao_s)
                    inicio_janela = agora
                    bytes_na_janela = 0


def _recuo_s(sem_progresso: int) -> float:
    """1 s após tentativa com progresso; 1, 2, 4... (teto 60 s) para falhas seguidas sem avanço."""
    return float(min(2 ** max(sem_progresso - 1, 0), 60))


def baixar_com_retentativas(
    http: httpx.Client,
    url: str,
    destino: Path,
    *,
    tamanho_esperado: int | None,
    tentativas: int,
    hosts_permitidos: tuple[str, ...],
    auth: tuple[str, str] | None = None,
    dormir: Callable[[float], None] = time.sleep,
    velocidade_minima_bps: float = 50 * 1024,
    janela_lentidao_s: float = 60.0,
    relogio: Callable[[], float] = time.monotonic,
    max_retomadas: int = 50,
    tempo_limite_total_s: float = 3600.0,
    relogio_total: Callable[[], float] = time.monotonic,
) -> Path:
    """Baixa `url` para `destino`, retomada via Range, retentativa com recuo e checagem do tamanho.

    Grava em `destino` + `.part` e só renomeia (atomicamente) para `destino` após confirmar o
    tamanho final. Levanta `TamanhoDivergenteErro` (apagando o `.part`) se o tamanho não bater.

    Resiliência ao WebDAV lento/travado (P4, P6): a tentativa é abortada se a taxa cair abaixo de
    `velocidade_minima_bps` por `janela_lentidao_s` segundos e retomada via Range (com `If-Range`
    quando o servidor deu ETag/Last-Modified; resposta 200 a um Range reinicia do zero). O
    contador de tentativas sem progresso zera quando uma tentativa grava bytes novos, mas três
    tetos independentes encerram a baixa com `BaixaArquivoErro` (que cita a URL): `tentativas`
    falhas seguidas sem avanço, `max_retomadas` falhas no total e `tempo_limite_total_s` de relógio.
    Há espera (recuo) entre tentativas, com ou sem progresso.
    """
    _verificar_host_permitido(url, hosts_permitidos)

    nome_arquivo = destino.name
    parcial = destino.parent / (destino.name + ".part")
    caminho_validador = parcial.with_name(parcial.name + ".validador")
    destino.parent.mkdir(parents=True, exist_ok=True)
    inicio_total = relogio_total()

    def _tamanho_parcial() -> int:
        return parcial.stat().st_size if parcial.exists() else 0

    def _prazo_excedido() -> bool:
        return relogio_total() - inicio_total >= tempo_limite_total_s

    def _falhar(motivo: str) -> BaixaArquivoErro:
        parcial.unlink(missing_ok=True)
        caminho_validador.unlink(missing_ok=True)
        return BaixaArquivoErro(nome_arquivo, f"{motivo} ({url})")

    ultimo_erro: Exception | None = None
    sem_progresso = 0
    retomadas = 0
    while True:
        bytes_antes = _tamanho_parcial()
        if tamanho_esperado is not None and bytes_antes == tamanho_esperado:
            break  # `.part` de uma execução anterior já está completo
        try:
            _baixar_uma_vez(
                http,
                url,
                parcial,
                auth=auth,
                velocidade_minima_bps=velocidade_minima_bps,
                janela_lentidao_s=janela_lentidao_s,
                relogio=relogio,
                prazo=_prazo_excedido,
            )
            break
        except _PrazoExcedido:
            raise _falhar(f"tempo total de {tempo_limite_total_s:.0f}s esgotado") from None
        except (httpx.HTTPError, VelocidadeBaixaErro) as exc:
            ultimo_erro = exc
            if _erro_permanente(exc):
                raise _falhar(f"erro HTTP permanente: {exc}") from exc
            sem_progresso = 0 if _tamanho_parcial() > bytes_antes else sem_progresso + 1
            retomadas += 1
            if sem_progresso >= tentativas:
                raise _falhar(
                    f"falha após {tentativas} tentativas sem progresso: {ultimo_erro}"
                ) from exc
            if retomadas >= max_retomadas:
                raise _falhar(
                    f"limite de {max_retomadas} retomadas atingido: {ultimo_erro}"
                ) from exc
            if _prazo_excedido():
                raise _falhar(
                    f"tempo total de {tempo_limite_total_s:.0f}s esgotado: {ultimo_erro}"
                ) from exc
            dormir(_recuo_s(sem_progresso))

    tamanho_final = _tamanho_parcial()
    caminho_validador.unlink(missing_ok=True)
    if tamanho_esperado is not None and tamanho_final != tamanho_esperado:
        parcial.unlink(missing_ok=True)
        raise TamanhoDivergenteErro(nome_arquivo, tamanho_esperado, tamanho_final)

    parcial.replace(destino)
    return destino


class ClienteRFB:
    """Cliente do compartilhamento WebDAV público de dados abertos do CNPJ."""

    def __init__(
        self,
        configuracao: Configuracao,
        http: httpx.Client | None = None,
        dormir: Callable[[float], None] = time.sleep,
    ) -> None:
        self._configuracao = configuracao
        self._auth = (configuracao.webdav_token, "")
        self._http = http or httpx.Client(auth=self._auth, timeout=configuracao.tempo_limite_s)
        self._dormir = dormir

    def _propfind(self, subpath: str) -> ET.Element | None:
        """PROPFIND com retentativa/recuo como a baixa; falhas viram `WebDAVIndisponivelErro`."""
        url = self._configuracao.webdav_url + subpath
        tentativas = max(self._configuracao.tentativas, 1)
        for numero in range(1, tentativas + 1):
            try:
                resposta = self._http.request(
                    "PROPFIND", url, headers={"Depth": "1"}, auth=self._auth
                )
                if resposta.status_code == 404:
                    return None
                resposta.raise_for_status()
                return ET.fromstring(resposta.text)
            except ET.ParseError as exc:
                raise WebDAVIndisponivelErro(url, f"resposta XML inválida: {exc}") from exc
            except httpx.HTTPError as exc:
                if _erro_permanente(exc) or numero == tentativas:
                    motivo = f"{exc} (após {numero} tentativa(s))"
                    raise WebDAVIndisponivelErro(url, motivo) from exc
                self._dormir(_recuo_s(numero))
        raise AssertionError("inalcançável")  # pragma: no cover

    def listar_meses(self) -> list[str]:
        root = self._propfind("")
        meses = []
        if root is not None:
            for resposta in root.findall("d:response", _DAV_NS):
                href = resposta.findtext("d:href", default="", namespaces=_DAV_NS)
                if not href.endswith("/"):
                    continue
                nome = href.rstrip("/").rsplit("/", maxsplit=1)[-1]
                if _MES_RE.match(nome):
                    meses.append(nome)
        return sorted(meses)

    def mes_mais_recente(self) -> str:
        meses = self.listar_meses()
        if not meses:
            raise MesInexistenteErro("(mais recente)", meses)
        return meses[-1]

    def listar_arquivos(self, mes: str) -> list[ArquivoRemoto]:
        disponiveis = self.listar_meses()
        if mes not in disponiveis:
            raise MesInexistenteErro(mes, disponiveis)

        root = self._propfind(f"{mes}/")
        if root is None:
            raise MesInexistenteErro(mes, disponiveis)

        arquivos = []
        for resposta in root.findall("d:response", _DAV_NS):
            href = resposta.findtext("d:href", default="", namespaces=_DAV_NS)
            if href.endswith("/"):
                continue  # a própria pasta
            nome = href.rsplit("/", maxsplit=1)[-1]
            if nome.startswith("Socios"):
                continue
            tamanho_texto = resposta.findtext(".//d:getcontentlength", namespaces=_DAV_NS)
            tamanho = int(tamanho_texto) if tamanho_texto and tamanho_texto.strip() else None
            if tamanho is None:
                print(
                    f"aviso: {mes}/{nome} sem getcontentlength; tamanho não será verificado",
                    file=sys.stderr,
                )
            arquivos.append(ArquivoRemoto(nome=nome, tamanho=tamanho))
        return arquivos

    def baixar(self, mes: str, arquivo: ArquivoRemoto, destino_dir: Path) -> Path:
        url = f"{self._configuracao.webdav_url}{mes}/{arquivo.nome}"
        destino = destino_dir / arquivo.nome
        return baixar_com_retentativas(
            self._http,
            url,
            destino,
            tamanho_esperado=arquivo.tamanho,
            tentativas=self._configuracao.tentativas,
            hosts_permitidos=self._configuracao.hosts_permitidos,
            auth=self._auth,
            dormir=self._dormir,
            velocidade_minima_bps=self._configuracao.velocidade_minima_bps,
            janela_lentidao_s=self._configuracao.janela_lentidao_s,
            max_retomadas=self._configuracao.max_retomadas,
            tempo_limite_total_s=self._configuracao.tempo_limite_total_s,
        )
