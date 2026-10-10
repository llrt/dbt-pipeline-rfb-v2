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
    resultado = _mf(tmp_path, "query", "--quiet", "--csv", str(saida), *args)
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
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


def test_metricas_mensais_batem_com_o_resumo(tmp_path: Path) -> None:
    metricas = "qtd_estabelecimentos,qtd_ativos,idade_media_anos,capital_social_medio"
    linhas = _consulta(
        tmp_path, "--metrics", metricas, "--group-by", "metric_time__month",
        "--order", "metric_time__month",
    )  # fmt: skip
    esperado = _sql(
        f"""select mes_referencia, sum(qtd_estabelecimentos), sum(qtd_ativos),
                   sum(soma_idade_anos) / nullif(sum(qtd_ativos), 0),
                   sum(soma_capital_social_matrizes) / nullif(sum(qtd_matrizes), 0)
            from {RESUMO} group by 1 order by 1"""
    )
    assert len(linhas) == len(esperado) == 2
    for linha, (mes, estab, ativos, idade, capital) in zip(linhas, esperado, strict=True):
        assert linha["metric_time__month"].startswith(mes)
        assert int(linha["qtd_estabelecimentos"]) == estab
        assert int(linha["qtd_ativos"]) == ativos
        assert _num(linha["idade_media_anos"]) == pytest.approx(idade)
        assert _num(linha["capital_social_medio"]) == pytest.approx(float(capital))


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


def test_variacao_mensal_usa_o_mes_anterior(tmp_path: Path) -> None:
    linhas = _consulta(
        tmp_path, "--metrics", "qtd_ativos,qtd_ativos_mes_anterior,variacao_mensal_ativos",
        "--group-by", "metric_time__month", "--order", "metric_time__month",
    )  # fmt: skip
    anterior, atual = (int(r["qtd_ativos"]) for r in linhas)
    assert _num(linhas[0]["qtd_ativos_mes_anterior"]) is None  # 1º mês da série: sem anterior
    assert int(linhas[1]["qtd_ativos_mes_anterior"]) == anterior
    assert int(linhas[1]["variacao_mensal_ativos"]) == atual - anterior


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


def test_aberturas_e_encerramentos_cobrem_a_fato(tmp_path: Path) -> None:
    linhas = _consulta(tmp_path, "--metrics", "aberturas,encerramentos")
    ((total, baixadas),) = _sql(
        """select count(*), count(*) filter (where s.rotulo_situacao_cadastral = 'BAIXADA')
           from '{gold}/fct_estabelecimentos.parquet' f
           join '{gold}/dim_situacao_cadastral.parquet' s using (sk_situacao_cadastral)"""
    )
    assert [(int(r["aberturas"]), int(r["encerramentos"])) for r in linhas] == [(total, baixadas)]
    assert baixadas > 0


def test_sobrevivencia_soma_os_estratos_antes_de_dividir(tmp_path: Path) -> None:
    linhas = _consulta(
        tmp_path, "--metrics", "taxa_sobrevivencia_3a", "--group-by", "metric_time__year"
    )
    obtido = {r["metric_time__year"][:4]: _num(r["taxa_sobrevivencia_3a"]) for r in linhas}
    esperado = {
        str(ano): taxa
        for ano, taxa in _sql(
            """select ano_coorte, sum(sobreviventes_3a) / nullif(sum(elegiveis_3a), 0)
               from '{gold}/mart_sobrevivencia_coorte.parquet' group by 1"""
        )
    }
    assert obtido.keys() == esperado.keys()
    for ano, taxa in esperado.items():
        assert obtido[ano] == (pytest.approx(taxa) if taxa is not None else None)
