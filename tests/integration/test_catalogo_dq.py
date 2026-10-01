"""DQ-02 AC 5 (R3-12): `docs/QUALIDADE_DADOS.md` é o catálogo que o manifesto atual geraria.

Lê `transform/target/manifest.json`, gerado pelo `dbt build` do `make ci`. Se falhar, rode
`uv run python scripts/gerar_qualidade_dados.py` (depois do `make ci`) e versione o resultado.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
MANIFESTO = RAIZ / "transform" / "target" / "manifest.json"
CATALOGO = RAIZ / "docs" / "QUALIDADE_DADOS.md"

sys.path.insert(0, str(RAIZ / "scripts"))

import gerar_qualidade_dados  # noqa: E402

pytestmark = pytest.mark.skipif(
    not MANIFESTO.is_file(), reason="rode via make ci (gera o manifesto do dbt)"
)


def test_catalogo_versionado_bate_com_o_manifesto() -> None:
    manifesto = json.loads(MANIFESTO.read_text(encoding="utf-8"))
    esperado = gerar_qualidade_dados.gerar(manifesto)
    assert CATALOGO.read_text(encoding="utf-8") == esperado, (
        "docs/QUALIDADE_DADOS.md desatualizado: rode "
        "`uv run python scripts/gerar_qualidade_dados.py`"
    )
