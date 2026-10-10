"""ADR-0018: a ontologia `docs/ontologia/rfb_cnpj.ttl` está em dia com a camada semântica.

Cobertura nos dois sentidos, para a documentação não envelhecer:

- todo nome que a ontologia mapeia (`rfbo:entidadeSemantica`, `rfbo:dimensaoSemantica`,
  `rfbo:metricaDbt`, `rfbo:modeloDbt`, `rfbo:colunaDbt`) existe em
  `transform/target/semantic_manifest.json` ou no `manifest.json`;
- toda entidade semântica e toda métrica do manifesto está mapeada em algum conceito;
- afinidade (RSEM-08): toda métrica está num conceito que anota o modelo semântico dela, pela
  entidade, pelo modelo, pelo modelo de uma coluna ou pela entidade de uma dimensão. Pega a
  métrica mapeada no conceito errado (`qtd_ativos_mei` em `Porte`, por exemplo).

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


def _ancoras_das_metricas() -> dict[str, set[str]]:
    """Modelos semânticos (e as entidades principais deles) de onde cada métrica tira os dados."""
    semantico = json.loads((TARGET / "semantic_manifest.json").read_text(encoding="utf-8"))
    entidade = {
        modelo["name"]: {e["name"] for e in modelo["entities"] if e["type"] == "primary"}
        | ({modelo["primary_entity"]} if modelo.get("primary_entity") else set())
        for modelo in semantico["semantic_models"]
    }
    metricas = {m["name"]: m for m in semantico["metrics"]}

    def ancoras(nome: str) -> set[str]:
        parametros = metricas[nome]["type_params"]
        if parametros.get("metric_aggregation_params"):
            modelo = parametros["metric_aggregation_params"]["semantic_model"]
            return {modelo} | entidade[modelo]
        entradas = [parametros.get("numerator"), parametros.get("denominator")]
        entradas += parametros.get("metrics") or []
        return set().union(*(ancoras(e["name"]) for e in entradas if e))

    return {nome: ancoras(nome) for nome in metricas}


def _ancoras_do_conceito(grafo: Graph, conceito: URIRef) -> set[str]:
    """Nomes do projeto que o conceito anota, reduzidos a modelo ou entidade."""

    def valores(anotacao: str) -> set[str]:
        return {str(v) for v in grafo.objects(conceito, RFBO[anotacao])}

    return (
        valores("entidadeSemantica")
        | valores("modeloDbt")
        | {coluna.split(".", 1)[0] for coluna in valores("colunaDbt")}
        | {dimensao.split("__", 1)[0] for dimensao in valores("dimensaoSemantica")}
    )


@sem_manifesto
def test_metrica_esta_num_conceito_do_mesmo_modelo_semantico(grafo: Graph) -> None:
    ancoras = _ancoras_das_metricas()
    sem_afinidade = []
    for conceito, valor in grafo.subject_objects(RFBO.metricaDbt):
        metrica = str(valor)
        if not ancoras[metrica] & _ancoras_do_conceito(grafo, conceito):
            modelos = sorted(ancoras[metrica])
            sem_afinidade.append(f"{grafo.qname(conceito)} rfbo:metricaDbt {metrica!r} ({modelos})")
    erro = "métrica num conceito que não anota o modelo dela:\n" + "\n".join(sem_afinidade)
    assert not sem_afinidade, erro
