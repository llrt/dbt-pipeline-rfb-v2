from __future__ import annotations

from rfb_pipeline.relatorio import PREFIXO_ANALISES as P
from rfb_pipeline.relatorio import renderizar


def _tabelas() -> dict:
    q1_colunas = ["municipio", "uf", "porte", "situacao", "qtd_empresas", "media_idade"]
    return {
        f"{P}parametros": (
            [
                "cnae_alvo",
                "municipio",
                "uf",
                "cnaes_fornecedores",
                "raio_fornecedores_km",
                "mes_referencia",
                "data_referencia",
            ],
            [("4741500", "FUNDÃO", "ES", "2071100", 100, "2026-09", "2026-09-12")],
        ),
        f"{P}q1_concorrentes": (
            q1_colunas,
            [
                ("FUNDÃO", "ES", "MICRO", "ATIVA", 1, 3.9),
                ("FUNDÃO", "ES", "MICRO", "INATIVA", 3, None),
                ("FUNDÃO", "ES", None, "INATIVA", 1, None),
            ],
        ),
        f"{P}q2_q3_idade_porte": (["porte", "media_idade", "qtd_empresas"], [("MICRO", 3.9, 1)]),
        f"{P}q4_fornecedores_resumo": (["ordem", "busca", "qtd_empresas"], [(1, "x", 0)]),
        f"{P}q4_fornecedores_secundarios_uf": (["cnpj_completo"], []),
        f"{P}adicao_concorrencia": (
            ["municipio", "ativos", "inativos", "ativos_por_10k_hab", "ranking_uf"],
            [("Fundão", 1, 4, 0.5, 1)],
        ),
        f"{P}adicao_sobrevivencia": (
            [f"{k}_{n}a" for n in (1, 3, 5) for k in ("elegiveis", "sobreviventes", "taxa")],
            [(6, 6, 1.0, 5, 4, 0.8, 4, 2, 0.5)],
        ),
        f"{P}adicao_dinamica": (["ano", "aberturas"], [(2010, 1)]),
        f"{P}adicao_fornecedores_proximos": (["cnpj_completo", "distancia_km"], []),
    }


def test_relatorio_afirma_concorrentes_ativos_e_inativos_do_caso() -> None:
    texto = renderizar(_tabelas(), None)
    assert "Em Fundão/ES há **1** concorrente ativo e **4** inativos no CNAE 4741500." in texto
    assert "| 3 anos | 5 | 4 | 80,0% |" in texto
    assert "Histórico de testes indisponível" in texto


def test_relatorio_secao_de_qualidade_lista_testes_que_nao_passaram() -> None:
    resumo = {
        "invocation_id": "abc",
        "executado_em": "2026-10-01 00:00:00.123",
        "testes": 1,
        "aprovados": 0,
        "avisos": 1,
        "falhos": 0,
        "pulados": 0,
    }
    texto = renderizar(_tabelas(), (resumo, [("cnaes_sem_par_bd", "warn", 1, "warn", "original")]))
    assert "**1** teste: 0 aprovados, 1 avisos" in texto
    assert "`cnaes_sem_par_bd` | warn | 1 | warn | original" in texto
    assert "> Execução dbt `abc` em 2026-10-01 00:00:00." in texto


def test_relatorio_media_de_idade_e_ponderada_por_qtd_empresas() -> None:
    """R3-16: com dois portes ativos, a média é ponderada (e não a do primeiro porte)."""
    tabelas = _tabelas()
    tabelas[f"{P}q2_q3_idade_porte"] = (
        ["porte", "media_idade", "qtd_empresas"],
        [("DEMAIS", 10.0, 1), ("MICRO", 4.0, 3)],
    )
    texto = renderizar(tabelas, None)
    assert (
        "Idade média das ativas: **5,5** anos (média ponderada por `qtd_empresas`, 4 empresas)."
        in texto
    )


def test_relatorio_tabelas_longas_mostram_top_20_e_o_total() -> None:
    tabelas = _tabelas()
    tabelas[f"{P}adicao_fornecedores_proximos"] = (
        ["cnpj_completo", "distancia_km"],
        [(f"{i:014d}", float(i)) for i in range(1, 46)],
    )
    texto = renderizar(tabelas, None)
    assert "| 00000000000020 | 20,00 |" in texto
    assert "| 00000000000021 |" not in texto
    assert "_Mostrando as 20 primeiras de 45 linhas._" in texto


def test_relatorio_traz_nota_de_interpretacao_de_ativa_e_da_adaptacao_da_q4() -> None:
    texto = renderizar(_tabelas(), None)
    assert '"ativa" é a situação cadastral da Receita Federal, não operação efetiva' in texto
    assert "o notebook 4 original retornava 0 nas buscas por microrregião" in texto
