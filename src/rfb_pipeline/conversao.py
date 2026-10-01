"""Conversão dos zips da RFB e dos csv.gz da Base dos Dados para a camada raw em Parquet.

Contrato da camada raw: ARCHITECTURE.md §4.2. Pontos principais:

- Leitura CSV via DuckDB `read_csv`, arquivo a arquivo, com `COPY ... TO ... (FORMAT parquet)`:
  os dados nunca passam pelo Python, e memória/threads/spill vêm da `Configuracao`.
- Todas as colunas de dados como VARCHAR; campos `""` (vazio entre aspas) viram NULL (comportamento
  padrão do DuckDB, mantido de propósito: o staging trata vazio e NULL da mesma forma).
- Escrita atômica: tudo é gravado num diretório temporário irmão do destino e só então publicado
  por rename, substituindo a partição anterior. Qualquer falha remove o temporário e preserva a
  partição anterior.
- Rejeitos do analisador (`store_rejects`) vão para `raw/_rejeitos/`; acima do limiar a entidade
  não é publicada.
- Contagem > 0: uma entidade (ou tabela BD) que resulte em 0 linhas no total não é publicada
  (`EntidadeVaziaErro`); um arquivo vazio numa entidade com outros arquivos não vazios só gera
  aviso no log.
"""

from __future__ import annotations

import logging
import re
import shutil
import sys
import uuid
import zipfile
import zlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path, PurePosixPath

import duckdb

from rfb_pipeline.configuracao import Configuracao
from rfb_pipeline.erros import (
    ConversaoErro,
    EntidadeVaziaErro,
    ErroIngestao,
    TaxaRejeitoExcedidaErro,
    ZipCorrompidoErro,
    ZipInseguroErro,
)
from rfb_pipeline.esquemas import EntidadeRFB, TabelaBD

__all__ = [
    "ConversaoErro",
    "EntidadeVaziaErro",
    "ResultadoConversao",
    "TaxaRejeitoExcedidaErro",
    "ZipCorrompidoErro",
    "ZipInseguroErro",
    "converter_entidade_rfb",
    "converter_tabela_bd",
    "data_referencia_do_nome",
    "extrair_zip_seguro",
]

_log = logging.getLogger(__name__)

_RE_MES = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_RE_DATA_NOME = re.compile(r"(?:^|\.)D(\d)(\d{2})(\d{2})(?:\.|$)")
_BLOCO_COPIA = 1024 * 1024


@dataclass(frozen=True)
class ResultadoConversao:
    entidade: str
    arquivo_origem: str
    arquivo_interno: str | None
    linhas: int
    linhas_rejeitadas: int
    parquet: tuple[Path, ...]
    data_referencia: date | None


# --------------------------------------------------------------------------- zip


def _entrada_insegura(nome: str) -> bool:
    normalizado = nome.replace("\\", "/")
    if normalizado.startswith("/") or re.match(r"^[A-Za-z]:", normalizado):
        return True
    return ".." in PurePosixPath(normalizado).parts


def extrair_zip_seguro(caminho_zip: Path, destino_dir: Path) -> list[Path]:
    """Extrai os arquivos de `caminho_zip` em `destino_dir`, recusando zip-slip.

    Todas as entradas são validadas antes de qualquer escrita: caminho absoluto, letra de drive ou
    componente `..` (ou qualquer caminho que resolva fora de `destino_dir`) levanta
    `ZipInseguroErro`. A integridade é verificada pelo CRC de cada entrada durante a extração
    (sem um `testzip` separado, que descomprimiria os ~2 GB de `Estabelecimentos0` duas vezes);
    zip ilegível ou CRC inválido levanta `ZipCorrompidoErro` e remove o que foi extraído.
    """
    destino_dir.mkdir(parents=True, exist_ok=True)
    raiz = destino_dir.resolve()
    extraidos: list[Path] = []
    try:
        with zipfile.ZipFile(caminho_zip) as zf:
            entradas = [info for info in zf.infolist() if not info.is_dir()]
            alvos: list[tuple[zipfile.ZipInfo, Path]] = []
            for info in entradas:
                alvo = (raiz / info.filename.replace("\\", "/")).resolve()
                if _entrada_insegura(info.filename) or not alvo.is_relative_to(raiz):
                    raise ZipInseguroErro(str(caminho_zip), info.filename)
                alvos.append((info, alvo))
            for info, alvo in alvos:
                alvo.parent.mkdir(parents=True, exist_ok=True)
                extraidos.append(alvo)
                with zf.open(info) as origem, alvo.open("wb") as saida:
                    shutil.copyfileobj(origem, saida, _BLOCO_COPIA)
    except (zipfile.BadZipFile, zlib.error, EOFError, NotImplementedError) as exc:
        for caminho in extraidos:
            caminho.unlink(missing_ok=True)
        raise ZipCorrompidoErro(str(caminho_zip), str(exc) or type(exc).__name__) from exc
    return extraidos


