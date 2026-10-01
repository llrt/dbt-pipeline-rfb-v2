"""Guarda da convenção de idioma (ADR-0014): falha se surgir nome fora da lista fechada.

Cobre as partes verificáveis: subpastas de `transform/models`, prefixos dos modelos dbt, módulos de
`src/rfb_pipeline`, subcomandos da CLI e alvos do Makefile. Para ampliar uma exceção, altere o
ADR-0014 e as listas abaixo no mesmo commit.
"""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

import pytest

from rfb_pipeline import cli

RAIZ = Path(__file__).resolve().parents[2]

SUBPASTAS_MODELS = {
    "staging",
    "staging/rfb",
    "staging/basedosdados",
    "intermediate",
    "marts",
    "marts/original",
    "marts/core",
    "marts/analytics",
    "observability",
    "audit",
}
PREFIXOS_MODELOS = ("stg_", "int_", "dim_", "fct_", "bridge_", "mart_", "dq_", "audit__")
MODELOS_ORIGINAIS_MVP = {"bh_empresas", "agg_empresas"}
MODULOS_ESPERADOS = {
    "__init__",
    "armazenamento",
    "basedosdados",
    "cli",
    "cliente_rfb",
    "configuracao",
    "conversao",
    "erros",
    "esquemas",
    "manifesto",
}
SUBCOMANDOS_ESPERADOS = {"ingerir", "sincronizar", "pipeline", "relatorio", "atualizar"}
ALVOS_MAKE_ESPERADOS = {
    "setup",
    "fixtures",
    "ingerir",
    "ci",
    "pipeline",
    "docs",
    "lint",
    "sincronizar",
    "relatorio",
    "clean",
    "atualizar",
}


def subpastas_fora_da_convencao(models: Path) -> list[str]:
    encontradas = {p.relative_to(models).as_posix() for p in models.rglob("*") if p.is_dir()}
    return sorted(encontradas - SUBPASTAS_MODELS)


def modelos_fora_da_convencao(models: Path) -> list[str]:
    return sorted(
        p.name
        for p in models.rglob("*.sql")
        if not p.name.startswith(PREFIXOS_MODELOS) and p.stem not in MODELOS_ORIGINAIS_MVP
    )


def modulos_fora_da_convencao(pacote: Path) -> list[str]:
    return sorted({p.stem for p in pacote.glob("*.py")} - MODULOS_ESPERADOS)


def subcomandos_da_cli() -> set[str]:
    analisador = cli._construir_analisador()
    for acao in analisador._actions:
        if isinstance(acao, argparse._SubParsersAction):
            return set(acao.choices)
    raise AssertionError("a CLI não tem subcomandos")


def alvos_do_make(makefile: Path) -> set[str]:
    return set(re.findall(r"^([A-Za-z][\w-]*):(?!=)", makefile.read_text(), flags=re.MULTILINE))


MODELS = RAIZ / "transform" / "models"


def test_subpastas_de_models_seguem_a_convencao() -> None:
    assert subpastas_fora_da_convencao(MODELS) == []


def test_modelos_tem_prefixo_permitido_ou_sao_originais_do_mvp() -> None:
    assert modelos_fora_da_convencao(MODELS) == []


def test_modulos_do_pacote_seguem_a_convencao() -> None:
    assert modulos_fora_da_convencao(RAIZ / "src" / "rfb_pipeline") == []


def test_subcomandos_da_cli_seguem_a_convencao() -> None:
    assert subcomandos_da_cli() <= SUBCOMANDOS_ESPERADOS


def test_alvos_do_make_seguem_a_convencao() -> None:
    assert alvos_do_make(RAIZ / "Makefile") <= ALVOS_MAKE_ESPERADOS


@pytest.mark.parametrize(
    ("subpasta", "esperado"),
    [
        ("marts/analises", "marts/analises"),
        ("observabilidade", "observabilidade"),
        ("paridade", "paridade"),
        ("staging/rfb/extra", "staging/rfb/extra"),
    ],
)
def test_guarda_detecta_subpasta_fora_da_convencao(
    tmp_path: Path, subpasta: str, esperado: str
) -> None:
    copia = tmp_path / "models"
    shutil.copytree(MODELS, copia)
    assert subpastas_fora_da_convencao(copia) == []
    (copia / subpasta).mkdir(parents=True, exist_ok=True)
    assert esperado in subpastas_fora_da_convencao(copia)


def test_guarda_detecta_modelo_sem_prefixo_permitido(tmp_path: Path) -> None:
    (tmp_path / "companies.sql").write_text("select 1")
    (tmp_path / "paridade__bh_empresas_sql_original.sql").write_text("select 1")
    (tmp_path / "stg_rfb__ok.sql").write_text("select 1")
    (tmp_path / "bh_empresas.sql").write_text("select 1")
    assert modelos_fora_da_convencao(tmp_path) == [
        "companies.sql",
        "paridade__bh_empresas_sql_original.sql",
    ]


def test_guarda_detecta_modulo_fora_da_lista(tmp_path: Path) -> None:
    (tmp_path / "convert.py").write_text("")
    (tmp_path / "cli.py").write_text("")
    assert modulos_fora_da_convencao(tmp_path) == ["convert"]


def test_guarda_detecta_alvo_make_fora_da_lista(tmp_path: Path) -> None:
    makefile = tmp_path / "Makefile"
    makefile.write_text("MES ?=\n.PHONY: ingest\ningest:\n\techo\nci: X := 1\nci:\n\techo\n")
    assert alvos_do_make(makefile) == {"ingest", "ci"}
