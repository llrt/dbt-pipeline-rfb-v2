"""Manifesto de execução da ingestão e decisão de idempotência.

Formato do manifesto: ARCHITECTURE.md §4.3. `linhas_lidas` por arquivo inclui as linhas
rejeitadas (`linhas_lidas = linhas_gravadas + linhas_rejeitadas`); o resumo por entidade em
`entidades` soma as linhas efetivamente gravadas e as rejeitadas.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from rfb_pipeline.config import Config

__all__ = [
    "VERSAO_PIPELINE",
    "ArquivoManifesto",
    "Manifesto",
    "caminho_manifesto",
    "escrever_manifesto",
    "ler_manifesto",
    "precisa_reconverter",
    "sha256_arquivo",
]

VERSAO_PIPELINE = "0.1.0"
_BLOCO_HASH = 1024 * 1024


def sha256_arquivo(caminho: Path) -> str:
    """Calcula o sha256 de `caminho` em streaming, sem carregar o arquivo inteiro em memória."""
    digest = hashlib.sha256()
    with caminho.open("rb") as fh:
        for bloco in iter(lambda: fh.read(_BLOCO_HASH), b""):
            digest.update(bloco)
    return digest.hexdigest()


@dataclass(frozen=True)
class ArquivoManifesto:
    nome: str
    bytes: int
    sha256: str
    entidade: str
    linhas_lidas: int
    linhas_rejeitadas: int
    parquet: tuple[str, ...]

    @property
    def linhas_gravadas(self) -> int:
        return self.linhas_lidas - self.linhas_rejeitadas

    def to_dict(self) -> dict:
        return {
            "nome": self.nome,
            "bytes": self.bytes,
            "sha256": self.sha256,
            "entidade": self.entidade,
            "linhas_lidas": self.linhas_lidas,
            "linhas_rejeitadas": self.linhas_rejeitadas,
            "parquet": list(self.parquet),
        }

    @staticmethod
    def from_dict(dados: dict) -> ArquivoManifesto:
        return ArquivoManifesto(
            nome=dados["nome"],
            bytes=int(dados["bytes"]),
            sha256=dados["sha256"],
            entidade=dados["entidade"],
            linhas_lidas=int(dados["linhas_lidas"]),
            linhas_rejeitadas=int(dados["linhas_rejeitadas"]),
            parquet=tuple(dados.get("parquet", [])),
        )


@dataclass(frozen=True)
class Manifesto:
    mes_referencia: str
    data_referencia: str | None
    iniciado_em: str
    concluido_em: str
    arquivos: tuple[ArquivoManifesto, ...]
    versao_pipeline: str = VERSAO_PIPELINE

    @property
    def entidades(self) -> dict[str, dict[str, int]]:
        resumo: dict[str, dict[str, int]] = {}
        for arquivo in self.arquivos:
            linha = resumo.setdefault(arquivo.entidade, {"linhas": 0, "rejeitadas": 0})
            linha["linhas"] += arquivo.linhas_gravadas
            linha["rejeitadas"] += arquivo.linhas_rejeitadas
        return resumo

    def arquivos_da_entidade(self, entidade: str) -> tuple[ArquivoManifesto, ...]:
        return tuple(a for a in self.arquivos if a.entidade == entidade)

    def to_dict(self) -> dict:
        return {
            "mes_referencia": self.mes_referencia,
            "data_referencia": self.data_referencia,
            "iniciado_em": self.iniciado_em,
            "concluido_em": self.concluido_em,
            "arquivos": [a.to_dict() for a in self.arquivos],
            "entidades": self.entidades,
            "versao_pipeline": self.versao_pipeline,
        }

    @staticmethod
    def from_dict(dados: dict) -> Manifesto:
        return Manifesto(
            mes_referencia=dados["mes_referencia"],
            data_referencia=dados.get("data_referencia"),
            iniciado_em=dados["iniciado_em"],
            concluido_em=dados["concluido_em"],
            arquivos=tuple(ArquivoManifesto.from_dict(a) for a in dados["arquivos"]),
            versao_pipeline=dados.get("versao_pipeline", VERSAO_PIPELINE),
        )


def caminho_manifesto(config: Config, mes: str) -> Path:
    return config.manifests_dir / f"{mes}.json"


def ler_manifesto(config: Config, mes: str) -> Manifesto | None:
    """Lê o manifesto de `mes`, ou `None` se ainda não existir."""
    caminho = caminho_manifesto(config, mes)
    if not caminho.exists():
        return None
    return Manifesto.from_dict(json.loads(caminho.read_text(encoding="utf-8")))


def escrever_manifesto(config: Config, manifesto: Manifesto) -> Path:
    """Grava o manifesto em `_manifests/<mes>.json` atomicamente (temp + rename)."""
    destino = caminho_manifesto(config, manifesto.mes_referencia)
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(f".tmp-{destino.name}-{uuid.uuid4().hex}")
    tmp.write_text(
        json.dumps(manifesto.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    tmp.replace(destino)
    return destino


def _particao_rfb_existe(config: Config, entidade: str, mes: str) -> bool:
    return (config.raw_dir / "rfb" / entidade / f"mes_referencia={mes}").is_dir()


def precisa_reconverter(
    config: Config,
    manifesto_anterior: Manifesto | None,
    entidade: str,
    mes: str,
    zips_atuais: list[tuple[str, int, str]],
    *,
    force: bool = False,
) -> bool:
    """Decide se a entidade `entidade` precisa ser (re)convertida para o mês `mes`.

    `zips_atuais` é a lista `(nome, bytes, sha256)` dos zips atuais da entidade. Retorna `False`
    (pula a conversão) somente quando `force` é falso, há manifesto anterior, a partição já existe
    em `raw/` e o conjunto de zips (nome+bytes+sha256) é idêntico ao do manifesto anterior para
    essa entidade — nesse caso o Parquet existente não é tocado (mtime inalterado).
    """
    if force or manifesto_anterior is None:
        return True
    if not _particao_rfb_existe(config, entidade, mes):
        return True
    anteriores = {
        (a.nome, a.bytes, a.sha256) for a in manifesto_anterior.arquivos_da_entidade(entidade)
    }
    return anteriores != set(zips_atuais)
