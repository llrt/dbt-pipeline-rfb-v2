"""ADR-0018: a camada semântica (MetricFlow) é válida e responde igual ao SQL direto sobre o gold.

Roda depois do `dbt build` do `make ci` (gold com 2026-08 e 2026-09 em `RAIZ_DADOS`). Cada consulta
usa o CLI `mf` (pacote `dbt-metricflow`) dentro de `transform/`, como um usuário faria.
"""

from __future__ import annotations

import csv
import os
import subprocess
from pathlib import Path

import duckdb
import pytest

from rfb_pipeline.caminhos import CAMADA_SEMANTICA, CONCEITOS

TRANSFORM = Path(__file__).resolve().parents[2] / "transform"
RAIZ = Path(os.environ.get("RAIZ_DADOS", TRANSFORM.parent / "dados"))
GOLD = RAIZ / "gold"

pytestmark = pytest.mark.skipif(
    not (GOLD / "fct_resumo_mensal").is_dir(), reason="rode via make ci (gera o gold)"
)


def _mf(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ | {"RAIZ_DADOS": str(RAIZ), "DBT_PROFILES_DIR": str(TRANSFORM)}
    return subprocess.run(
        ["uv", "run", "mf", *args], cwd=TRANSFORM, env=env, capture_output=True, text=True,
        check=False,
    )  # fmt: skip


def _consulta(tmp_path: Path, *args: str) -> list[dict[str, str]]:
    saida = tmp_path / "resultado.csv"
    saida.unlink(missing_ok=True)
    resultado = _mf(tmp_path, "query", "--quiet", "--csv", str(saida), *args)
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    if not saida.exists():  # o `mf` não grava o CSV quando a consulta volta vazia
        return []
    with saida.open(encoding="utf-8") as arquivo:
        return list(csv.DictReader(arquivo))


def _sql(consulta: str) -> list[tuple]:
    return duckdb.sql(consulta.format(gold=GOLD)).fetchall()


def _num(valor: str) -> float | None:
    return float(valor) if valor not in ("", None) else None


RESUMO = "read_parquet('{gold}/fct_resumo_mensal/*/*.parquet', hive_partitioning = true)"


def test_configuracao_valida_contra_o_warehouse(tmp_path: Path) -> None:
    resultado = _mf(tmp_path, "validate-configs")
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert "ERRORS: 0, FUTURE_ERRORS: 0, WARNINGS: 0" in resultado.stdout


# Cada métrica do resumo e o SQL equivalente nas linhas de um mês (contagens, numeradores, ratios).
MEI = "sum(qtd_ativos) filter (where opcao_mei)"
METRICAS_DO_RESUMO = {
    "qtd_estabelecimentos": "sum(qtd_estabelecimentos)",
    "qtd_ativos": "sum(qtd_ativos)",
    "qtd_ativos_mei": MEI,
    "qtd_matrizes": "sum(qtd_matrizes)",
    "capital_social_total": "sum(soma_capital_social_matrizes)",
    "soma_idade_anos_ativos": "sum(soma_idade_anos)",
    "pct_ativos": "sum(qtd_ativos) / nullif(sum(qtd_estabelecimentos), 0)",
    "idade_media_anos": "sum(soma_idade_anos) / nullif(sum(qtd_ativos), 0)",
    "capital_social_medio": "sum(soma_capital_social_matrizes) / nullif(sum(qtd_matrizes), 0)",
    "pct_mei_entre_ativos": f"{MEI} / nullif(sum(qtd_ativos), 0)",
}
CONTAGENS_DO_RESUMO = list(METRICAS_DO_RESUMO)[:6]


def _iguais(obtido: str, esperado: object) -> bool:
    if esperado is None:
        return _num(obtido) is None
    return _num(obtido) == pytest.approx(float(esperado))


@pytest.mark.parametrize("grao", ["metric_time__month", "metric_time__year", None])
def test_metricas_do_resumo_batem_com_o_sql(tmp_path: Path, grao: str | None) -> None:
    """Todas as métricas do resumo, no mês, no ano e sem tempo. No ano e sem tempo vale a fotografia
    do último mês (`non_additive_dimension`), inclusive nos numeradores dos ratios."""
    if grao == "metric_time__month":
        chave, filtro = "mes_referencia", "true"
    elif grao == "metric_time__year":
        chave = "left(mes_referencia, 4)"
        filtro = f"mes_referencia in (select max(mes_referencia) from {RESUMO} group by {chave})"
    else:
        chave, filtro = "''", f"mes_referencia = (select max(mes_referencia) from {RESUMO})"
    colunas = ", ".join(METRICAS_DO_RESUMO.values())
    esperado = {
        linha[0]: linha[1:]
        for linha in _sql(f"select {chave}, {colunas} from {RESUMO} where {filtro} group by 1")
    }
    agrupamento = ["--group-by", grao] if grao else []
    linhas = _consulta(tmp_path, "--metrics", ",".join(METRICAS_DO_RESUMO), *agrupamento)
    tamanho = {"metric_time__month": 7, "metric_time__year": 4, None: 0}[grao]
    obtido = {(r[grao][:tamanho] if grao else ""): r for r in linhas}
    assert obtido.keys() == esperado.keys()
    diferencas = [
        (periodo, metrica, obtido[periodo][metrica], valor)
        for periodo, valores in esperado.items()
        for metrica, valor in zip(METRICAS_DO_RESUMO, valores, strict=True)
        if not _iguais(obtido[periodo][metrica], valor)
    ]
    assert not diferencas, f"(período, métrica, mf, SQL): {diferencas}"


def test_fixture_discrimina_a_fotografia_em_todas_as_contagens() -> None:
    """Pré-condição do teste acima: somar os meses daria outro número em cada contagem do resumo."""
    colunas = ", ".join(METRICAS_DO_RESUMO[m] for m in CONTAGENS_DO_RESUMO)
    ultimo_mes = f"(select max(mes_referencia) from {RESUMO})"
    ((*ultimo,),) = _sql(f"select {colunas} from {RESUMO} where mes_referencia = {ultimo_mes}")
    ((*soma,),) = _sql(f"select {colunas} from {RESUMO}")
    iguais = [m for m, u, s in zip(CONTAGENS_DO_RESUMO, ultimo, soma, strict=True) if u == s]
    assert not iguais, f"contagens em que o último mês é igual à soma dos meses: {iguais}"


def test_fotografia_mensal_nao_soma_meses(tmp_path: Path) -> None:
    """`non_additive_dimension`: no ano (ou sem tempo) vale o último mês, não a soma dos meses."""
    ((ultimo_ativos, ultimo_estab),) = _sql(
        f"""select sum(qtd_ativos), sum(qtd_estabelecimentos) from {RESUMO}
            where mes_referencia = (select max(mes_referencia) from {RESUMO})"""
    )
    ((soma_ativos,),) = _sql(f"select sum(qtd_ativos) from {RESUMO}")
    assert soma_ativos > ultimo_ativos  # a fixture tem 2 meses: somar daria outro número
    por_ano = _consulta(
        tmp_path, "--metrics", "qtd_ativos,qtd_estabelecimentos", "--group-by", "metric_time__year"
    )
    assert [(int(r["qtd_ativos"]), int(r["qtd_estabelecimentos"])) for r in por_ano] == [
        (ultimo_ativos, ultimo_estab)
    ]
    sem_tempo = _consulta(tmp_path, "--metrics", "qtd_ativos")
    assert [int(r["qtd_ativos"]) for r in sem_tempo] == [ultimo_ativos]


SUSPENSA_PB = (
    "{{ Dimension('municipio__sigla_uf') }} = 'PB'"
    " and {{ Dimension('situacao_cadastral__rotulo_situacao_cadastral') }} = 'SUSPENSA'"
)


def test_fotografia_com_filtro_vale_o_ultimo_mes_em_que_o_recorte_tem_linhas(
    tmp_path: Path,
) -> None:
    """RSEM-01, limitação do MetricFlow documentada na A6 e na B3: o `MAX(mes)` da fotografia é
    calculado depois do `--where`. Quando o filtro esvazia o último mês, o ano (e a consulta sem
    tempo) devolve a fotografia do último mês em que o recorte tem linhas, não zero. Linha R da
    fixture: a filial de Água Branca/PB estava SUSPENSA em 2026-08 e está BAIXADA em 2026-09."""
    no_gold = _sql(
        f"""select r.mes_referencia, sum(r.qtd_estabelecimentos) from {RESUMO} r
            join '{{gold}}/dim_municipio.parquet' m using (sk_municipio)
            join '{{gold}}/dim_situacao_cadastral.parquet' s using (sk_situacao_cadastral)
            where m.sigla_uf = 'PB' and s.rotulo_situacao_cadastral = 'SUSPENSA' group by 1"""
    )
    ((ultimo_mes,),) = _sql(f"select max(mes_referencia) from {RESUMO}")
    assert no_gold == [("2026-08", 1)] and ultimo_mes == "2026-09"  # só no penúltimo mês

    def consulta(*args: str) -> list[tuple[str, int]]:
        linhas = _consulta(tmp_path, "--metrics", "qtd_estabelecimentos", *args)
        return [
            (
                r.get("metric_time__month", r.get("metric_time__year", ""))[:7],
                int(r["qtd_estabelecimentos"]),
            )
            for r in linhas
        ]

    assert consulta("--group-by", "metric_time__month", "--where", SUSPENSA_PB) == [("2026-08", 1)]
    # a fotografia "do ano" é a de 2026-08, e "quantas há?" responde 1, não 0
    assert consulta("--group-by", "metric_time__year", "--where", SUSPENSA_PB) == [("2026-01", 1)]
    assert consulta("--where", SUSPENSA_PB) == [("", 1)]
    # caminhos recomendados: filtrar o mês (vazio = nenhuma) ou agrupar pela situação, sem filtrá-la
    no_mes = (
        f"{SUSPENSA_PB} and {{{{ TimeDimension('metric_time', 'month') }}}} = '{ultimo_mes}-01'"
    )
    assert consulta("--group-by", "metric_time__month", "--where", no_mes) == []
    por_situacao = _consulta(
        tmp_path, "--metrics", "qtd_estabelecimentos,qtd_ativos",
        "--group-by", "metric_time__year,situacao_cadastral__rotulo_situacao_cadastral",
        "--where", "{{ Dimension('municipio__sigla_uf') }} = 'PB'",
    )  # fmt: skip
    assert [
        (
            r["situacao_cadastral__rotulo_situacao_cadastral"],
            _num(r["qtd_estabelecimentos"]),
            _num(r["qtd_ativos"]),
        )
        for r in por_situacao
    ] == [("BAIXADA", 2, 0)]


def test_variacao_mensal_usa_o_mes_anterior(tmp_path: Path) -> None:
    linhas = _consulta(
        tmp_path, "--metrics",
        "qtd_ativos,qtd_ativos_mes_anterior,variacao_mensal_ativos,variacao_mensal_ativos_pct",
        "--group-by", "metric_time__month", "--order", "metric_time__month",
    )  # fmt: skip
    anterior, atual = (int(r["qtd_ativos"]) for r in linhas)
    assert anterior != atual  # a fixture discrimina: a variação não é zero
    assert _num(linhas[0]["qtd_ativos_mes_anterior"]) is None  # 1º mês da série: sem anterior
    assert int(linhas[1]["qtd_ativos_mes_anterior"]) == anterior
    assert int(linhas[1]["variacao_mensal_ativos"]) == atual - anterior
    assert _num(linhas[0]["variacao_mensal_ativos_pct"]) is None
    assert _num(linhas[1]["variacao_mensal_ativos_pct"]) == pytest.approx(
        (atual - anterior) / anterior
    )


def test_estudo_de_caso_fundao(tmp_path: Path) -> None:
    """Saved query da pergunta-guia; o número de 2026-09 é o do notebook 4 (MICRO, idade 3,9)."""
    linhas = _consulta(tmp_path, "--saved-query", "estudo_caso_fundao_tintas")
    obtido = {
        (r["metric_time__month"][:7], r["porte__rotulo_porte"]): (
            int(r["qtd_estabelecimentos"]),
            int(r["qtd_ativos"]),
            _num(r["idade_media_anos"]),
        )
        for r in linhas
    }
    esperado = {
        (mes, porte): (estab, ativos, idade)
        for mes, porte, estab, ativos, idade in _sql(
            f"""select r.mes_referencia, p.rotulo_porte, sum(r.qtd_estabelecimentos),
                       sum(r.qtd_ativos), sum(r.soma_idade_anos) / nullif(sum(r.qtd_ativos), 0)
                from {RESUMO} r
                join '{{gold}}/dim_municipio.parquet' m using (sk_municipio)
                join '{{gold}}/dim_cnae.parquet' c using (sk_cnae)
                join '{{gold}}/dim_porte.parquet' p using (sk_porte)
                where m.nome_municipio = 'Fundão' and m.sigla_uf = 'ES'
                  and c.codigo_subclasse = '4741500'
                group by 1, 2"""
        )
    }
    assert obtido.keys() == esperado.keys()
    for chave, (estab, ativos, idade) in esperado.items():
        assert obtido[chave][:2] == (estab, ativos)
        assert obtido[chave][2] == pytest.approx(idade)
    assert obtido[("2026-09", "MICRO")] == (2, 1, pytest.approx(3.9))


DINAMICA = "'{gold}/mart_dinamica_mercado.parquet'"
DATA_VALIDA = "case when {sk} > 0 then {sk} // 10000 end"


def _dinamica(linhas: list[dict[str, str]], *chave: str) -> dict[tuple[str, ...], tuple]:
    """Linhas do `mf` por chave. Lado sem evento no período vem nulo e vale 0; o saldo, não."""
    return {
        tuple(r[c][:4] if c.startswith("metric_time") else r[c] for c in chave): (
            int(_num(r["aberturas"]) or 0),
            int(_num(r["encerramentos"]) or 0),
            _num(r["saldo_aberturas_encerramentos"]),
        )
        for r in linhas
    }


def _pre_condicoes_da_dinamica() -> None:
    """Casos da fixture sem os quais uma regra errada passaria batido nos testes da dinâmica."""
    fato = "'{gold}/fct_estabelecimentos.parquet'"
    inicio = DATA_VALIDA.format(sk="sk_data_inicio_atividade")
    situacao = DATA_VALIDA.format(sk="sk_data_situacao")
    ((em_outro_ano, ativos_com_situacao, inativos_sem_situacao, sem_inicio),) = _sql(
        f"""select count(*) filter (where not eh_ativa and {inicio} <> {situacao}),
                   count(*) filter (where eh_ativa and {situacao} is not null),
                   count(*) filter (where not eh_ativa and sk_data_situacao <= 0),
                   count(*) filter (where sk_data_inicio_atividade <= 0)
            from {fato}"""
    )
    assert em_outro_ano > 0, "fixture sem inativo com ano de início diferente do da situação"
    assert ativos_com_situacao > 0, "fixture sem ativo com data da situação válida"
    # Linha Q da fixture: sem o filtro de data válida, as chaves -1/-2 viram um ano nulo no `mf`.
    assert inativos_sem_situacao > 0, "fixture sem inativo com data da situação -1/-2"
    assert sem_inicio > 0, "fixture sem estabelecimento com data de início -1/-2"


def test_dinamica_por_ano_bate_com_o_mart(tmp_path: Path) -> None:
    """Mesma regra de `mart_dinamica_mercado`: abertura pela data de início, encerramento = não
    ativo pela data da situação, datas -1/-2 sem evento; saldo = aberturas − encerramentos."""
    _pre_condicoes_da_dinamica()
    esperado = {
        (str(ano),): (abe, enc, sal)
        for ano, abe, enc, sal in _sql(
            f"select ano, sum(aberturas), sum(encerramentos), sum(saldo) from {DINAMICA} group by 1"
        )
    }
    assert any(0 in valores[:2] for valores in esperado.values()), "sem ano só de um lado"
    linhas = _consulta(
        tmp_path, "--metrics", "aberturas,encerramentos,saldo_aberturas_encerramentos",
        "--group-by", "metric_time__year",
    )  # fmt: skip
    assert _dinamica(linhas, "metric_time__year") == esperado


def test_dinamica_por_ano_e_secao_bate_com_o_mart(tmp_path: Path) -> None:
    _pre_condicoes_da_dinamica()
    linhas = _consulta(tmp_path, "--saved-query", "dinamica_anual_por_secao_cnae")
    esperado = {
        (str(ano), secao): (abe, enc, sal)
        for ano, secao, abe, enc, sal in _sql(
            f"""select d.ano, c.descricao_secao,
                       sum(d.aberturas), sum(d.encerramentos), sum(d.saldo)
                from {DINAMICA} d join '{{gold}}/dim_cnae.parquet' c using (sk_cnae)
                group by 1, 2"""
        )
    }
    assert len(esperado) > 1
    assert _dinamica(linhas, "metric_time__year", "cnae__descricao_secao") == esperado


def test_baixas_sao_so_as_baixadas_com_data_valida(tmp_path: Path) -> None:
    """RSEM-04: `baixas` = BAIXADA pela data da situação válida; encerramento inclui as inaptas."""
    fato = """'{gold}/fct_estabelecimentos.parquet' f
              join '{gold}/dim_situacao_cadastral.parquet' s using (sk_situacao_cadastral)"""
    situacao = DATA_VALIDA.format(sk="sk_data_situacao")
    baixada = "s.rotulo_situacao_cadastral = 'BAIXADA'"
    esperado = {
        str(ano): total
        for ano, total in _sql(
            f"""select {situacao}, count(*) from {fato}
                where {baixada} and {situacao} is not null group by 1"""
        )
    }
    ((inativas_nao_baixadas, baixadas_sem_data),) = _sql(
        f"""select count(*) filter (where not eh_ativa and not {baixada}
                                      and {situacao} is not null),
                   count(*) filter (where {baixada} and {situacao} is null)
            from {fato}"""
    )
    assert inativas_nao_baixadas > 0, "fixture sem encerramento que não é baixa"
    assert baixadas_sem_data > 0, "fixture sem baixada com data da situação -1/-2"
    linhas = _consulta(
        tmp_path, "--metrics", "baixas,encerramentos", "--group-by", "metric_time__year"
    )
    obtido = {r["metric_time__year"][:4]: int(_num(r["baixas"]) or 0) for r in linhas}
    assert {ano: total for ano, total in obtido.items() if total} == esperado
    assert sum(obtido.values()) < sum(int(_num(r["encerramentos"]) or 0) for r in linhas)


COORTE = "'{gold}/mart_sobrevivencia_coorte.parquet'"
METRICAS_DA_COORTE = {
    f"{metrica}_{n}a": sql.format(n=n)
    for n in (1, 3, 5)
    for metrica, sql in (
        ("elegiveis", "sum(elegiveis_{n}a)"),
        ("sobreviventes", "sum(sobreviventes_{n}a)"),
        ("taxa_sobrevivencia", "sum(sobreviventes_{n}a) / nullif(sum(elegiveis_{n}a), 0)"),
    )
}


def test_sobrevivencia_soma_os_estratos_antes_de_dividir(tmp_path: Path) -> None:
    """Elegíveis, sobreviventes e taxas a 1, 3 e 5 anos por coorte, iguais ao mart somado."""
    colunas = ", ".join(METRICAS_DA_COORTE.values())
    esperado = {
        str(linha[0]): linha[1:]
        for linha in _sql(f"select ano_coorte, {colunas} from {COORTE} group by 1")
    }
    # pré-condição: horizontes diferentes dão números diferentes (taxa de 1 ano ≠ de 3 anos)
    ((distintos,),) = _sql(
        f"""select count(*) from (select ano_coorte from {COORTE} group by 1
            having sum(sobreviventes_1a) <> sum(sobreviventes_3a) and sum(elegiveis_3a) > 0)"""
    )
    assert distintos > 0
    linhas = _consulta(
        tmp_path, "--metrics", ",".join(METRICAS_DA_COORTE), "--group-by", "metric_time__year"
    )
    obtido = {r["metric_time__year"][:4]: r for r in linhas}
    assert obtido.keys() == esperado.keys()
    diferencas = [
        (ano, metrica, obtido[ano][metrica], valor)
        for ano, valores in esperado.items()
        for metrica, valor in zip(METRICAS_DA_COORTE, valores, strict=True)
        if not _iguais(obtido[ano][metrica], valor)
    ]
    assert not diferencas, f"(coorte, métrica, mf, SQL): {diferencas}"


def test_saved_query_sobrevivencia_por_coorte_e_porte(tmp_path: Path) -> None:
    linhas = _consulta(tmp_path, "--saved-query", "sobrevivencia_por_coorte_e_porte")
    taxas = [f"taxa_sobrevivencia_{n}a" for n in (1, 3, 5)]
    esperado = {
        (str(linha[0]), linha[1]): linha[2:]
        for linha in _sql(
            f"""select c.ano_coorte, p.rotulo_porte,
                       {", ".join(METRICAS_DA_COORTE[x] for x in taxas)}
                from {COORTE} c join '{{gold}}/dim_porte.parquet' p using (sk_porte)
                group by 1, 2"""
        )
    }
    obtido = {(r["metric_time__year"][:4], r["porte__rotulo_porte"]): r for r in linhas}
    assert obtido.keys() == esperado.keys()
    for chave, valores in esperado.items():
        for taxa, valor in zip(taxas, valores, strict=True):
            assert _iguais(obtido[chave][taxa], valor), (chave, taxa)


def test_saved_query_serie_mensal_ativos_por_uf(tmp_path: Path) -> None:
    linhas = _consulta(tmp_path, "--saved-query", "serie_mensal_ativos_por_uf")
    metricas = ["qtd_ativos", "pct_ativos", "idade_media_anos"]
    esperado = {
        (mes, uf): valores
        for mes, uf, *valores in _sql(
            f"""select r.mes_referencia, m.sigla_uf,
                       {", ".join(METRICAS_DO_RESUMO[x] for x in metricas)}
                from {RESUMO} r join '{{gold}}/dim_municipio.parquet' m using (sk_municipio)
                group by 1, 2"""
        )
    }
    obtido = {(r["metric_time__month"][:7], r["municipio__sigla_uf"]): r for r in linhas}
    assert len(esperado) > 2 and obtido.keys() == esperado.keys()
    for chave, valores in esperado.items():
        for metrica, valor in zip(metricas, valores, strict=True):
            assert _iguais(obtido[chave][metrica], valor), (chave, metrica)


DOCS = (CONCEITOS, CAMADA_SEMANTICA)


def test_numeros_citados_na_doc_batem_com_as_fixtures(tmp_path: Path) -> None:
    """RSEM-10: os números na prosa de `conceitos.md` e `camada-semantica.md` vêm das fixtures. Se
    a fixture mudar, este teste aponta a frase a recalibrar; os outros exemplos remetem à saída."""
    doc = " ".join(" ".join(d.read_text(encoding="utf-8") for d in DOCS).split())
    por_mes = {
        r["metric_time__month"][:7]: {k: int(_num(v)) for k, v in r.items() if k.startswith("qtd")}
        for r in _consulta(
            tmp_path,
            "--metrics",
            "qtd_ativos,qtd_estabelecimentos,qtd_matrizes",
            "--group-by",
            "metric_time__month",
        )  # fmt: skip
    }
    agosto, setembro = por_mes["2026-08"]["qtd_ativos"], por_mes["2026-09"]["qtd_ativos"]
    soma = agosto + setembro
    (linha_pb,) = _consulta(
        tmp_path, "--metrics", "qtd_estabelecimentos", "--group-by", "metric_time__year",
        "--where", SUSPENSA_PB,
    )  # fmt: skip
    suspensas_pb = linha_pb["qtd_estabelecimentos"]
    fundao = {
        (r["metric_time__month"][:10], r["porte__rotulo_porte"]): r
        for r in _consulta(tmp_path, "--saved-query", "estudo_caso_fundao_tintas")
    }[("2026-09-01", "MICRO")]
    idade = f"{float(fundao['idade_media_anos']):.1f}"
    citacoes = [
        (
            f"são {por_mes['2026-09']['qtd_estabelecimentos']} estabelecimentos e "
            f"{por_mes['2026-09']['qtd_matrizes']} matrizes"
        ),
        f"somar 2026-08 ({agosto}) e 2026-09 ({setembro}) daria {soma} ativos",
        f"A segunda consulta devolve {setembro} para 2026 (o valor de 2026-09), não {soma}.",
        f"`qtd_ativos` por ano dá {setembro} (o valor de 2026-09), não {soma} (08 + 09)",
        f"A consulta devolve {suspensas_pb} para 2026 (a fotografia de 2026-08)",
        f"2026-09-01 MICRO {fundao['qtd_estabelecimentos']} {fundao['qtd_ativos']} {idade}",
        f"({fundao['qtd_ativos']} loja ativa, MICRO, {idade.replace('.', ',')} anos)",
    ]
    faltando = [citacao for citacao in citacoes if citacao not in doc]
    assert not faltando, "frases da doc com número diferente das fixtures:\n" + "\n".join(faltando)
