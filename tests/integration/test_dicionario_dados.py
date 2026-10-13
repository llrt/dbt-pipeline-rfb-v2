# ruff: noqa: E501
"""ADR-0019: `docs/DICIONARIO_DADOS.md` é o dicionário que o manifesto e o catálogo atuais gerariam.

Usa o `manifest.json` e o `catalog.json` de `dbt docs generate` sobre o warehouse do `make ci`
(fixture `manifesto_e_catalogo`). Se falhar, rode `make dicionario` e versione o resultado.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
DICIONARIO = RAIZ / "docs" / "DICIONARIO_DADOS.md"
SCRIPT = RAIZ / "scripts" / "gerar_dicionario_dados.py"

sys.path.insert(0, str(RAIZ / "scripts"))

import gerar_dicionario_dados  # noqa: E402

pytestmark = pytest.mark.skipif(
    "RAIZ_DADOS" not in os.environ, reason="rode via make ci (exporta RAIZ_DADOS)"
)

# Prefixos de nome de modelo/seed/fonte do projeto: citá-los entre crases exige que existam.
PREFIXOS = ("stg_", "int_", "dim_", "fct_", "bridge_", "mart_", "audit__", "dominio_", "dq_")


def _carregar(manifesto_e_catalogo) -> tuple[dict, dict]:
    manifesto, catalogo = (json.loads(p.read_text(encoding="utf-8")) for p in manifesto_e_catalogo)
    return manifesto, catalogo


def test_verificar_passa_com_o_dicionario_versionado(manifesto_e_catalogo) -> None:
    """O gerador em modo `--verificar` (gera em memória e compara) aceita o arquivo versionado."""
    manifesto, catalogo = manifesto_e_catalogo
    resultado = subprocess.run(
        [sys.executable, str(SCRIPT), "--verificar", "--manifesto", str(manifesto),
         "--catalogo", str(catalogo), "--saida", str(DICIONARIO)],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    assert resultado.returncode == 0, (
        "docs/DICIONARIO_DADOS.md desatualizado: rode `make dicionario`\n" + resultado.stderr
    )


def test_dicionario_versionado_bate_com_o_manifesto(manifesto_e_catalogo) -> None:
    manifesto, catalogo = _carregar(manifesto_e_catalogo)
    esperado = gerar_dicionario_dados.gerar(manifesto, catalogo)
    assert DICIONARIO.read_text(encoding="utf-8") == esperado, (
        "docs/DICIONARIO_DADOS.md desatualizado: rode `make dicionario`"
    )


def test_toda_tabela_e_coluna_real_esta_no_dicionario(manifesto_e_catalogo) -> None:
    """Cada modelo, seed e fonte do projeto tem seção; cada coluna real do catálogo tem linha."""
    manifesto, catalogo = _carregar(manifesto_e_catalogo)
    texto = DICIONARIO.read_text(encoding="utf-8")
    secoes = set(re.findall(r"^#### `([^`]+)`$", texto, flags=re.M))
    esperadas = {
        n["name"]
        for n in manifesto["nodes"].values()
        if n["package_name"] == "rfb" and n["resource_type"] in ("model", "seed")
    } | {
        f"{s['source_name']}.{s['name']}"
        for s in manifesto["sources"].values()
        if s["package_name"] == "rfb"
    }
    assert secoes == esperadas
    for unique_id, no in catalogo["nodes"].items():
        declarado = manifesto["nodes"].get(unique_id)
        if declarado is None or declarado["resource_type"] not in ("model", "seed"):
            continue
        secao = texto.split(f"#### `{declarado['name']}`\n", 1)[1].split("\n#### ", 1)[0]
        for coluna in no["columns"]:
            assert f"| `{coluna.lower()}` |" in secao.lower(), f"{declarado['name']}.{coluna}"


def test_links_e_ancoras_do_dicionario_resolvem() -> None:
    texto = DICIONARIO.read_text(encoding="utf-8")
    ancoras = set(re.findall(r'<a id="([^"]+)"></a>', texto))
    internos = set(re.findall(r"\]\(#([^)]+)\)", texto))
    assert not internos - ancoras, f"links sem âncora: {sorted(internos - ancoras)}"
    for alvo in set(re.findall(r"\]\(((?:adr/)?[A-Z0-9a-z_./-]+\.md)\)", texto)):
        assert (RAIZ / "docs" / alvo).is_file(), f"link quebrado: {alvo}"


def test_identificadores_de_tabela_citados_existem(manifesto_e_catalogo) -> None:
    """Todo `stg_*`/`dim_*`/... entre crases (descrições vindas dos YAMLs inclusive) existe no projeto."""
    manifesto, _ = _carregar(manifesto_e_catalogo)
    existentes = {n["name"] for n in manifesto["nodes"].values() if n["package_name"] == "rfb"}
    existentes |= {s["name"] for s in manifesto["sources"].values() if s["package_name"] == "rfb"}
    existentes |= {m["name"] for m in manifesto["macros"].values() if m["package_name"] == "rfb"}
    inexistentes = set()
    for citado in re.findall(r"`([^`\n]+)`", DICIONARIO.read_text(encoding="utf-8")):
        base = re.split(r"[.\s(]", citado)[0]
        if base.startswith(PREFIXOS) and base not in existentes and not base.endswith("*"):
            inexistentes.add(base)
    assert not inexistentes, f"identificadores inexistentes no dicionário: {sorted(inexistentes)}"
