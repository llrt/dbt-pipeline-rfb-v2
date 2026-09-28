"""Cliente WebDAV da RFB: listagem de meses/arquivos e download resiliente."""

from __future__ import annotations

import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx

from rfb_pipeline.config import Config
from rfb_pipeline.errors import (
    DownloadError,
    ErroIngestao,
    HostNaoPermitidoError,
    MesInexistenteError,
    TamanhoDivergenteError,
)

__all__ = [
    "ArquivoRemoto",
    "ClienteRFB",
    "DownloadError",
    "ErroIngestao",
    "HostNaoPermitidoError",
    "MesInexistenteError",
    "TamanhoDivergenteError",
    "baixar_com_retry",
]

_DAV_NS = {"d": "DAV:"}
_MES_RE = re.compile(r"^\d{4}-\d{2}$")


@dataclass(frozen=True)
class ArquivoRemoto:
    nome: str
    tamanho: int


def _verificar_host_permitido(url: str, hosts_permitidos: tuple[str, ...]) -> None:
    host = urllib.parse.urlsplit(url).hostname or ""
    if host not in hosts_permitidos:
        raise HostNaoPermitidoError(host, hosts_permitidos)


def _baixar_uma_vez(http: httpx.Client, url: str, parcial: Path, *, auth) -> None:
    headers: dict[str, str] = {}
    modo = "wb"
    if parcial.exists() and parcial.stat().st_size > 0:
        headers["Range"] = f"bytes={parcial.stat().st_size}-"
        modo = "ab"

    with http.stream("GET", url, headers=headers, auth=auth) as resp:
        if headers.get("Range") and resp.status_code != 206:
            modo = "wb"  # servidor não suporta retomada; reinicia do zero
        resp.raise_for_status()
        with open(parcial, modo) as fh:
            for chunk in resp.iter_bytes():
                fh.write(chunk)


def baixar_com_retry(
    http: httpx.Client,
    url: str,
    destino: Path,
    *,
    tamanho_esperado: int | None,
    tentativas: int,
    hosts_permitidos: tuple[str, ...],
    auth: tuple[str, str] | None = None,
    dormir: Callable[[float], None] = time.sleep,
) -> Path:
    """Baixa `url` para `destino`, com retomada via Range, retry com backoff e checagem de tamanho.

    Grava em `destino` + `.part` e só renomeia (atomicamente) para `destino` após confirmar o
    tamanho final. Levanta `TamanhoDivergenteError` (apagando o `.part`) se o tamanho não bater, e
    `DownloadError` citando o arquivo se todas as tentativas falharem.
    """
    _verificar_host_permitido(url, hosts_permitidos)

    nome_arquivo = destino.name
    parcial = destino.parent / (destino.name + ".part")
    destino.parent.mkdir(parents=True, exist_ok=True)

    ultimo_erro: Exception | None = None
    sucesso = False
    for tentativa in range(tentativas):
        try:
            _baixar_uma_vez(http, url, parcial, auth=auth)
            sucesso = True
            break
        except httpx.HTTPError as exc:
            ultimo_erro = exc
            if tentativa < tentativas - 1:
                dormir(2**tentativa)

    if not sucesso:
        parcial.unlink(missing_ok=True)
        raise DownloadError(nome_arquivo, f"falha após {tentativas} tentativas: {ultimo_erro}")

    tamanho_final = parcial.stat().st_size
    if tamanho_esperado is not None and tamanho_final != tamanho_esperado:
        parcial.unlink(missing_ok=True)
        raise TamanhoDivergenteError(nome_arquivo, tamanho_esperado, tamanho_final)

    parcial.replace(destino)
    return destino


class ClienteRFB:
    """Cliente do compartilhamento WebDAV público de dados abertos do CNPJ."""

    def __init__(
        self,
        config: Config,
        http: httpx.Client | None = None,
        dormir: Callable[[float], None] = time.sleep,
    ) -> None:
        self._config = config
        self._auth = (config.webdav_token, "")
        self._http = http or httpx.Client(auth=self._auth, timeout=config.timeout_s)
        self._dormir = dormir

    def _propfind(self, subpath: str) -> ET.Element | None:
        url = self._config.webdav_url + subpath
        resp = self._http.request("PROPFIND", url, headers={"Depth": "1"}, auth=self._auth)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return ET.fromstring(resp.text)

    def listar_meses(self) -> list[str]:
        root = self._propfind("")
        meses = []
        if root is not None:
            for response in root.findall("d:response", _DAV_NS):
                href = response.findtext("d:href", default="", namespaces=_DAV_NS)
                if not href.endswith("/"):
                    continue
                nome = href.rstrip("/").rsplit("/", maxsplit=1)[-1]
                if _MES_RE.match(nome):
                    meses.append(nome)
        return sorted(meses)

    def mes_mais_recente(self) -> str:
        meses = self.listar_meses()
        if not meses:
            raise MesInexistenteError("(mais recente)", meses)
        return meses[-1]

    def listar_arquivos(self, mes: str) -> list[ArquivoRemoto]:
        disponiveis = self.listar_meses()
        if mes not in disponiveis:
            raise MesInexistenteError(mes, disponiveis)

        root = self._propfind(f"{mes}/")
        if root is None:
            raise MesInexistenteError(mes, disponiveis)

        arquivos = []
        for response in root.findall("d:response", _DAV_NS):
            href = response.findtext("d:href", default="", namespaces=_DAV_NS)
            if href.endswith("/"):
                continue  # a própria pasta
            nome = href.rsplit("/", maxsplit=1)[-1]
            if nome.startswith("Socios"):
                continue
            tamanho_texto = response.findtext(".//d:getcontentlength", namespaces=_DAV_NS)
            arquivos.append(ArquivoRemoto(nome=nome, tamanho=int(tamanho_texto or 0)))
        return arquivos

    def baixar(self, mes: str, arquivo: ArquivoRemoto, destino_dir: Path) -> Path:
        url = f"{self._config.webdav_url}{mes}/{arquivo.nome}"
        destino = destino_dir / arquivo.nome
        return baixar_com_retry(
            self._http,
            url,
            destino,
            tamanho_esperado=arquivo.tamanho,
            tentativas=self._config.tentativas,
            hosts_permitidos=self._config.hosts_permitidos,
            auth=self._auth,
            dormir=self._dormir,
        )
