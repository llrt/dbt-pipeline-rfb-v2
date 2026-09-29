"""`bh_empresas` no Parquet de `gold/` contra o cenário de fixtures da spec (Original AC 2–7).

Lê `RAIZ_DADOS` do ambiente — exportado por `make ci`, que roda `dbt build` antes do pytest.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import duckdb
import pytest

pytestmark = pytest.mark.skipif(
    "RAIZ_DADOS" not in os.environ, reason="rode via make ci (exporta RAIZ_DADOS)"
)

COLUNAS = [
    "cnpj_raiz",
    "cnpj_completo",
    "nome",
    "natureza_juridica",
    "porte",
    "cnae_principal",
    "desc_cnae_principal",
    "grupo_cnae_principal",
    "cnaes_secundarios",
    "municipio",
    "microrregiao_municipio",
    "mesorregiao_municipio",
    "uf",
    "situacao",
    "idade_atual",
]


@pytest.fixture(scope="module")
def linhas() -> dict[str, dict[str, object]]:
    parquet = Path(os.environ["RAIZ_DADOS"]) / "gold" / "bh_empresas.parquet"
    assert parquet.is_file(), f"{parquet} não existe; rode `make ci`"
    with duckdb.connect() as con:
        relacao = con.sql(f"select * from read_parquet('{parquet}')")
        assert relacao.columns == COLUNAS
        registros = relacao.fetchall()
    por_cnpj = {r[1]: dict(zip(COLUNAS, r, strict=True)) for r in registros}
    assert len(por_cnpj) == len(registros), "cnpj_completo repetido em bh_empresas"
    return por_cnpj


def test_doze_linhas_sem_k_l_m(linhas: dict[str, dict[str, object]]) -> None:
    assert len(linhas) == 12
    raizes = {linha["cnpj_raiz"] for linha in linhas.values()}
    assert raizes.isdisjoint({"13131313", "14141414", "15151515"})


def test_linha_a(linhas: dict[str, dict[str, object]]) -> None:
    a = linhas["11111111000191"]
    assert a["cnpj_raiz"] == "11111111"
    assert a["nome"] == "TINTAS FUNDÃO"
    assert a["porte"] == "MICRO"
    assert a["situacao"] == "ATIVA"
    assert a["idade_atual"] == 3.9
    assert a["municipio"] == "FUNDÃO"
    assert a["microrregiao_municipio"] == "LINHARES"
    assert a["mesorregiao_municipio"] == "LITORAL NORTE ESPÍRITO-SANTENSE"
    assert a["uf"] == "ES"
    assert a["cnae_principal"] == "4741500"


def test_linha_e(linhas: dict[str, dict[str, object]]) -> None:
    e = linhas["55555555000191"]
    assert e["nome"] == "TINTAS CAPIXABA"
    assert e["porte"] is None
    assert e["situacao"] == "INATIVA"
    assert e["idade_atual"] is None


def test_cnae_com_zero_a_esquerda_linha_n(linhas: dict[str, dict[str, object]]) -> None:
    assert linhas["16161616000184"]["cnae_principal"] == "0111301"


RESULTADOS_DBT = Path(__file__).resolve().parents[2] / "transform" / "target" / "run_results.json"


def _status_dos_testes() -> dict[str, tuple[str, int | None]]:
    """`nome do teste -> (status, failures)` do último `dbt build` (o do `make ci`)."""
    assert RESULTADOS_DBT.is_file(), f"{RESULTADOS_DBT} não existe; rode `make ci`"
    resultados = json.loads(RESULTADOS_DBT.read_text(encoding="utf-8"))["results"]
    return {
        r["unique_id"].split(".")[2]: (r["status"], r["failures"])
        for r in resultados
        if r["unique_id"].startswith("test.rfb.")
    }


def _falhas_armazenadas(teste: str) -> list[tuple[object, ...]]:
    """Linhas gravadas por `store_failures` de um teste singular, ordenadas."""
    banco = Path(os.environ["RAIZ_DADOS"]) / "warehouse.duckdb"
    with duckdb.connect(str(banco), read_only=True) as con:
        return sorted(con.sql(f"select * from main_dbt_test__audit.{teste}").fetchall())


def test_linha_g_razao_social_com_espaco_a_esquerda(linhas: dict[str, dict[str, object]]) -> None:
    """R2-01: o raw guarda o espaço; `bh_empresas.nome` sai com trim e a paridade passa."""
    raw = Path(os.environ["RAIZ_DADOS"]) / "raw" / "rfb" / "empresas"
    with duckdb.connect() as con:
        razao = con.sql(
            f"select razao_social from read_parquet('{raw}/*/*.parquet') "
            "where cnpj_raiz = '77777777' and _mes_referencia = '2026-09'"
        ).fetchone()
    assert razao == (" ATACADO VITORIA TINTAS",)
    (g,) = [linha for linha in linhas.values() if linha["cnpj_raiz"] == "77777777"]
    assert g["nome"] == "ATACADO VITORIA TINTAS"
    assert _status_dos_testes()["paridade_bh_empresas"] == ("pass", 0)


def test_warn_de_trim_acusa_exatamente_g(linhas: dict[str, dict[str, object]]) -> None:
    (cnpj_g,) = [c for c, linha in linhas.items() if linha["cnpj_raiz"] == "77777777"]
    assert _status_dos_testes()["bh_empresas_nome_alterado_por_trim"] == ("warn", 1)
    assert _falhas_armazenadas("bh_empresas_nome_alterado_por_trim") == [
        (cnpj_g, " ATACADO VITORIA TINTAS", "ATACADO VITORIA TINTAS")
    ]


def test_idade_fora_de_faixa_avisa_e_so_falha_acima_de_100() -> None:
    """Original AC 12 (emenda R2-02): 1..100 linhas fora de [0, 200] -> WARN; > 100 -> ERROR."""
    manifesto = json.loads((RESULTADOS_DBT.parent / "manifest.json").read_text(encoding="utf-8"))
    (config,) = [
        no["config"]
        for no in manifesto["nodes"].values()
        if no["resource_type"] == "test"
        and no.get("attached_node") == "model.rfb.bh_empresas"
        and no.get("column_name") == "idade_atual"
    ]
    assert (config["severity"].lower(), config["warn_if"], config["error_if"]) == (
        "error",
        "!=0",
        ">100",
    )
    status = _status_dos_testes()
    (inicio_absurdo,) = [n for n in status if n.startswith("dbt_utils_accepted_range_stg_rfb")]
    assert status[inicio_absurdo] == ("pass", 0)


def test_descartes_do_inner_join_sao_exatamente_k_l_m() -> None:
    """Original AC 11 (R2-05): 3 descartes — K e M sem município BD, L sem CNAE BD."""
    assert _status_dos_testes()["bh_empresas_descartes_inner_join"] == ("warn", 3)
    descartes = {
        cnpj[:8]: motivos
        for cnpj, *motivos in _falhas_armazenadas("bh_empresas_descartes_inner_join")
    }
    # (sem_empresa, sem_natureza, sem_cnae_bd, sem_municipio_bd)
    assert descartes == {
        "13131313": [False, False, False, True],
        "14141414": [False, False, True, False],
        "15151515": [False, False, False, True],
    }