# ----------------------------------------------------------------- data de referência


def data_referencia_do_nome(nome_interno: str, mes_referencia: str) -> date | None:
    """Extrai a data do extrato embutida no nome interno do arquivo da RFB.

    O token tem a forma `D` + último dígito do ano + `MMDD` (ex. `D60912`). O ano é o mais recente
    `<=` ano de `mes_referencia` cujo último dígito coincide. Retorna `None` se não houver token
    ou se a data for inválida.
    """
    achado = _RE_DATA_NOME.search(nome_interno)
    if achado is None:
        return None
    digito, mes, dia = (int(g) for g in achado.groups())
    ano_ref = int(mes_referencia[:4])
    ano = ano_ref - ((ano_ref - digito) % 10)
    try:
        return date(ano, mes, dia)
    except ValueError:
        return None


# ----------------------------------------------------------------------- DuckDB


def _literal(valor: str) -> str:
    return "'" + valor.replace("'", "''") + "'"


def _identificador(nome: str) -> str:
    return '"' + nome.replace('"', '""') + '"'


def _ts(momento: datetime) -> str:
    if momento.tzinfo is not None:
        momento = momento.astimezone(UTC).replace(tzinfo=None)
    return momento.isoformat(sep=" ")


def _conectar(configuracao: Configuracao) -> duckdb.DuckDBPyConnection:
    tmp = configuracao.raiz_dados / "_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET memory_limit = {_literal(configuracao.duckdb_memory_limit)}")
    con.execute(f"SET threads = {int(configuracao.duckdb_threads)}")
    con.execute(f"SET temp_directory = {_literal(str(tmp))}")
    con.execute("SET preserve_insertion_order = false")
    return con


def _publicar(tmp_dir: Path, final_dir: Path) -> None:
    """Troca `final_dir` por `tmp_dir` com renames; em falha restaura a versão anterior."""
    antigo: Path | None = None
    if final_dir.exists():
        antigo = final_dir.with_name(f".old-{final_dir.name}-{uuid.uuid4().hex}")
        final_dir.rename(antigo)
    try:
        tmp_dir.rename(final_dir)
    except BaseException:
        if antigo is not None:
            antigo.rename(final_dir)
        raise
    if antigo is not None:
        shutil.rmtree(antigo, ignore_errors=True)


def _dir_temporario(final_dir: Path) -> Path:
    tmp = final_dir.with_name(f".tmp-{final_dir.name}-{uuid.uuid4().hex}")
    tmp.mkdir(parents=True)
    return tmp


# -------------------------------------------------------------------------- RFB

_TABELA_REJEITOS = "_rfb_rejeitos"
_TABELA_REJEITOS_VARREDURA = "_rfb_rejeitos_varredura"
_TABELA_REJEITOS_ENTIDADE = "_rfb_rejeitos_entidade"


