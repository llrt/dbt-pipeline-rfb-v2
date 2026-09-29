"""CLI de linha de comando do pipeline RFB/CNPJ.

`rfb ingest` liga cliente WebDAV/BD, conversão e manifesto (T10). `rfb sync` publica raw/gold no
S3/Tigris (T11). `pipeline` e `report` ainda são stubs (T28, T27).
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import time
from datetime import UTC, date, datetime
from pathlib import Path

import httpx

from rfb_pipeline.basedosdados import baixar_tabelas_bd
from rfb_pipeline.config import Config, carregar_config
from rfb_pipeline.convert import converter_entidade_rfb, converter_tabela_bd
from rfb_pipeline.errors import ErroIngestao, MesInexistenteError
from rfb_pipeline.manifest import (
    ArquivoManifesto,
    Manifesto,
    escrever_manifesto,
    ler_manifesto,
    precisa_reconverter,
    sha256_arquivo,
)
from rfb_pipeline.rfb_client import ArquivoRemoto, ClienteRFB
from rfb_pipeline.schemas import ENTIDADES_RFB, TABELAS_BD, EntidadeRFB, entidade_do_zip
from rfb_pipeline.storage import sincronizar

EXIT_NO_IMPL = 2
_RE_MES = re.compile(r"^\d{4}-\d{2}$")


def _no_implementado(nome: str) -> None:
    print(f"{nome}: não implementado")
    sys.exit(EXIT_NO_IMPL)


# --------------------------------------------------------------------------- ingest


def _limpar_residuos(config: Config) -> None:
    """Remove resíduos de execuções interrompidas antes de iniciar a ingestão."""
    rfb_dir = config.raw_dir / "rfb"
    if rfb_dir.is_dir():
        for entidade_dir in rfb_dir.iterdir():
            if not entidade_dir.is_dir():
                continue
            for padrao in (".tmp-*", ".old-*"):
                for residuo in entidade_dir.glob(padrao):
                    shutil.rmtree(residuo, ignore_errors=True)
    tmp_dir = config.data_root / "_tmp"
    if tmp_dir.is_dir():
        for residuo in tmp_dir.glob("extract-*"):
            shutil.rmtree(residuo, ignore_errors=True)


def _meses_disponiveis_local(origem_local: Path) -> list[str]:
    pasta = origem_local / "rfb"
    if not pasta.is_dir():
        return []
    return sorted(p.name for p in pasta.iterdir() if p.is_dir() and _RE_MES.match(p.name))


def _resolver_mes(mes: str | None, cliente: ClienteRFB | None, origem_local: Path | None) -> str:
    disponiveis = (
        _meses_disponiveis_local(origem_local)
        if origem_local is not None
        else cliente.listar_meses()
    )
    if mes is not None:
        if mes not in disponiveis:
            raise MesInexistenteError(mes, disponiveis)
        return mes
    if not disponiveis:
        raise MesInexistenteError("(mais recente)", disponiveis)
    return disponiveis[-1]


def _zips_locais_entidade(origem_local: Path, mes: str, entidade: EntidadeRFB) -> list[Path]:
    pasta = origem_local / "rfb" / mes
    return sorted(p for p in pasta.glob("*.zip") if entidade.padrao_zip.match(p.name))


def _baixar_entidades_remoto(
    cliente: ClienteRFB, mes: str, destino_dir: Path
) -> dict[str, list[Path]]:
    """Baixa os zips do mês (só entidades de `ENTIDADES_RFB`, nunca `Socios*`).

    Reaproveita um zip já baixado se o tamanho em disco confere com o anunciado pelo WebDAV.
    """
    por_entidade: dict[str, list[Path]] = {}
    for arquivo in cliente.listar_arquivos(mes):
        entidade = entidade_do_zip(arquivo.nome)
        if entidade is None:
            continue
        destino = destino_dir / arquivo.nome
        if (
            arquivo.tamanho is not None
            and destino.exists()
            and destino.stat().st_size == arquivo.tamanho
        ):
            caminho = destino
        else:
            caminho = cliente.baixar(mes, ArquivoRemoto(arquivo.nome, arquivo.tamanho), destino_dir)
        por_entidade.setdefault(entidade.nome, []).append(caminho)
    return por_entidade


def ingest(
    config: Config,
    *,
    mes: str | None = None,
    origem_local: Path | None = None,
    force: bool = False,
    ingerido_em: datetime | None = None,
) -> Manifesto:
    """Executa a ingestão completa (RFB + Base dos Dados) e grava o manifesto do mês.

    Levanta `ErroIngestao` (ou subclasses) em qualquer falha; nesse caso a partição anterior de
    cada entidade permanece intacta e nada é gravado para as entidades ainda não convertidas.
    """
    _limpar_residuos(config)
    ingerido_em = ingerido_em or datetime.now(UTC)

    cliente = ClienteRFB(config) if origem_local is None else None
    mes_resolvido = _resolver_mes(mes, cliente, origem_local)

    manifesto_anterior = ler_manifesto(config, mes_resolvido)
    data_referencia: date | None = None
    if manifesto_anterior is not None and manifesto_anterior.data_referencia:
        data_referencia = date.fromisoformat(manifesto_anterior.data_referencia)

    remotos_por_entidade: dict[str, list[Path]] | None = None
    if origem_local is None:
        remotos_por_entidade = _baixar_entidades_remoto(
            cliente, mes_resolvido, config.downloads_dir(mes_resolvido)
        )

    entradas: list[ArquivoManifesto] = []
    for entidade in ENTIDADES_RFB.values():
        inicio = time.monotonic()
        if origem_local is not None:
            zips = _zips_locais_entidade(origem_local, mes_resolvido, entidade)
        else:
            zips = remotos_por_entidade.get(entidade.nome, [])
        if not zips:
            raise ErroIngestao(
                f"nenhum zip encontrado para a entidade {entidade.nome!r} no mês {mes_resolvido!r}"
            )

        zips_atuais = [(p.name, p.stat().st_size, sha256_arquivo(p)) for p in zips]

        if not precisa_reconverter(
            config, manifesto_anterior, entidade.nome, mes_resolvido, zips_atuais, force=force
        ):
            reaproveitadas = manifesto_anterior.arquivos_da_entidade(entidade.nome)
            entradas.extend(reaproveitadas)
            linhas = sum(a.linhas_gravadas for a in reaproveitadas)
            rejeitadas = sum(a.linhas_rejeitadas for a in reaproveitadas)
            print(
                f"{entidade.nome}: pulada (sem mudanças) - {linhas} linhas, "
                f"{rejeitadas} rejeitadas, {time.monotonic() - inicio:.1f}s"
            )
            continue

        resultados = converter_entidade_rfb(
            zips, entidade, mes_resolvido, config, ingerido_em=ingerido_em
        )
        bytes_por_nome = {nome: b for nome, b, _ in zips_atuais}
        sha_por_nome = {nome: s for nome, _, s in zips_atuais}
        for resultado in resultados:
            if resultado.data_referencia is not None:
                data_referencia = resultado.data_referencia
            entradas.append(
                ArquivoManifesto(
                    nome=resultado.arquivo_origem,
                    bytes=bytes_por_nome[resultado.arquivo_origem],
                    sha256=sha_por_nome[resultado.arquivo_origem],
                    entidade=resultado.entidade,
                    linhas_lidas=resultado.linhas + resultado.linhas_rejeitadas,
                    linhas_rejeitadas=resultado.linhas_rejeitadas,
                    parquet=tuple(str(p.relative_to(config.data_root)) for p in resultado.parquet),
                )
            )
        linhas = sum(r.linhas for r in resultados)
        rejeitadas = sum(r.linhas_rejeitadas for r in resultados)
        print(
            f"{entidade.nome}: {linhas} linhas, {rejeitadas} rejeitadas, "
            f"{time.monotonic() - inicio:.1f}s"
        )

    destino_bd = config.downloads_dir(mes_resolvido) / "bd"
    caminhos_bd = baixar_tabelas_bd(config, destino_bd, origem_local=origem_local)
    for nome_tabela, tabela in TABELAS_BD.items():
        inicio = time.monotonic()
        resultado = converter_tabela_bd(
            caminhos_bd[nome_tabela], tabela, config, ingerido_em=ingerido_em
        )
        print(f"bd.{nome_tabela}: {resultado.linhas} linhas, {time.monotonic() - inicio:.1f}s")

    manifesto = Manifesto(
        mes_referencia=mes_resolvido,
        data_referencia=data_referencia.isoformat() if data_referencia else None,
        iniciado_em=ingerido_em.isoformat(),
        concluido_em=datetime.now(UTC).isoformat(),
        arquivos=tuple(entradas),
    )
    escrever_manifesto(config, manifesto)
    return manifesto


def _cmd_ingest(args: argparse.Namespace) -> int:
    config = carregar_config()
    ingest(config, mes=args.mes, origem_local=args.origem_local, force=args.force)
    return 0


def _cmd_sync(_args: argparse.Namespace) -> int:
    config = carregar_config()
    enviados = sincronizar(config)
    for chave in enviados:
        print(f"enviado: {chave}")
    print(f"{len(enviados)} objeto(s) enviado(s)")
    return 0


def _cmd_pipeline(_args: argparse.Namespace) -> None:
    _no_implementado("pipeline")


def _cmd_report(_args: argparse.Namespace) -> None:
    _no_implementado("report")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rfb",
        description="Pipeline ELT RFB/CNPJ (dbt + DuckDB).",
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    p_ingest = sub.add_parser("ingest", help="Ingesta os dados RFB/BD para a camada raw.")
    p_ingest.add_argument("--mes", default=None, help="Mês YYYY-MM (padrão: o mais recente).")
    p_ingest.add_argument(
        "--origem-local",
        dest="origem_local",
        type=Path,
        default=None,
        help="Usa fixtures locais em vez de baixar da rede (layout <dir>/rfb, <dir>/bd).",
    )
    p_ingest.add_argument(
        "--force", action="store_true", help="Reconverte mesmo se o manifesto não mudou."
    )
    p_ingest.set_defaults(func=_cmd_ingest)

    p_sync = sub.add_parser("sync", help="Sincroniza raw/ e gold/ a S3 (não implementado).")
    p_sync.set_defaults(func=_cmd_sync)

    p_pipeline = sub.add_parser("pipeline", help="Pipeline ponta a ponta (não implementado).")
    p_pipeline.set_defaults(func=_cmd_pipeline)

    p_report = sub.add_parser(
        "report", help="Gera o relatório do estudo de caso (não implementado)."
    )
    p_report.set_defaults(func=_cmd_report)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        codigo = args.func(args)
    except ErroIngestao as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except httpx.HTTPError as exc:  # rede escapando dos clientes: sem traceback, com a URL
        try:
            url = str(exc.request.url)
        except RuntimeError:
            url = "(URL desconhecida)"
        print(f"erro de rede em {url}: {exc}", file=sys.stderr)
        return 1
    return codigo if codigo is not None else 0


if __name__ == "__main__":
    sys.exit(main())
