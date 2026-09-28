"""CLI de linha de comando do pipeline RFB/CNPJ.

Stub de fundação: define argparse e os subcomandos do contrato. Cada
subcomando ainda não está implementado e sai com código 2.
"""

from __future__ import annotations

import argparse
import sys

EXIT_NO_IMPL = 2


def _no_implementado(nome: str) -> None:
    print(f"{nome}: não implementado")
    sys.exit(EXIT_NO_IMPL)


def _cmd_ingest(_args: argparse.Namespace) -> None:
    _no_implementado("ingest")


def _cmd_sync(_args: argparse.Namespace) -> None:
    _no_implementado("sync")


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

    p_ingest = sub.add_parser("ingest", help="Ingesta os dados RFB/BD (não implementado).")
    p_ingest.set_defaults(func=_cmd_ingest)

    p_sync = sub.add_parser("sync", help="Sincroniza raw/ e gold/ a S3 (não implementado).")
    p_sync.set_defaults(func=_cmd_sync)

    p_pipeline = sub.add_parser("pipeline", help="Pipeline ponta a ponta (não implementado).")
    p_pipeline.set_defaults(func=_cmd_pipeline)

    p_report = sub.add_parser("report", help="Gera o relatório do estudo de caso (não implementado).")
    p_report.set_defaults(func=_cmd_report)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    main()