def _sql_copia_rfb(
    csv: Path,
    parquet: Path,
    entidade: EntidadeRFB,
    arquivo_origem: str,
    mes: str,
    data_ref: date | None,
    ingerido_em: datetime,
    encoding: str = "latin-1",
) -> str:
    colunas = ", ".join(_identificador(c) for c in entidade.colunas)
    tecnicas = (
        f"{_literal(arquivo_origem)}::VARCHAR AS _arquivo_origem, "
        f"{_literal(mes)}::VARCHAR AS _mes_referencia, "
        f"{_literal(data_ref.isoformat()) if data_ref else 'NULL'}::DATE AS _data_referencia, "
        f"{_literal(_ts(ingerido_em))}::TIMESTAMP AS _ingerido_em"
    )
    if csv.stat().st_size == 0:
        # O sniffer do DuckDB falha em arquivo vazio; produz um Parquet vazio com o schema certo.
        vazias = ", ".join(f"NULL::VARCHAR AS {_identificador(c)}" for c in entidade.colunas)
        origem = f"(SELECT {vazias} LIMIT 0)"
    else:
        struct = ", ".join(f"{_literal(c)}: 'VARCHAR'" for c in entidade.colunas)
        origem = (
            f"read_csv({_literal(str(csv))}, delim=';', quote='\"', escape='\"', header=false, "
            f"encoding={_literal(encoding)}, all_varchar=true, columns={{{struct}}}, "
            f"store_rejects=true, rejects_table='{_TABELA_REJEITOS}', "
            f"rejects_scan='{_TABELA_REJEITOS_VARREDURA}')"
        )
    return (
        f"COPY (SELECT {colunas}, {tecnicas} FROM {origem}) "
        f"TO {_literal(str(parquet))} (FORMAT parquet, COMPRESSION zstd)"
    )


_MSG_NAO_LATIN1 = "not latin-1 encoded"
_BLOCO_TRANSCODIFICACAO = 64 * 1024 * 1024


def _transcodificar_latin1_para_utf8(origem: Path, destino: Path) -> int:
    """Copia `origem` (latin-1) para `destino` em UTF-8; devolve quantos bytes 0x80–0x9F havia."""
    controles = 0
    with origem.open("rb") as entrada, destino.open("wb") as saida:
        while bloco := entrada.read(_BLOCO_TRANSCODIFICACAO):
            controles += sum(bloco.count(bytes([b])) for b in range(0x80, 0xA0))
            saida.write(bloco.decode("latin-1").encode("utf-8"))
    return controles


def _existe_tabela(con: duckdb.DuckDBPyConnection, nome: str) -> bool:
    linha = con.execute(
        "SELECT count(*) FROM duckdb_tables() WHERE table_name = ?", [nome]
    ).fetchone()
    return bool(linha and linha[0])


def _converter_csv_rfb(
    con: duckdb.DuckDBPyConnection,
    csv: Path,
    parquet: Path,
    entidade: EntidadeRFB,
    arquivo_origem: str,
    mes: str,
    data_ref: date | None,
    ingerido_em: datetime,
) -> tuple[int, int]:
    """Converte um CSV RFB; retorna (linhas gravadas, linhas rejeitadas).

    As tabelas de rejeitos do DuckDB acumulam entre scans, então são descartadas antes de cada
    arquivo; os rejeitos deste arquivo são copiados para a tabela da entidade.
    """

    def _copiar(origem: Path, encoding: str) -> tuple | None:
        con.execute(f"DROP TABLE IF EXISTS {_TABELA_REJEITOS}")
        con.execute(f"DROP TABLE IF EXISTS {_TABELA_REJEITOS_VARREDURA}")
        sql = _sql_copia_rfb(
            origem, parquet, entidade, arquivo_origem, mes, data_ref, ingerido_em, encoding
        )
        return con.execute(sql).fetchone()

    try:
        linha = _copiar(csv, "latin-1")
    except duckdb.Error as exc:
        if _MSG_NAO_LATIN1 not in str(exc):
            raise ConversaoErro(f"{arquivo_origem}/{csv.name}", str(exc)) from exc
        # O decodificador latin-1 do DuckDB recusa os bytes 0x80–0x9F (controles C1), que o
        # extrato real traz em raros campos (ex.: 2026-09, Estabelecimentos0: dois bytes 0x8F).
        # ISO-8859-1 mapeia todo byte para U+0000–U+00FF: transcodifica em Python e relê em UTF-8.
        utf8 = csv.with_name(csv.name + ".utf8")
        try:
            controles = _transcodificar_latin1_para_utf8(csv, utf8)
            print(
                f"aviso: {arquivo_origem}/{csv.name}: {controles} byte(s) 0x80–0x9F; "
                "relido após transcodificar latin-1 -> UTF-8",
                file=sys.stderr,
            )
            linha = _copiar(utf8, "utf-8")
        except duckdb.Error as exc2:
            raise ConversaoErro(f"{arquivo_origem}/{csv.name}", str(exc2)) from exc2
        finally:
            utf8.unlink(missing_ok=True)
    linhas = int(linha[0]) if linha else 0

    if not _existe_tabela(con, _TABELA_REJEITOS):
        return linhas, 0
    con.execute(
        f"""
        INSERT INTO {_TABELA_REJEITOS_ENTIDADE}
        SELECT {_literal(arquivo_origem)}, {_literal(csv.name)}, line, column_idx, column_name,
               error_type::VARCHAR, csv_line, error_message
        FROM {_TABELA_REJEITOS}
        """
    )
    rejeitadas = con.execute(
        f"SELECT count(*) FROM (SELECT DISTINCT file_id, line FROM {_TABELA_REJEITOS})"
    ).fetchone()
    return linhas, int(rejeitadas[0]) if rejeitadas else 0


