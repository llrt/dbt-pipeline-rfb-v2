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


@pytest.mark.parametrize(
    ("subpasta", "selecao", "exclusao"),
    [
        ("", "path:analyses", ["--exclude", "path:analyses/regras_negocio"]),  # RRN-09
        ("regras_negocio", "path:analyses/regras_negocio", []),
    ],
)
def test_compilar_analises_separa_estudo_de_caso_e_regras(
    subpasta: str, selecao: str, exclusao: list[str], tmp_path: Path, monkeypatch
) -> None:
    from rfb_pipeline import relatorio

    chamadas = []

    def _run(comando, **_):
        chamadas.append(comando)
        raise RuntimeError("parar antes de compilar")

    monkeypatch.setattr(relatorio, "_executavel_dbt", lambda: ["dbt"])
    monkeypatch.setattr(relatorio.subprocess, "run", _run)
    with pytest.raises(RuntimeError):
        relatorio.compilar_analises(tmp_path, tmp_path, "ci", subpasta=subpasta)
    (comando,) = chamadas
    assert comando[comando.index("--select") + 1] == selecao
    if exclusao:
        assert comando[comando.index("--exclude") : comando.index("--exclude") + 2] == exclusao
    else:
        assert "--exclude" not in comando


# incremento: enriquecimento_ibge
_COLUNAS_IBGE = [
    "ordem", "escopo", "municipio", "regic_hierarquia", "renda_per_capita_media_2022",
    "renda_per_capita_mediana_2022", "polo_compras", "pct_compras_no_polo", "ativos_cnae",
    "unidades_locais_cempre", "pessoal_ocupado_cempre", "tem_sigilo", "ano_cempre", "uf",
]  # fmt: skip


def _caso_ibge(*linhas: tuple) -> dict:
    tabelas = _tabelas()
    tabelas[f"{P}enriquecimento_ibge"] = (_COLUNAS_IBGE, list(linhas))
    return tabelas


_CASO = (1, "município do caso", "Iúna", "Centro Local", 900.0, 700.0, "Manhuaçu", 56.67, 0, 2, 9,
         False, 2024, "ES")  # fmt: skip
_UF = (3, "UF", "ES", None, 1650.0, None, None, None, 30, 281, 1207, True, 2024, "ES")


def test_relatorio_polo_noutra_uf_e_mostrado_com_a_uf() -> None:
    """RIBG-03: polo noutra UF (Iúna/ES -> Manhuaçu/MG) não vira "não tem polo"."""
    polo = (2, "polo de compras", "Manhuaçu", "Centro Sub-Regional A", 1500.0, 1000.0,
            "Belo Horizonte", 30.0, 4, 6, 20, False, 2024, "MG")  # fmt: skip
    texto = renderizar(_caso_ibge(_CASO, polo, _UF), None)
    assert "vão principalmente a **Manhuaçu/MG** (56,7 % desses deslocamentos)" in texto
    assert "não tem polo" not in texto


def test_relatorio_polo_fora_da_dimensao_ainda_e_citado_e_sem_polo_so_quando_nulo() -> None:
    texto = renderizar(_caso_ibge(_CASO, _UF), None)
    assert "vão principalmente a **Manhuaçu** (56,7 % desses deslocamentos)." in texto
    sem_polo = _CASO[:6] + (None, None) + _CASO[8:]
    assert "não tem polo de compras na REGIC 2018" in renderizar(_caso_ibge(sem_polo, _UF), None)


# incremento: enriquecimento_ibge — warehouse da v1.3 ainda não reconstruído (Greptile PR #7)
def test_relatorio_sem_o_gold_do_ibge_troca_a_secao_pelo_aviso() -> None:
    from rfb_pipeline.relatorio import AVISO_IBGE_NAO_CONSTRUIDO

    texto = renderizar(_tabelas(), None, AVISO_IBGE_NAO_CONSTRUIDO)
    assert "## Enriquecimento com o IBGE (renda, rede urbana e CEMPRE)" in texto
    assert (
        "> **Aviso:** dados do IBGE ainda não construídos; rode `rfb pipeline` ou "
        "`rfb atualizar --renovar-ibge`."
    ) in texto
    assert "Em Fundão/ES há **1** concorrente ativo" in texto
    assert "## Qualidade dos dados" in texto


def test_faltas_ibge_por_introspeccao_do_warehouse(tmp_path: Path) -> None:
    from rfb_pipeline.relatorio import REQUISITOS_IBGE, faltas_ibge

    warehouse = tmp_path / "warehouse.duckdb"
    with duckdb.connect(str(warehouse)) as con:  # forma da v1.3: dim e área sem as colunas novas
        con.execute(
            "create view dim_municipio as select 1 as sk_municipio, '1' as id_municipio_ibge"
        )
        con.execute("create view mart_concorrencia_area_mercado as select 1 as sk_cnae")
    faltas = faltas_ibge(warehouse)
    assert "mart_emprego_setor_municipio" in faltas
    assert "bridge_municipio_destino_compras" in faltas
    assert "dim_municipio.renda_per_capita_media_2022" in faltas
    assert "mart_concorrencia_area_mercado.ativos_no_polo" in faltas

    with duckdb.connect(str(warehouse)) as con:  # forma da v1.4
        for relacao, colunas in REQUISITOS_IBGE.items():
            selecao = ", ".join(["1 as sk", *(f"1 as {c}" for c in colunas)])
            con.execute(f"create or replace view {relacao} as select {selecao}")
    assert faltas_ibge(warehouse) == []
