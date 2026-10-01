"""Modelo estrela (`gold/`) contra o cenário de fixtures da spec (CORE-01, BI-01).

Lê `RAIZ_DADOS` do ambiente — exportado por `make ci`, que roda `dbt build` antes do pytest.
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pytest

pytestmark = pytest.mark.skipif(
    "RAIZ_DADOS" not in os.environ, reason="rode via make ci (exporta RAIZ_DADOS)"
)


def _consultar(sql: str) -> list[tuple]:
    """Executa `sql` com `{nome}` substituído pelo `read_parquet` do mart em `gold/`."""
    gold = Path(os.environ["RAIZ_DADOS"]) / "gold"

    class _Tabelas(dict):
        def __missing__(self, nome: str) -> str:
            arquivo = gold / f"{nome}.parquet"
            assert arquivo.is_file(), f"{arquivo} não existe; rode `make ci`"
            return f"read_parquet('{arquivo}')"

    with duckdb.connect() as con:
        return con.execute(sql.format_map(_Tabelas())).fetchall()


def test_dim_municipio_fundao_com_populacao_2024() -> None:
    linhas = _consultar(
        "select sk_municipio, nome_municipio, ano_populacao, populacao, sigla_uf, "
        "nome_microrregiao, latitude from {dim_municipio} where codigo_rfb = '5643'"
    )
    assert len(linhas) == 1
    sk, nome, ano, populacao, uf, microrregiao, latitude = linhas[0]
    assert (sk, nome, ano, populacao, uf) == (3202207, "Fundão", 2024, 20000, "ES")
    assert microrregiao == "Linhares"
    assert latitude == pytest.approx(-19.9687204052472)


def test_dim_municipio_tem_membro_nao_informado() -> None:
    linhas = _consultar(
        "select nome_municipio, nome_uf, populacao from {dim_municipio} where sk_municipio = -1"
    )
    assert linhas == [("NÃO INFORMADO", "NÃO INFORMADO", None)]


def test_dim_municipio_tem_os_oito_municipios_do_bd_mais_o_membro_nao_informado() -> None:
    (total,) = _consultar("select count(*) from {dim_municipio}")[0]
    assert total == 8 + 1


def test_dim_cnae_tem_0111301_com_hierarquia_e_sem_o_cnae_sem_par_no_bd() -> None:
    (linha,) = _consultar(
        "select sk_cnae, codigo_subclasse, codigo_secao, descricao_subclasse "
        "from {dim_cnae} where codigo_subclasse = '0111301'"
    )
    assert linha[:3] == (111301, "0111301", "A")
    assert linha[3] == "Cultivo de arroz"
    # 3511500 só existe no domínio RFB; na dimensão é representado pelo membro -1.
    assert _consultar("select 1 from {dim_cnae} where codigo_subclasse = '3511500'") == []
    assert len(_consultar("select 1 from {dim_cnae}")) == 7 + 1


@pytest.mark.parametrize(
    ("dimensao", "chave"),
    [
        ("dim_municipio", "sk_municipio"),
        ("dim_cnae", "sk_cnae"),
        ("dim_natureza_juridica", "sk_natureza_juridica"),
        ("dim_porte", "sk_porte"),
        ("dim_situacao_cadastral", "sk_situacao_cadastral"),
    ],
)
def test_toda_dimensao_tem_membro_menos_um_e_chave_unica(dimensao: str, chave: str) -> None:
    total, distintas, menos_um = _consultar(
        f"select count(*), count(distinct {chave}), count(*) filter (where {chave} = -1) "
        f"from {{{dimensao}}}"
    )[0]
    assert total == distintas
    assert menos_um == 1


def test_dim_natureza_juridica_cobre_o_dominio_rfb_mais_o_membro() -> None:
    codigos = {
        r[0] for r in _consultar("select codigo_natureza_juridica from {dim_natureza_juridica}")
    }
    assert codigos == {"2062", "2135", "2305", "0000", "8885", "-1"}


def test_dim_porte_e_situacao_vem_dos_seeds() -> None:
    portes = dict(_consultar("select sk_porte, rotulo_porte from {dim_porte}"))
    assert portes == {0: "N/A", 1: "MICRO", 3: "PEQUENA", 5: "DEMAIS", -1: "NÃO INFORMADO"}
    situacoes = dict(
        _consultar(
            "select sk_situacao_cadastral, rotulo_situacao_cadastral from {dim_situacao_cadastral}"
        )
    )
    assert situacoes[2] == "ATIVA"
    assert situacoes[8] == "BAIXADA"
