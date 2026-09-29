"""ADR-0006: todo nó do projeto dbt (`rfb`) declara `meta.escopo` (R1-13).

Lê `transform/target/manifest.json`, gerado pelo `dbt build` do `make ci` (que roda antes do
pytest de integração). Sem o manifesto, o teste é pulado.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

MANIFESTO = Path(__file__).resolve().parents[2] / "transform" / "target" / "manifest.json"
ESCOPOS = {"original", "adicao", "adaptado"}

pytestmark = pytest.mark.skipif(not MANIFESTO.is_file(), reason="rode `dbt build` antes")


def test_todos_os_nos_do_projeto_tem_meta_escopo() -> None:
    manifesto = json.loads(MANIFESTO.read_text(encoding="utf-8"))
    sem_escopo: list[str] = []
    total = 0
    for secao in ("nodes", "sources", "macros", "unit_tests"):
        for id_no, no in manifesto.get(secao, {}).items():
            if no.get("package_name") != "rfb":
                continue
            total += 1
            meta = no.get("meta") or (no.get("config") or {}).get("meta") or {}
            if meta.get("escopo") not in ESCOPOS:
                sem_escopo.append(id_no)
    assert total > 0
    assert sem_escopo == []
