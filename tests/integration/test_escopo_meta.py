"""ADR-0006 / DQ-01 AC 6: todo nó do projeto dbt (`rfb`) declara `meta.escopo` e a tag `escopo_*`.

Lê `transform/target/manifest.json`, gerado pelo `dbt build` do `make ci` (que roda antes do
pytest de integração). Sem o manifesto, o teste é pulado. Regras:

- modelos, seeds, fontes, testes unitários e analyses: `meta.escopo` válido + exatamente uma
  tag `escopo_*`, igual ao valor de `meta.escopo`;
- testes de dados (genéricos e singulares): `meta.escopo` válido + a tag `escopo_<meta.escopo>`;
  o dbt propaga as tags da fonte/modelo pai ao teste, então tags de escopo extras são toleradas
  (ex.: teste `adicao` sobre uma fonte `original`);
- macros (incl. testes genéricos): `meta.escopo` válido (macros não têm tags no dbt);
- incremento (ADR-0015): `meta.incremento` e a tag `incremento_<valor>` andam juntos — falha se um
  nó tiver o meta sem a tag ou a tag sem o meta (macros: só checa o valor do meta, sem tags);
- hooks `on-run-*` (nós `operation`): ignorados — não aceitam config no dbt; a macro que chamam
  já é verificada.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

MANIFESTO = Path(__file__).resolve().parents[2] / "transform" / "target" / "manifest.json"
ESCOPOS = {"original", "adicao", "adaptado"}
SECOES = ("nodes", "sources", "macros", "unit_tests", "exposures")


def _problemas_incremento(id_no: str, secao: str, no: dict) -> list[str]:
    """`meta.incremento` sem a tag `incremento_<valor>` (ou a tag sem o meta) -> problema."""
    config = no.get("config") or {}
    incremento = (no.get("meta") or config.get("meta") or {}).get("incremento")
    if secao == "macros":
        return []
    todas = no.get("tags") or config.get("tags") or []
    tags = sorted(t for t in todas if t.startswith("incremento_"))
    esperado = [f"incremento_{incremento}"] if incremento else []
    if tags != esperado:
        return [f"{id_no}: meta.incremento={incremento!r} incoerente com as tags {tags}"]
    return []


def nos_com_problema(manifesto: dict) -> list[str]:
    """Lista `id: motivo` dos nós do projeto sem escopo coerente (meta + tag)."""
    problemas: list[str] = []
    for secao in SECOES:
        for id_no, no in manifesto.get(secao, {}).items():
            if no.get("package_name") != "rfb":
                continue
            if no.get("resource_type") == "operation":
                continue
            config = no.get("config") or {}
            escopo = (no.get("meta") or config.get("meta") or {}).get("escopo")
            problemas.extend(
                _problemas_incremento(id_no, secao, no)
            )  # incremento: enriquecimento_bd
            if escopo not in ESCOPOS:
                problemas.append(f"{id_no}: meta.escopo ausente ou inválido ({escopo!r})")
                continue
            if secao == "macros":
                continue
            todas = no.get("tags") or config.get("tags") or []
            tags = [t for t in todas if t.startswith("escopo_")]
            esperado = f"escopo_{escopo}"
            if no.get("resource_type") == "test":
                coerente = esperado in tags
            else:
                coerente = tags == [esperado]
            if not coerente:
                problemas.append(f"{id_no}: tags de escopo {tags} != ['escopo_{escopo}']")
    return problemas


def test_validador_reprova_no_sem_tag_ou_com_tag_incoerente() -> None:
    def manifesto(tags: list[str], escopo: str = "adicao") -> dict:
        no = {"package_name": "rfb", "meta": {"escopo": escopo}, "tags": tags}
        return {"nodes": {"model.rfb.m": no}}

    assert nos_com_problema(manifesto(["escopo_adicao"])) == []
    assert len(nos_com_problema(manifesto([]))) == 1
    assert len(nos_com_problema(manifesto(["escopo_original"]))) == 1
    assert len(nos_com_problema(manifesto(["escopo_adicao", "escopo_original"]))) == 1
    teste = {"package_name": "rfb", "resource_type": "test", "meta": {"escopo": "adicao"}}
    herdada = {"nodes": {"t": {**teste, "tags": ["escopo_adicao", "escopo_original"]}}}
    assert nos_com_problema(herdada) == []  # teste tolera tag herdada da fonte
    assert len(nos_com_problema({"nodes": {"t": {**teste, "tags": ["escopo_original"]}}})) == 1
    assert len(nos_com_problema(manifesto(["escopo_adicao"], escopo="inexistente"))) == 1
    sem_meta = {"nodes": {"m": {"package_name": "rfb", "tags": ["escopo_adicao"]}}}
    assert len(nos_com_problema(sem_meta)) == 1
    de_terceiros = {"nodes": {"m": {"package_name": "dbt_utils"}}}
    assert nos_com_problema(de_terceiros) == []


# incremento: enriquecimento_bd
def test_validador_exige_coerencia_entre_meta_incremento_e_tag() -> None:
    def manifesto(meta: dict, tags: list[str]) -> dict:
        no = {"package_name": "rfb", "meta": {"escopo": "adicao", **meta}, "tags": tags}
        return {"nodes": {"model.rfb.m": no}}

    ok = manifesto(
        {"incremento": "enriquecimento_bd"}, ["escopo_adicao", "incremento_enriquecimento_bd"]
    )
    assert nos_com_problema(ok) == []
    assert nos_com_problema(manifesto({}, ["escopo_adicao"])) == []
    sem_tag = manifesto({"incremento": "enriquecimento_bd"}, ["escopo_adicao"])
    assert len(nos_com_problema(sem_tag)) == 1
    sem_meta = manifesto({}, ["escopo_adicao", "incremento_enriquecimento_bd"])
    assert len(nos_com_problema(sem_meta)) == 1
    outra_tag = manifesto(
        {"incremento": "enriquecimento_bd"}, ["escopo_adicao", "incremento_outro"]
    )
    assert len(nos_com_problema(outra_tag)) == 1


@pytest.mark.skipif(not MANIFESTO.is_file(), reason="rode `dbt build` antes")
def test_todos_os_nos_do_projeto_tem_meta_escopo_e_tag_coerente() -> None:
    manifesto = json.loads(MANIFESTO.read_text(encoding="utf-8"))
    total = sum(
        1
        for secao in SECOES
        for no in manifesto.get(secao, {}).values()
        if no.get("package_name") == "rfb"
    )
    assert total > 0
    assert nos_com_problema(manifesto) == []
