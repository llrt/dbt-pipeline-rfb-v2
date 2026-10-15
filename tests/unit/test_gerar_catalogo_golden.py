# ruff: noqa: E501  (textos e SQL de exemplo)
"""Regras do gerador do catálogo das golden queries (ADR-0023), sem dbt nem warehouse."""

from __future__ import annotations

import datetime as dt
import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))

import gerar_catalogo_golden as g  # noqa: E402

CONCEITOS = {"porte", "renda"}
SQL_VALIDO = """{# ---
id: gq_core__porte__01
conceito: porte
camada: core
perguntas: ["Quantas micro?", "Quantas por porte?"]
intencao: "Ativos por porte."
tabelas: [fct_estabelecimentos, dim_porte]
colunas_chave: [sk_porte]
armadilhas: ["MEI não é porte."]
variacoes: ["Por UF."]
resposta_esperada_fixtures:
  colunas: [rotulo_porte, ativos]
  linhas:
    - [MICRO, 4]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select por.rotulo_porte, count(*) as ativos
from {{ ref('fct_estabelecimentos') }} as fct
inner join {{ ref('dim_porte') }} as por on fct.sk_porte = por.sk_porte
group by all
order by 1
"""


def _validar(texto: str, nome: str = "gq_core__porte__01") -> list[str]:
    return g.validar_cabecalho(g.ler_cabecalho(texto), nome, texto, CONCEITOS)


def test_cabecalho_valido_passa() -> None:
    assert _validar(SQL_VALIDO) == []


def test_sem_cabecalho_falha() -> None:
    with pytest.raises(g.CatalogoErro, match="falta o cabeçalho"):
        g.ler_cabecalho("select 1")


@pytest.mark.parametrize(
    ("troca", "esperado"),
    [
        (('intencao: "Ativos por porte."\n', ""), "faltam os campos intencao"),
        (("camada: core", "camada: gold"), "camada inválida"),
        (("conceito: porte", "conceito: tamanho"), "fora da matriz"),
        (
            ('perguntas: ["Quantas micro?", "Quantas por porte?"]', 'perguntas: ["Só uma?"]'),
            "de 2 a 4",
        ),
        (
            ("tabelas: [fct_estabelecimentos, dim_porte]", "tabelas: [fct_estabelecimentos]"),
            "difere das relações",
        ),
        (("order by 1\n", ""), "order by"),
        (("'golden_query'", "'outra'"), "golden_query"),
        (("id: gq_core__porte__01", "id: gq_core__porte__02"), "difere do nome do arquivo"),
        (("    - [MICRO, 4]", "    - [MICRO]"), "tamanho de `colunas`"),
        (('armadilhas: ["MEI não é porte."]', "armadilhas: []"), "`armadilhas`"),
    ],
)
def test_cabecalho_invalido_e_apontado(troca: tuple[str, str], esperado: str) -> None:
    texto = SQL_VALIDO.replace(*troca)
    assert texto != SQL_VALIDO
    problemas = _validar(texto)
    assert any(esperado in p for p in problemas), problemas


def test_relacoes_citadas_no_cabecalho_nao_contam_como_do_sql() -> None:
    texto = SQL_VALIDO.replace(
        'variacoes: ["Por UF."]', "variacoes: [\"Use {{ ref('dim_municipio') }}.\"]"
    )
    assert _validar(texto) == []


def test_nome_do_arquivo_precisa_bater_com_camada_e_conceito() -> None:
    assert any(
        "difere" in p or "diferem" in p for p in _validar(SQL_VALIDO, "gq_analytics__porte__01")
    )


def _matriz(sem_query: dict) -> dict:
    return {
        "camadas": [{"id": c} for c in g.CAMADAS],
        "conceitos": [{"id": "porte"}, {"id": "renda"}],
        "sem_query": sem_query,
    }


def _completa() -> tuple[dict, list[str]]:
    ids = [f"gq_{c}__porte__01" for c in g.CAMADAS]
    motivos = {"renda": {c: "não se aplica" for c in g.CAMADAS}}
    return _matriz(motivos), ids


def test_matriz_completa_passa() -> None:
    matriz, ids = _completa()
    assert g.problemas_de_cobertura(matriz, ids) == []


def test_celula_sem_query_nem_motivo_falha() -> None:
    matriz, ids = _completa()
    del matriz["sem_query"]["renda"]["raw"]
    assert g.problemas_de_cobertura(matriz, ids) == ["renda × raw: sem golden query e sem motivo"]


