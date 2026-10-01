"""Publicação opcional do gold no MotherDuck (ADR-0016, PUB-01).

Desacoplada do dbt: o gold em Parquet continua sendo o contrato; aqui cada dataset de `gold/` vira
uma tabela do banco de destino (`CREATE OR REPLACE TABLE … AS SELECT * FROM read_parquet(…)`). O
destino é uma URI DuckDB (`md:<banco>` em produção; um arquivo `.duckdb` local nos testes). O
token do MotherDuck é lido do ambiente pelo próprio DuckDB e nunca entra em SQL, log ou arquivo.
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import duckdb

from rfb_pipeline.configuracao import Configuracao
from rfb_pipeline.erros import ErroIngestao

__all__ = [
    "Dataset",
    "DestinoMotherDuck",
    "TabelaPublicada",
    "descobrir_datasets",
    "gerar_sql_tabela",
    "ler_destino_motherduck",
    "publicar",
    "publicar_motherduck",
]

_RE_IDENTIFICADOR = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PREFIXO_MD = "md:"


@dataclass(frozen=True)
class Dataset:
    """Um dataset do gold: um `.parquet` ou um diretório particionado (`chave=valor/`)."""

    nome: str
    padrao: str  # glob passado a `read_parquet`
    particionado: bool


@dataclass(frozen=True)
class TabelaPublicada:
    nome: str
    linhas: int


@dataclass(frozen=True)
class DestinoMotherDuck:
    banco: str
    token: str

    @property
    def uri(self) -> str:
        return f"{_PREFIXO_MD}{self.banco}"


def ler_destino_motherduck(env: Mapping[str, str] | None = None) -> DestinoMotherDuck | None:
    """Destino lido de `MOTHERDUCK_TOKEN` + `MOTHERDUCK_BANCO`; `None` se faltar qualquer um."""
    if env is None:
        env = os.environ
    token = (env.get("MOTHERDUCK_TOKEN") or "").strip()
    banco = (env.get("MOTHERDUCK_BANCO") or "").strip()
    if not token or not banco:
        return None
    _validar_identificador(banco, "MOTHERDUCK_BANCO")
    return DestinoMotherDuck(banco=banco, token=token)


def _validar_identificador(valor: str, origem: str) -> None:
    if not _RE_IDENTIFICADOR.match(valor):
        raise ErroIngestao(f"{origem} inválido: {valor!r} (use letras, dígitos e '_')")


def _literal(texto: str) -> str:
    return "'" + texto.replace("'", "''") + "'"


def descobrir_datasets(gold: Path) -> list[Dataset]:
    """Datasets de `gold/`: `*.parquet` soltos e diretórios particionados (`chave=valor/`)."""
    if not gold.is_dir():
        raise ErroIngestao(f"gold não encontrado em {gold}; rode o dbt build antes de publicar")
    datasets: list[Dataset] = []
    for item in sorted(gold.iterdir()):
        if item.name.startswith("."):
            continue
        if item.is_file() and item.suffix == ".parquet":
            datasets.append(Dataset(item.stem, str(item), particionado=False))
        elif item.is_dir() and any(item.glob("*=*/*.parquet")):
            datasets.append(Dataset(item.name, str(item / "*" / "*.parquet"), particionado=True))
    return datasets


def gerar_sql_tabela(banco: str, dataset: Dataset) -> str:
    """SQL que recria a tabela do dataset em `<banco>.main`. Nunca contém credenciais."""
    _validar_identificador(banco, "banco")
    _validar_identificador(dataset.nome, "nome da tabela")
    leitura = f"read_parquet({_literal(dataset.padrao)}"
    leitura += ", hive_partitioning = true)" if dataset.particionado else ")"
    return f'CREATE OR REPLACE TABLE "{banco}".main."{dataset.nome}" AS SELECT * FROM {leitura}'


def _selecionar(datasets: list[Dataset], tabelas: Sequence[str] | None) -> list[Dataset]:
    if not tabelas:
        return datasets
    por_nome = {d.nome: d for d in datasets}
    desconhecidas = [t for t in tabelas if t not in por_nome]
    if desconhecidas:
        raise ErroIngestao(
            f"tabela(s) inexistente(s) no gold: {', '.join(desconhecidas)}; "
            f"disponíveis: {', '.join(sorted(por_nome))}"
        )
    return [por_nome[t] for t in dict.fromkeys(tabelas)]


def publicar(
    gold: Path,
    destino: str,
    banco: str,
    *,
    tabelas: Sequence[str] | None = None,
    segredos: Sequence[str] = (),
    ao_publicar: Callable[[TabelaPublicada], None] | None = None,
) -> list[TabelaPublicada]:
    """Publica os datasets do gold em `destino` (URI DuckDB), sob o catálogo `banco`.

    `destino` é `md:<banco>` (MotherDuck, token no ambiente) ou o caminho de um arquivo `.duckdb`
    (testes). Erros do DuckDB são re-levantados como `ErroIngestao` com `segredos` mascarados.
    """
    _validar_identificador(banco, "banco")
    selecionados = _selecionar(descobrir_datasets(gold), tabelas)
    if not selecionados:
        raise ErroIngestao(f"nenhum dataset Parquet encontrado em {gold}")

    ancora = "" if destino.startswith(_PREFIXO_MD) else f' AS "{banco}"'
    publicadas: list[TabelaPublicada] = []
    try:
        with duckdb.connect(":memory:") as con:
            con.execute(f"ATTACH {_literal(destino)}{ancora}")
            for dataset in selecionados:
                con.execute(gerar_sql_tabela(banco, dataset))
                linhas = con.execute(
                    f'SELECT count(*) FROM "{banco}".main."{dataset.nome}"'
                ).fetchone()[0]
                publicada = TabelaPublicada(dataset.nome, linhas)
                publicadas.append(publicada)
                if ao_publicar is not None:
                    ao_publicar(publicada)
    except duckdb.Error as exc:
        mensagem = str(exc)
        for segredo in segredos:
            mensagem = mensagem.replace(segredo, "***")
        raise ErroIngestao(f"falha ao publicar em {destino}: {mensagem}") from None
    return publicadas


def publicar_motherduck(
    configuracao: Configuracao,
    *,
    tabelas: Sequence[str] | None = None,
    env: Mapping[str, str] | None = None,
    imprimir: Callable[[str], None] = print,
) -> list[TabelaPublicada] | None:
    """Publica o gold no MotherDuck se `MOTHERDUCK_TOKEN` e `MOTHERDUCK_BANCO` estiverem definidos.

    Sem configuração, avisa e devolve `None` sem abrir nenhuma conexão. Com `RAIZ_DADOS=s3://`
    recusa: o gold está no bucket e a publicação lê Parquet local (ver ADR-0016); aponte
    `RAIZ_DADOS` para uma cópia local do gold.
    """
    destino = ler_destino_motherduck(env)
    if destino is None:
        imprimir("MotherDuck não configurado; nada publicado")
        return None
    if configuracao.raiz_dados_s3 is not None:
        raise ErroIngestao(
            "RAIZ_DADOS é s3://: a publicação lê o gold local e não lê de S3; aponte RAIZ_DADOS "
            "para uma cópia local do gold (ex.: baixada do bucket) e rode `rfb publicar` de novo"
        )
    if not os.environ.get("motherduck_token"):
        # o DuckDB/MotherDuck lê o token deste ambiente; nunca vai a SQL, log ou arquivo
        os.environ["motherduck_token"] = destino.token

    def _linha(t: TabelaPublicada) -> None:
        imprimir(f"{t.nome}: {t.linhas} linhas")

    publicadas = publicar(
        configuracao.gold_dir,
        destino.uri,
        destino.banco,
        tabelas=tabelas,
        segredos=(destino.token,),
        ao_publicar=_linha,
    )
    total = sum(t.linhas for t in publicadas)
    imprimir(f"{len(publicadas)} tabela(s), {total} linhas publicadas em {destino.uri}")
    return publicadas
