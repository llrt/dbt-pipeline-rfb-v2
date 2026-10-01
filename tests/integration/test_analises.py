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
        "select ativos, inativos, ativos_por_10k_hab, ranking_uf from {mart_concorrencia_municipio} "
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