def test_celula_com_query_e_motivo_falha() -> None:
    matriz, ids = _completa()
    matriz["sem_query"]["porte"] = {"core": "motivo"}
    assert "porte × core: tem golden query e motivo ao mesmo tempo" in g.problemas_de_cobertura(
        matriz, ids
    )


def test_motivo_que_cita_id_inexistente_falha() -> None:
    matriz, ids = _completa()
    matriz["sem_query"]["renda"]["core"] = "use gq_core__renda__07"
    assert any("gq_core__renda__07" in p for p in g.problemas_de_cobertura(matriz, ids))


@pytest.mark.parametrize(
    "coluna",
    ["nome", "razao_social", "nome_fantasia", "cpf", "email", "telefone1", "ddd1", "logradouro", "bairro",
     "cep", "numero", "complemento", "nome_socio", "estabelecimento__nome_fantasia"],
)  # fmt: skip
def test_colunas_de_pessoa_contato_ou_endereco_sao_proibidas(coluna: str) -> None:
    assert g.colunas_proibidas([coluna]) == [coluna]


@pytest.mark.parametrize(
    "coluna",
    ["nome_municipio", "nome_uf", "nome_regiao_metropolitana", "nome_municipio_polo_compras", "nome_mes",
     "municipio", "uf", "ativos", "municipio__nome_municipio", "municipio__nome_municipio_polo_compras"],
)  # fmt: skip
def test_colunas_de_lugar_e_agregado_sao_permitidas(coluna: str) -> None:
    assert g.colunas_proibidas([coluna]) == []


def test_cnpj_so_com_identifica_estabelecimento() -> None:
    assert g.colunas_proibidas(["cnpj_completo", "cnpj_raiz"]) == ["cnpj_completo", "cnpj_raiz"]
    assert g.colunas_proibidas(["cnpj_completo"], "identifica_estabelecimento") == []
    assert g.colunas_proibidas(["nome"], "identifica_estabelecimento") == ["nome"]


def test_normalizar_sql_torna_portavel() -> None:
    raiz = "/Users/alguem/dados"
    compilado = (
        '\n\nselect * from "warehouse"."main"."dim_porte" as p\n'
        "join read_parquet('/Users/alguem/dados/raw/rfb/empresas/*.parquet') as e on true   \n"
    )
    portavel = g.normalizar_sql(compilado, raiz)
    assert portavel == (
        "select * from main.dim_porte as p\n"
        "join read_parquet('${RAIZ_DADOS}/raw/rfb/empresas/*.parquet') as e on true\n"
    )
    assert not g.caminho_absoluto_no_sql(portavel)
    assert g.caminho_absoluto_no_sql("read_parquet('/home/x/raw/a.parquet')")


def test_normalizar_valores() -> None:
    assert g.normalizar_resultado(
        ["a", "b", "c", "d", "e"], [(Decimal("1000.50"), 1 / 3, dt.date(2026, 9, 12), None, True)]
    ) == {
        "colunas": ["a", "b", "c", "d", "e"],
        "linhas": [[1000.5, 0.333333, "2026-09-12", None, True]],
    }


def test_resultado_mf_normaliza_e_ordena() -> None:
    resultado = g.resultado_mf(
        ["mes", "uf", "qtd", "pct"],
        [
            ["2026-09-01 00:00:00", "SP", "2", ""],
            ["2026-08-01 00:00:00", "ES", "10", "0.3333333333"],
        ],
    )
    assert resultado["linhas"] == [
        ["2026-08-01", "ES", 10, 0.333333],
        ["2026-09-01", "SP", 2, None],
    ]


def test_resultado_sql_semantico_tem_a_forma_do_csv_do_mf() -> None:
    """O SQL do MetricFlow devolve timestamp e texto; o resultado fica igual ao do CSV do `mf query` (RGQ-01)."""
    resultado = g.resultado_sql_semantico(
        ["metric_time__month", "classe_cnae", "qtd", "pct", "sigilo"],
        [
            (dt.datetime(2026, 9, 1), "47415", 2, None, False),
            (dt.datetime(2026, 8, 1), "20711", 10, Decimal("0.33333333"), True),
        ],
    )
    assert resultado["linhas"] == [
        ["2026-08-01", 20711, 10, 0.333333, True],
        ["2026-09-01", 47415, 2, None, False],
    ]
    assert g.resultado_sql_semantico(["metric_time__month"], []) == {"colunas": [], "linhas": []}


