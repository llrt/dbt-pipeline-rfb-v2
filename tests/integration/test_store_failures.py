"""DQ-01 AC 3: todo teste que pode avisar guarda as linhas com falha (`store_failures`).

Lê `transform/target/manifest.json`, gerado pelo `dbt build` do `make ci`. Um teste "pode avisar"
quando a severidade é `warn` **ou** quando `warn_if`/`error_if` diferem do padrão (`!=0`): com
severidade `error`, um `error_if` maior que o `warn_if` abre uma faixa de aviso (R3-13).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

MANIFESTO = Path(__file__).resolve().parents[2] / "transform" / "target" / "manifest.json"
PADRAO = "!=0"

pytestmark = pytest.mark.skipif(
    not MANIFESTO.is_file(), reason="rode via make ci (gera o manifesto do dbt)"
)


def _limite(config: dict, chave: str) -> str:
    return str(config.get(chave, PADRAO)).replace(" ", "")


def pode_avisar(config: dict) -> bool:
    return (
        str(config.get("severity", "error")).lower() == "warn"
        or _limite(config, "warn_if") != PADRAO
        or _limite(config, "error_if") != PADRAO
    )


def avisam_sem_store_failures(manifesto: dict) -> list[str]:
    return sorted(
        no["name"]
        for no in manifesto["nodes"].values()
        if no["resource_type"] == "test"
        and no["package_name"] == "rfb"
        and pode_avisar(no["config"])
        and not no["config"].get("store_failures")
    )


def test_guarda_reprova_teste_que_avisa_so_por_warn_if_ou_error_if() -> None:
    def no(config: dict) -> dict:
        return {"resource_type": "test", "package_name": "rfb", "name": "t", "config": config}

    assert avisam_sem_store_failures({"nodes": {"a": no({"severity": "warn"})}}) == ["t"]
    assert avisam_sem_store_failures({"nodes": {"a": no({"error_if": ">100"})}}) == ["t"]
    assert avisam_sem_store_failures({"nodes": {"a": no({"severity": "error"})}}) == []
    assert (
        avisam_sem_store_failures(
            {"nodes": {"a": no({"error_if": ">100", "store_failures": True})}}
        )
        == []
    )


def test_todo_teste_que_pode_avisar_guarda_as_falhas() -> None:
    manifesto = json.loads(MANIFESTO.read_text(encoding="utf-8"))
    assert avisam_sem_store_failures(manifesto) == []
