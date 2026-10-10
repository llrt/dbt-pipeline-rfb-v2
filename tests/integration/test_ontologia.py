"""ADR-0018: a ontologia `docs/ontologia/rfb_cnpj.ttl` está em dia com a camada semântica.

Cobertura nos dois sentidos, para a documentação não envelhecer:

- todo nome que a ontologia mapeia (`rfbo:entidadeSemantica`, `rfbo:dimensaoSemantica`,
  `rfbo:metricaDbt`, `rfbo:modeloDbt`, `rfbo:colunaDbt`) existe em
  `transform/target/semantic_manifest.json` ou no `manifest.json`;
- toda entidade semântica e toda métrica do manifesto está mapeada em algum conceito.

Os manifestos vêm do `dbt parse` do `make ci`; sem eles, os testes de cobertura são pulados.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from rdflib import OWL, RDF, RDFS, Graph, Namespace, URIRef

RAIZ = Path(__file__).resolve().parents[2]
ONTOLOGIA = RAIZ / "docs" / "ontologia" / "rfb_cnpj.ttl"
TARGET = RAIZ / "transform" / "target"
RFBO = Namespace("https://github.com/llrt/dbt-pipeline-rfb-v2/ontologia/rfb_cnpj#")

sem_manifesto = pytest.mark.skipif(
    not (TARGET / "semantic_manifest.json").is_file() or not (TARGET / "manifest.json").is_file(),
    reason="rode via make ci (gera os manifestos do dbt)",
)


@pytest.fixture(scope="module")
def grafo() -> Graph:
    return Graph().parse(ONTOLOGIA, format="turtle")


def _mapeados(grafo: Graph, propriedade: URIRef) -> Iterator[tuple[str, str]]:
    """(conceito, nome) para cada valor da anotação `propriedade`."""
    for conceito, nome in grafo.subject_objects(propriedade):
        yield grafo.qname(conceito), str(nome)


def _nomes_do_projeto() -> dict[str, set[str]]:
    """Nomes válidos por tipo de anotação, lidos dos manifestos do dbt."""
    semantico = json.loads((TARGET / "semantic_manifest.json").read_text(encoding="utf-8"))
    manifesto = json.loads((TARGET / "manifest.json").read_text(encoding="utf-8"))
    entidades: set[str] = set()
    dimensoes: set[str] = set()
    for modelo in semantico["semantic_models"]:
        chaves = {e["name"] for e in modelo["entities"]}
        entidades |= chaves
        principais = {e["name"] for e in modelo["entities"] if e["type"] == "primary"}
        principais |= {modelo["primary_entity"]} if modelo.get("primary_entity") else set()
        entidades |= principais
        dimensoes |= {f"{p}__{d['name']}" for p in principais for d in modelo["dimensions"]}
    nos = [
        no for no in manifesto["nodes"].values() if no["resource_type"] in ("model", "seed")
    ]  # fmt: skip
    return {
        "entidadeSemantica": entidades,
        "dimensaoSemantica": dimensoes,
        "metricaDbt": {m["name"] for m in semantico["metrics"]},
        "modeloDbt": {no["name"] for no in nos},
        "colunaDbt": {f"{no['name']}.{coluna}" for no in nos for coluna in no["columns"]},
    }


def test_conceitos_tem_rotulo_e_comentario_em_portugues(grafo: Graph) -> None:
    sem_texto = []
    for tipo in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty):
        for recurso in grafo.subjects(RDF.type, tipo):
            rotulos = [r for r in grafo.objects(recurso, RDFS.label) if r.language == "pt"]
            comentarios = [c for c in grafo.objects(recurso, RDFS.comment) if c.language == "pt"]
            if not rotulos or (tipo == OWL.Class and not comentarios):
                sem_texto.append(grafo.qname(recurso))
    assert not sem_texto, f"sem rdfs:label (ou rdfs:comment, nas classes) @pt: {sorted(sem_texto)}"


@sem_manifesto
def test_todo_nome_mapeado_existe_no_projeto(grafo: Graph) -> None:
    validos = _nomes_do_projeto()
    inexistentes = [
        f"{conceito} rfbo:{anotacao} {nome!r}"
        for anotacao, nomes in validos.items()
        for conceito, nome in _mapeados(grafo, RFBO[anotacao])
        if nome not in nomes
    ]
    assert not inexistentes, "nomes que não existem nos manifestos:\n" + "\n".join(inexistentes)


@sem_manifesto
def test_toda_entidade_e_metrica_do_manifesto_esta_mapeada(grafo: Graph) -> None:
    validos = _nomes_do_projeto()
    for anotacao in ("entidadeSemantica", "metricaDbt"):
        mapeados = {nome for _, nome in _mapeados(grafo, RFBO[anotacao])}
        faltantes = validos[anotacao] - mapeados
        assert not faltantes, f"sem conceito na ontologia (rfbo:{anotacao}): {sorted(faltantes)}"