def test_comando_mf() -> None:
    entrada = {
        "metricas": ["qtd_ativos", "pct_ativos"],
        "group_by": ["metric_time__month"],
        "where": "{{ Dimension('municipio__sigla_uf') }} = 'ES'",
    }
    assert g.comando_mf(entrada) == (
        "uv run mf query --metrics qtd_ativos,pct_ativos --group-by metric_time__month "
        "--where \"{{ Dimension('municipio__sigla_uf') }} = 'ES'\""
    )
    assert g.comando_mf({"saved_query": "serie"}) == "uv run mf query --saved-query serie"


def _entrada_semantica(**extra) -> dict:
    return {
        "id": "gq_semantica__porte__01",
        "conceito": "porte",
        "camada": "semantica",
        "perguntas": ["a?", "b?"],
        "intencao": "x",
        "armadilhas": ["y"],
        "variacoes": ["z"],
        "resposta_esperada_fixtures": {"colunas": [], "linhas": []},
        **extra,
    }


def test_semantica_exige_saved_query_ou_metricas() -> None:
    assert g.validar_semantica(_entrada_semantica(metricas=["qtd_ativos"]), CONCEITOS) == []
    assert g.validar_semantica(_entrada_semantica(saved_query="s"), CONCEITOS) == []
    assert g.validar_semantica(_entrada_semantica(), CONCEITOS)
    assert g.validar_semantica(_entrada_semantica(saved_query="s", where="x"), CONCEITOS)


def test_catalogo_e_indice_gerados(tmp_path: Path) -> None:
    matriz = _matriz(
        {"porte": {c: "m" for c in g.CAMADAS if c != "core"}, "renda": {c: "m" for c in g.CAMADAS}}
    )
    matriz["camadas"] = [{"id": c, "nome": c, "uso": c} for c in g.CAMADAS]
    matriz["conceitos"] = [{"id": "porte", "nome": "Porte"}, {"id": "renda", "nome": "Renda"}]
    golden = {"gq_core__porte__01": (g.ler_cabecalho(SQL_VALIDO), SQL_VALIDO)}
    compilado = {"gq_core__porte__01": 'select 1 from "warehouse"."main"."dim_porte" order by 1'}
    catalogo = g.gerar_catalogo(matriz, golden, compilado, [], "/x", {})
    (consulta,) = catalogo["golden_queries"]
    assert consulta["sql"] == "select 1 from main.dim_porte order by 1\n"
    assert consulta["arquivo"] == "transform/analyses/golden/gq_core__porte__01.sql"
    assert json.loads(g.serializar(catalogo)) == catalogo
    indice = g.renderizar_indice(catalogo)
    assert "[01](../transform/analyses/golden/gq_core__porte__01.sql)" in indice
    assert "- `porte` × `raw`: m" in indice
    guia = f"# G\n\nantes\n{g.INICIO_BLOCO}\nvelho\n{g.FIM_BLOCO}\ndepois\n"
    assert g.substituir_bloco(guia, indice) == f"# G\n\nantes\n{indice}\ndepois\n"
    # Os dois blocos gerados convivem: os marcadores do esquema não casam com os do índice.
    dois = f"{g.INICIO_ESQUEMA}\nx\n{g.FIM_ESQUEMA}\nmeio\n{g.INICIO_BLOCO}\ny\n{g.FIM_BLOCO}\n"
    assert g.substituir_bloco(dois, "I") == f"{g.INICIO_ESQUEMA}\nx\n{g.FIM_ESQUEMA}\nmeio\nI\n"
    assert g.substituir_bloco(dois, "E", g.INICIO_ESQUEMA, g.FIM_ESQUEMA).startswith("E\nmeio\n")


def test_catalogo_recusa_problemas() -> None:
    matriz = _matriz({})
    matriz["conceitos"] = [{"id": "porte", "nome": "Porte"}]
    golden = {"gq_core__porte__01": (g.ler_cabecalho(SQL_VALIDO), SQL_VALIDO)}
    with pytest.raises(g.CatalogoErro, match="sem golden query e sem motivo"):
        g.gerar_catalogo(matriz, golden, {"gq_core__porte__01": "select 1"}, [], None, {})


def test_golden_queries_do_repositorio_validas() -> None:
    """Os cabeçalhos versionados, `semantica.yml` e a matriz (sem dbt): o CI de integração executa as queries."""
    assert (
        g.problemas_gerais(g.carregar_matriz(), g.carregar_golden(), g.carregar_semantica()) == []
    )