def _gravar_rejeitos(con: duckdb.DuckDBPyConnection, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(f".tmp-{destino.name}-{uuid.uuid4().hex}")
    con.execute(
        f"COPY (SELECT * FROM {_TABELA_REJEITOS_ENTIDADE} ORDER BY arquivo_origem, linha) "
        f"TO {_literal(str(tmp))} (FORMAT parquet, COMPRESSION zstd)"
    )
    tmp.replace(destino)


def _unico_arquivo(caminho_zip: Path, extraidos: list[Path]) -> Path:
    if len(extraidos) != 1:
        raise ErroIngestao(
            f"zip {caminho_zip.name}: esperado exatamente 1 arquivo interno, encontrados "
            f"{len(extraidos)}"
        )
    return extraidos[0]


def converter_entidade_rfb(
    zips: Sequence[Path],
    entidade: EntidadeRFB,
    mes: str,
    configuracao: Configuracao,
    *,
    ingerido_em: datetime,
) -> list[ResultadoConversao]:
    """Converte todos os zips de uma entidade RFB e publica a partição do mês atomicamente.

    Cada zip vira `parte-<nome do zip sem extensão>.parquet` em
    `raw/rfb/<entidade>/mes_referencia=<mes>/`. A conversão ocorre num diretório temporário irmão
    e só é publicada (substituindo a partição anterior) quando todos os zips foram convertidos e a
    taxa de rejeito da entidade, `rejeitadas / (gravadas + rejeitadas)`, não excede
    `configuracao.max_taxa_rejeito`. Rejeitos, quando existem, vão para
    `raw/_rejeitos/<entidade>/mes_referencia=<mes>/rejeitos.parquet`. Campos `""` são gravados
    como NULL.

    Levanta `ZipInseguroErro`, `ZipCorrompidoErro`, `ConversaoErro` ou
    `TaxaRejeitoExcedidaErro`; se a entidade inteira resultar em 0 linhas gravadas, levanta
    `EntidadeVaziaErro` (um arquivo vazio entre outros não vazios só gera aviso).
    Em qualquer falha a partição anterior permanece intacta.
    """
    if not _RE_MES.match(mes):
        raise ValueError(f"mes_referencia inválido: {mes!r} (esperado YYYY-MM)")

    final_dir = configuracao.raw_dir / "rfb" / entidade.nome / f"mes_referencia={mes}"
    caminho_rejeitos = (
        configuracao.rejeitos_dir / entidade.nome / f"mes_referencia={mes}" / "rejeitos.parquet"
    )
    final_dir.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = _dir_temporario(final_dir)
    extracao_dir = configuracao.raiz_dados / "_tmp" / f"extracao-{entidade.nome}-{uuid.uuid4().hex}"

    parciais: list[tuple[str, str, int, int, str, date | None]] = []
    con: duckdb.DuckDBPyConnection | None = None
    try:
        con = _conectar(configuracao)
        con.execute(
            f"""
            CREATE TEMP TABLE {_TABELA_REJEITOS_ENTIDADE} (
                arquivo_origem VARCHAR, arquivo_interno VARCHAR, linha BIGINT,
                coluna BIGINT, nome_coluna VARCHAR, tipo_erro VARCHAR,
                linha_csv VARCHAR, mensagem VARCHAR
            )
            """
        )
        for caminho_zip in sorted(zips, key=lambda p: p.name):
            csv = _unico_arquivo(caminho_zip, extrair_zip_seguro(caminho_zip, extracao_dir))
            nome_interno = csv.relative_to(extracao_dir.resolve()).as_posix()
            data_ref = data_referencia_do_nome(nome_interno, mes)
            nome_parquet = f"parte-{caminho_zip.stem}.parquet"
            try:
                linhas, rejeitadas = _converter_csv_rfb(
                    con,
                    csv,
                    tmp_dir / nome_parquet,
                    entidade,
                    caminho_zip.name,
                    mes,
                    data_ref,
                    ingerido_em,
                )
            finally:
                csv.unlink(missing_ok=True)
            parciais.append(
                (caminho_zip.name, nome_interno, linhas, rejeitadas, nome_parquet, data_ref)
            )

        total_linhas = sum(p[2] for p in parciais)
        total_rejeitadas = sum(p[3] for p in parciais)
        lidas = total_linhas + total_rejeitadas
        taxa = total_rejeitadas / lidas if lidas else 0.0

        if total_rejeitadas:
            _gravar_rejeitos(con, caminho_rejeitos)
        if taxa > configuracao.max_taxa_rejeito:
            raise TaxaRejeitoExcedidaErro(
                entidade.nome, taxa, configuracao.max_taxa_rejeito, str(caminho_rejeitos)
            )
        if not total_linhas:
            raise EntidadeVaziaErro(entidade.nome, [p[0] for p in parciais])
        for origem, interno, linhas, *_ in parciais:
            if not linhas:
                _log.warning(
                    "%s: arquivo %s (%s) resultou em 0 linhas; demais arquivos da entidade "
                    "não estão vazios",
                    entidade.nome,
                    origem,
                    interno,
                )
        if not total_rejeitadas:
            caminho_rejeitos.unlink(missing_ok=True)

        _publicar(tmp_dir, final_dir)
    finally:
        if con is not None:
            con.close()
        shutil.rmtree(tmp_dir, ignore_errors=True)
        shutil.rmtree(extracao_dir, ignore_errors=True)

    return [
        ResultadoConversao(
            entidade=entidade.nome,
            arquivo_origem=origem,
            arquivo_interno=interno,
            linhas=linhas,
            linhas_rejeitadas=rejeitadas,
            parquet=(final_dir / nome_parquet,),
            data_referencia=data_ref,
        )
        for origem, interno, linhas, rejeitadas, nome_parquet, data_ref in parciais
    ]


# --------------------------------------------------------------------------- BD


def converter_tabela_bd(
    csv_gz: Path, tabela: TabelaBD, configuracao: Configuracao, *, ingerido_em: datetime
) -> ResultadoConversao:
    """Converte um csv.gz da Base dos Dados em `raw/bd/<tabela>/<tabela>.parquet`.

    CSV UTF-8 com cabecalho, vírgula, aspas `"` (campos multilinha aceitos), todas as colunas
    VARCHAR, mais `_arquivo_origem` e `_ingerido_em`. Leitura estrita: qualquer erro de parsing
    levanta `ConversaoErro`; 0 linhas levanta `EntidadeVaziaErro`. Mesma publicação atômica da
    RFB.
    """
    final_dir = configuracao.raw_dir / "bd" / tabela.nome
    final_dir.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = _dir_temporario(final_dir)
    nome_parquet = f"{tabela.nome}.parquet"
    sql = (
        f"COPY (SELECT *, {_literal(csv_gz.name)}::VARCHAR AS _arquivo_origem, "
        f"{_literal(_ts(ingerido_em))}::TIMESTAMP AS _ingerido_em "
        f"FROM read_csv({_literal(str(csv_gz))}, header=true, delim=',', quote='\"', "
        f"escape='\"', encoding='utf-8', compression='gzip', all_varchar=true)) "
        f"TO {_literal(str(tmp_dir / nome_parquet))} (FORMAT parquet, COMPRESSION zstd)"
    )
    con: duckdb.DuckDBPyConnection | None = None
    try:
        con = _conectar(configuracao)
        try:
            linha = con.execute(sql).fetchone()
        except duckdb.Error as exc:
            raise ConversaoErro(csv_gz.name, str(exc)) from exc
        if not (linha and linha[0]):
            raise EntidadeVaziaErro(tabela.nome, [csv_gz.name])
        _publicar(tmp_dir, final_dir)
    finally:
        if con is not None:
            con.close()
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return ResultadoConversao(
        entidade=tabela.nome,
        arquivo_origem=csv_gz.name,
        arquivo_interno=None,
        linhas=int(linha[0]) if linha else 0,
        linhas_rejeitadas=0,
        parquet=(final_dir / nome_parquet,),
        data_referencia=None,
    )
