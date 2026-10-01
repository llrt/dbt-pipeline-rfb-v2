"""Análises novas (ANA-01..04) contra o cenário de fixtures da spec (mês 2026-09).

Lê `RAIZ_DADOS` do ambiente — exportado por `make ci`, que roda `dbt build` antes do pytest.
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    "RAIZ_DADOS" not in os.environ, reason="rode via make ci (exporta RAIZ_DADOS)"
)


def test_concorrencia_fundao_tintas_1_ativo_4_inativos_0_5_por_10k(consultar) -> None:
    (linha,) = consultar(
        "select ativos, inativos, ativos_por_10k_hab, ranking_uf "
        "from {mart_concorrencia_municipio} "
        "where cnae_principal = '4741500' and municipio = 'Fundão'"
    )
    assert linha[:3] == (1, 4, 0.5)


def test_concorrencia_sem_populacao_nao_tem_densidade_nem_ranking(consultar) -> None:
    linhas = consultar(
        "select ativos_por_10k_hab, ranking_uf from {mart_concorrencia_municipio} "
        "where populacao is null"
    )
    assert linhas, "o membro -1 (exterior/sem BD) deve aparecer no mart"
    assert all(linha == (None, None) for linha in linhas)


def test_concorrencia_ranking_na_uf_para_tintas(consultar) -> None:
    # Serra (1 ativo, 520 000 hab.) < Fundão (1 ativo, 20 000 hab.): Fundão é o mais denso do ES.
    linhas = consultar(
        "select municipio, ranking_uf from {mart_concorrencia_municipio} "
        "where cnae_principal = '4741500' and uf = 'ES' order by ranking_uf"
    )
    assert linhas[0] == ("Fundão", 1)


def test_sobrevivencia_tintas_es_6_6_5_4_4_2(consultar) -> None:
    (linha,) = consultar(
        "select sum(elegiveis_1a), sum(sobreviventes_1a), sum(elegiveis_3a), "
        "sum(sobreviventes_3a), sum(elegiveis_5a), sum(sobreviventes_5a) "
        "from {mart_sobrevivencia_coorte} "
        "where cnae_principal = '4741500' and uf = 'ES'"
    )
    assert linha == (6, 6, 5, 4, 4, 2)


def test_dinamica_fundao_tintas_aberturas_e_encerramentos_por_ano(consultar) -> None:
    linhas = consultar(
        "select ano, aberturas, encerramentos, saldo from {mart_dinamica_mercado} "
        "where cnae_principal = '4741500' and municipio = 'Fundão' order by ano"
    )
    assert linhas == [
        (2010, 1, 0, 1),
        (2015, 1, 0, 1),
        (2018, 1, 0, 1),
        (2019, 0, 1, -1),
        (2020, 1, 0, 1),
        (2021, 0, 1, -1),
        (2022, 1, 0, 1),
        (2023, 0, 1, -1),
        (2024, 0, 1, -1),
    ]


def test_fornecedores_proximos_so_f_principal_e_h_secundario(consultar) -> None:
    linhas = consultar(
        "select municipio, via, distancia_km from {mart_fornecedores_proximos} "
        "order by distancia_km"
    )
    assert [(m, v) for m, v, _ in linhas] == [("Serra", "principal"), ("Linhares", "secundario")]
    assert linhas[0][2] == pytest.approx(18.66, abs=0.5)
    assert linhas[1][2] == pytest.approx(73.68, abs=0.5)