def _esquema_minimo() -> tuple[dict, dict, dict]:
    semantico = {
        "semantic_models": [
            {"name": "dim_porte", "primary_entity": None, "node_relation": {"alias": "dim_porte"},
             "entities": [{"name": "porte", "type": "primary"}],
             "dimensions": [{"name": "rotulo_porte", "type": "categorical", "description": "Rótulo.\n"}]},
            {"name": "fct_resumo_mensal", "primary_entity": "resumo_mensal", "node_relation": {"alias": "fct_resumo_mensal"},
             "entities": [{"name": "porte", "type": "foreign"}, {"name": "cnae", "type": "foreign"}],
             "dimensions": [{"name": "mes", "type": "time", "type_params": {"time_granularity": "month"}}]},
        ],
        "metrics": [
            {"name": "qtd_ativos", "type": "simple", "label": "Ativos", "description": "Ativos no mês.",
             "type_params": {"expr": "qtd_ativos", "metric_aggregation_params": {"semantic_model": "fct_resumo_mensal", "agg": "sum"}},
             "filter": None},
            {"name": "qtd_x", "type": "simple", "label": None, "description": None,
             "type_params": {"expr": "qtd_estabelecimentos", "metric_aggregation_params": {"semantic_model": "fct_resumo_mensal", "agg": "sum"}},
             "filter": {"where_filters": [{"where_sql_template": "{{ Dimension('porte__rotulo_porte') }} = 'MICRO'"}]}},
            {"name": "pct", "type": "ratio", "label": None, "description": "",
             "type_params": {"numerator": {"name": "qtd_ativos"}, "denominator": {"name": "qtd_x"}}, "filter": None},
        ],
    }  # fmt: skip
    manifesto = {
        "nodes": {
            "model.rfb.dim_porte": {"package_name": "rfb", "original_file_path": "models/marts/core/dim_porte.sql",
                                    "alias": "dim_porte", "name": "dim_porte", "description": "Porte.",
                                    "meta": {"grao": "porte (`sk_porte`)"},
                                    "columns": {"rotulo_porte": {"description": "Rótulo\n do porte."}}},
            "model.rfb.dq_resumo": {"package_name": "rfb", "original_file_path": "models/observability/dq_resumo.sql",
                                    "alias": "dq_resumo", "name": "dq_resumo"},
            "test.rfb.algum_teste": {"package_name": "rfb", "original_file_path": "models/marts/core/_core.yml",
                                     "alias": "algum_teste", "name": "algum_teste"},
        }
    }  # fmt: skip
    catalogo = {
        "nodes": {
            "model.rfb.dim_porte": {"columns": {"nome": {"name": "nome", "type": "VARCHAR", "index": 2},
                                                "rotulo_porte": {"name": "rotulo_porte", "type": "VARCHAR", "index": 1}}},
            "model.rfb.dq_resumo": {"columns": {"x": {"name": "x", "type": "INTEGER", "index": 1}}},
            "test.rfb.algum_teste": {"columns": {"x": {"name": "x", "type": "INTEGER", "index": 1}}},
        }
    }  # fmt: skip
    return manifesto, catalogo, semantico


def test_esquema_gera_metricas_dimensoes_e_relacoes() -> None:
    """RGQ-02: métricas com natureza, medida, filtro e entidades; dimensões qualificadas; relações com colunas."""
    esquema = g.gerar_esquema(*_esquema_minimo())
    metricas = {m["nome"]: m for m in esquema["metricas"]}
    assert metricas["qtd_ativos"]["medida"] == "sum(qtd_ativos) em fct_resumo_mensal"
    assert metricas["qtd_ativos"]["natureza"].startswith("fotografia mensal")
    assert metricas["qtd_ativos"]["entidades"] == [
        "porte",
        "resumo_mensal",
    ]  # `cnae` não tem modelo próprio aqui
    assert metricas["qtd_x"]["filtro"] == ["{{ Dimension('porte__rotulo_porte') }} = 'MICRO'"]
    assert metricas["pct"]["medida"] == "qtd_ativos / qtd_x"
    assert [d["nome"] for d in esquema["dimensoes"]] == [
        "porte__rotulo_porte",
        "resumo_mensal__mes",
    ]
    assert esquema["dimensoes"][1]["grao"] == "month"
    (relacao,) = esquema["relacoes"]  # observabilidade e testes ficam fora
    assert relacao["nome"] == "main.dim_porte" and relacao["camada"] == "core"
    assert [(c["nome"], c["proibida_na_saida"]) for c in relacao["colunas"]] == [
        ("rotulo_porte", False),
        ("nome", True),
    ]
    assert relacao["colunas"][0]["descricao"] == "Rótulo do porte."
    indice = g.renderizar_esquema({**esquema, "golden_queries": []})
    assert "**`nome`** varchar" in indice and "`porte__rotulo_porte`" in indice


