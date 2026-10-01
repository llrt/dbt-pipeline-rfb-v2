"""Enriquecimento com bases da Base dos Dados (ENR-02/03, ADR-0015) contra o cenário de fixtures.

Lê `RAIZ_DADOS` do ambiente — exportado por `make ci`, que roda `dbt build` antes do pytest.
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    "RAIZ_DADOS" not in os.environ, reason="rode via make ci (exporta RAIZ_DADOS)"
)


# incremento: enriquecimento_bd
def test_fundao_atributos_do_censo_2022_e_regiao_metropolitana(consultar) -> None:
    (linha,) = consultar(
        "select populacao_censo_2022, domicilios_2022, area_km2, densidade_hab_km2, "
        "taxa_alfabetizacao, idade_mediana, indice_envelhecimento, razao_sexo, "
        "nome_regiao_metropolitana from {dim_municipio} where sk_municipio = 3202207"
    )
    assert linha == (17951, 6715, 287.0, 62.55, 0.93371, 37.0, 67.68, 97.67, "RM Grande Vitória")


# incremento: enriquecimento_bd
def test_regiao_metropolitana_nao_pertence_e_nao_informado(consultar) -> None:
    linhas = dict(
        consultar("select nome_municipio, nome_regiao_metropolitana from {dim_municipio}")
    )
    assert linhas["Linhares"] == "NÃO PERTENCE"
    assert linhas["Aracruz"] == "NÃO PERTENCE"
    assert linhas["NÃO INFORMADO"] == "NÃO INFORMADO"
    assert {m for m, rm in linhas.items() if rm == "RM Grande Vitória"} == {
        "Fundão",
        "Serra",
        "Vitória",
    }


# incremento: enriquecimento_bd
def test_municipio_sem_censo_tem_atributos_e_densidade_nulos(consultar) -> None:
    linhas = consultar(
        "select densidade_hab_km2, domicilios_2022, area_km2 from {dim_municipio} "
        "where sk_municipio = 2200202"  # Água Branca/PI: fora do Censo da fixture
    )
    assert linhas == [(None, None, None)]


# incremento: enriquecimento_bd
def test_vizinhos_de_fundao_sao_aracruz_e_serra(consultar) -> None:
    linhas = consultar(
        "select viz.nome_municipio from {bridge_municipio_vizinho} as b "
        "join {dim_municipio} as viz on b.sk_municipio_vizinho = viz.sk_municipio "
        "where b.sk_municipio = 3202207 order by 1"
    )
    assert linhas == [("Aracruz",), ("Serra",)]


# incremento: enriquecimento_bd
def test_vizinhanca_simetrica_sem_autopar_e_so_ano_recente(consultar) -> None:
    pares = {tuple(p) for p in consultar("select * from {bridge_municipio_vizinho}")}
    assert len(pares) == len(consultar("select * from {bridge_municipio_vizinho}"))
    assert all((b, a) in pares for a, b in pares)
    assert all(a != b for a, b in pares)
    assert (3202207, 3203205) not in pares  # Fundão–Linhares só existe em 2019
    assert len(pares) == 8  # Fundão–Aracruz/Serra, Serra–Vitória, Aracruz–Linhares (x2 sentidos)
