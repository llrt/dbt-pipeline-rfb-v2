from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from rfb_pipeline.relatorio import PREFIXO_ANALISES as P
from rfb_pipeline.relatorio import ler_qualidade, renderizar


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


_COLUNAS_AREA = [
    "municipio",
    "nome_regiao_metropolitana",
    "domicilios_2022",
    "area_km2",
    "ativos",
    "inativos",
    "qtd_vizinhos",
    "ativos_vizinhos",
    "inativos_vizinhos",
    "ativos_regiao_metropolitana",
    "inativos_regiao_metropolitana",
    "ativos_por_mil_domicilios",
    "ativos_por_km2",
    "ativos_area_por_mil_domicilios",
    "ativos_area_por_km2",
]


# incremento: enriquecimento_bd
def test_relatorio_traz_a_area_de_mercado_do_caso() -> None:
    tabelas = _tabelas()
    tabelas[f"{P}enriquecimento_area_mercado"] = (
        _COLUNAS_AREA,
        [
            (
                "Fundão", "RM Grande Vitória", 6715, 287.0, 1, 4, 2, 1, 0, 2, 4,
                0.14892, 0.003484, 0.009675, 0.000879,
            )
        ],
    )  # fmt: skip
    texto = renderizar(tabelas, None)
    assert "## Área de mercado (enriquecimento com a Base dos Dados)" in texto
    assert "| 2 vizinhos | 1 | 0 |" in texto
    assert "| Região metropolitana (RM Grande Vitória) | 2 | 4 |" in texto
    assert "**0,1489** ativos por mil domicílios" in texto
    assert "**0,003484** por km²" in texto


# incremento: enriquecimento_bd
def test_relatorio_area_de_mercado_sem_estabelecimentos_do_cnae() -> None:
    tabelas = _tabelas()
    tabelas[f"{P}enriquecimento_area_mercado"] = (_COLUNAS_AREA, [])
    assert "não tem estabelecimentos deste CNAE" in renderizar(tabelas, None)


# incremento: enriquecimento_bd
def test_relatorio_sem_a_analysis_nao_tem_a_secao_de_area_de_mercado() -> None:
    assert "Área de mercado" not in renderizar(_tabelas(), None)


def test_ler_qualidade_sem_tabela_de_historico_devolve_none(tmp_path: Path) -> None:
    banco = tmp_path / "w.duckdb"
    duckdb.connect(str(banco)).close()
    assert ler_qualidade(banco) is None


def test_ler_qualidade_propaga_erro_que_nao_e_tabela_inexistente(tmp_path: Path) -> None:
    """RBP-08: coluna renomeada não pode virar "histórico indisponível" em silêncio."""
    banco = tmp_path / "w.duckdb"
    with duckdb.connect(str(banco)) as con:
        con.execute("create table main.dq_resumo_execucao (invocation_id varchar)")
        con.execute("create table main.dq_historico_testes (invocation_id varchar)")
    with pytest.raises(duckdb.BinderException):
        ler_qualidade(banco)


def test_ler_qualidade_inclui_avisos_e_falhas_e_exclui_aprovados(tmp_path: Path) -> None:
    banco = tmp_path / "w.duckdb"
    with duckdb.connect(str(banco)) as con:
        con.execute(
            "create table main.dq_resumo_execucao as select 'i1' as invocation_id, "
            "now() as executado_em, 3 as testes, 1 as aprovados, 1 as avisos, 1 as falhos, "
            "0 as pulados"
        )
        con.execute(
            "create table main.dq_historico_testes (invocation_id varchar, nome_teste varchar, "
            "status varchar, falhas integer, severidade varchar, escopo varchar)"
        )
        con.execute(
            "insert into main.dq_historico_testes values ('i1','t_ok','pass',0,'error','adicao'), "
            "('i1','t_aviso','warn',1,'warn','adicao'), ('i1','t_erro','fail',2,'error','adicao')"
        )
    _, pendentes = ler_qualidade(banco)
    assert [p[0] for p in pendentes] == ["t_aviso", "t_erro"]