def test_esquema_recusa_modelo_semantico_sem_natureza() -> None:
    manifesto, catalogo, semantico = _esquema_minimo()
    semantico["metrics"][0]["type_params"]["metric_aggregation_params"]["semantic_model"] = (
        "dim_porte"
    )
    with pytest.raises(g.CatalogoErro, match="sem natureza"):
        g.gerar_esquema(manifesto, catalogo, semantico)


@pytest.mark.parametrize(
    ("sql", "esperado"),
    [
        # M1 da RGQ: CNPJ básico como inteiro, com alias livre.
        ("select max(left(cnpj_completo, 8)::bigint) as maior_raiz from main.fct_estabelecimentos", ["maior_raiz"]),
        # M2 da RGQ: nome de empresário individual com outro alias.
        ("select min(nome) as titular, count(*) as n from main.bh_empresas", ["titular"]),
        # Pela CTE e por `string_agg`.
        ("with a as (select nome as x from main.mart_fornecedores_proximos) select string_agg(x, ', ') as y from a", ["y"]),
        # Contagens, `is null` (o CASE do MetricFlow) e filtro: permitidos.
        ("select count(distinct left(cnpj_completo, 8)) as empresas, count(*) filter (where nome like 'A%') as n "
         "from main.bh_empresas", []),
        ("select sum(case when not cnpj_completo is null then 1 else 0 end) as aberturas from main.fct_estabelecimentos", []),
        # `nome` de relação de lugar (município da Base dos Dados) não é de pessoa.
        ("select nome as nome_municipio from main.stg_bd__municipios order by 1", []),
    ],
)  # fmt: skip
def test_saida_derivada_de_coluna_proibida_e_recusada(sql: str, esperado: list[str]) -> None:
    """RGQ-04: a guarda segue a linhagem da coluna de saída, não só o nome dela."""
    assert [p.split(" ", 1)[0] for p in g.colunas_derivadas_proibidas(sql)] == esperado


def test_cnpj_derivado_passa_com_identifica_estabelecimento() -> None:
    sql = "select cnpj_completo, eh_ativa from main.fct_estabelecimentos"
    assert g.colunas_derivadas_proibidas(sql)
    assert g.colunas_derivadas_proibidas(sql, "identifica_estabelecimento") == []


def test_raiz_e_cnpj_numerico_sao_identificador() -> None:
    assert g.colunas_proibidas(["maior_raiz", "cnpj_raiz", "raiz"]) == [
        "maior_raiz",
        "cnpj_raiz",
        "raiz",
    ]
    assert g.numero_identificador(11222333000181) and g.numero_identificador(52998224725)
    assert not g.numero_identificador(20260912)  # `sk_data` AAAAMMDD
    assert not g.numero_identificador(11111111111)
    assert g.RE_CPF_MASCARADO.search("PINTE BEM ***.***.***-**")


def test_id_citado_em_armadilha_precisa_existir() -> None:
    """RGQ-07 (M8): a armadilha que cita uma golden query inexistente é apontada."""
    cab = g.ler_cabecalho(SQL_VALIDO)
    assert g.ids_citados_inexistentes([cab], ["gq_core__porte__01"]) == []
    cab["armadilhas"] = ["Veja gq_core__porte__09."]
    assert g.ids_citados_inexistentes([cab], ["gq_core__porte__01"]) == [
        "gq_core__porte__01: cita gq_core__porte__09, que não existe"
    ]


def test_guia_cita_so_ids_que_existem() -> None:
    texto = "Parta de `gq_core__porte__01` ou de `gq_core__ativos__01`."
    assert g.problemas_do_guia(texto, ["gq_core__porte__01"]) == [
        f"{g.GUIA.name}: cita gq_core__ativos__01, que não existe"
    ]


def test_exemplos_sql_do_guia_precisam_de_marca() -> None:
    texto = "x\n\n  ```sql\n  -- exemplo: um\n  select 1\n  ```\n\n```sql\n-- exemplo: dois\nselect 2\n```\n"
    assert g.exemplos_sql_do_guia(texto) == {
        "um": "-- exemplo: um\nselect 1",
        "dois": "-- exemplo: dois\nselect 2",
    }
    with pytest.raises(g.CatalogoErro, match="sem `-- exemplo"):
        g.exemplos_sql_do_guia("```sql\nselect 1\n```\n")
    with pytest.raises(g.CatalogoErro, match="repetido"):
        g.exemplos_sql_do_guia(
            "```sql\n-- exemplo: a\nselect 1\n```\n```sql\n-- exemplo: a\nselect 2\n```\n"
        )
