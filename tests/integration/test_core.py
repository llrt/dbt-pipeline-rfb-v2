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


def test_dim_data_tem_29_de_fevereiro_de_2000_e_a_data_de_referencia() -> None:
    (linha,) = _consultar(
        "select data, ano, mes, nome_mes, ano_mes, dia_semana from {dim_data} "
        "where sk_data = 20000229"
    )
    assert str(linha[0]) == "2000-02-29"
    assert linha[1:] == (2000, 2, "fevereiro", "2000-02", "terça-feira")
    (referencia,) = _consultar("select data from {dim_data} where sk_data = 20260912")[0]
    assert str(referencia) == "2026-09-12"


def test_dim_data_vai_de_1900_a_data_de_referencia_sem_lacunas() -> None:
    primeiro, ultimo, dias = _consultar(
        "select min(data), max(data), count(*) from {dim_data} where sk_data > 0"
    )[0]
    assert str(primeiro) == "1900-01-01"  # R3-03: início fixo, não o menor dia das fatos
    assert str(ultimo) == "2026-09-12"
    assert dias == (ultimo - primeiro).days + 1


def test_dim_data_membros_menos_um_e_menos_dois_tem_data_contigua_e_sem_ano() -> None:
    """R3-03: sem data NULL (tabela de datas do Power BI) e sem atributos de calendário."""
    linhas = _consultar(
        "select sk_data, cast(data as varchar), ano, mes, nome_mes from {dim_data} "
        "where sk_data < 0 order by sk_data"
    )
    assert linhas == [
        (-2, "1899-12-30", None, None, "DATA INVÁLIDA"),
        (-1, "1899-12-31", None, None, "NÃO INFORMADO"),
    ]
    assert _consultar("select count(*) from {dim_data} where data is null")[0][0] == 0


# cnpj_completo do cenário (spec): raiz + ordem + DV.
CNPJ_A = "11111111000191"
CNPJ_C = "33333333000191"
CNPJ_K = "13131313000120"
CNPJ_L = "14141414000155"  # DV inválido (proposital)
CNPJ_M = "15151515000160"
CNPJ_O = "11111111000272"


def test_fato_tem_16_linhas_sem_descartes() -> None:
    assert _consultar(
        "select count(*), count(distinct cnpj_completo) from {fct_estabelecimentos}"
    ) == [(16, 16)]


def test_fato_k_l_m_presentes_com_menos_um_na_dimensao_faltante() -> None:
    linhas = {
        r[0]: r[1:]
        for r in _consultar(
            "select cnpj_completo, sk_municipio, sk_cnae, sk_natureza_juridica "
            "from {fct_estabelecimentos} where cnpj_completo in ('13131313000120', "
            "'14141414000155', '15151515000160')"
        )
    }
    assert set(linhas) == {CNPJ_K, CNPJ_L, CNPJ_M}
    # K: município EXTERIOR (9707) sem par no BD; L: CNAE 3511500 sem par no BD (e DV inválido);
    # M: município 1182 sem par no BD. Nas demais dimensões têm par.
    assert linhas[CNPJ_K][0] == -1 and linhas[CNPJ_K][1] != -1
    assert linhas[CNPJ_L][1] == -1 and linhas[CNPJ_L][0] != -1
    assert linhas[CNPJ_M][0] == -1 and linhas[CNPJ_M][1] != -1
    assert all(linha[2] != -1 for linha in linhas.values())


def test_fato_m_tem_data_da_situacao_nula_como_menos_um() -> None:
    (linha,) = _consultar(
        "select sk_data_inicio_atividade, sk_data_situacao from {fct_estabelecimentos} "
        f"where cnpj_completo = '{CNPJ_M}'"
    )
    assert linha == (20231201, -1)


def test_fato_a_e_c_sao_mei() -> None:
    mei = {
        r[0] for r in _consultar("select cnpj_completo from {fct_estabelecimentos} where opcao_mei")
    }
    # A e a filial O (mesma raiz, a opção é da empresa) e C.
    assert mei == {CNPJ_A, CNPJ_O, CNPJ_C}


def test_fato_linha_a_atributos() -> None:
    (linha,) = _consultar(
        "select f.idade_anos, f.eh_matriz, f.eh_ativa, f.opcao_simples, f.capital_social, "
        "m.nome_municipio, c.codigo_subclasse, n.codigo_natureza_juridica, p.rotulo_porte, "
        "s.rotulo_situacao_cadastral, d.data "
        "from {fct_estabelecimentos} f "
        "join {dim_municipio} m using (sk_municipio) join {dim_cnae} c using (sk_cnae) "
        "join {dim_natureza_juridica} n using (sk_natureza_juridica) "
        "join {dim_porte} p using (sk_porte) "
        "join {dim_situacao_cadastral} s using (sk_situacao_cadastral) "
        "join {dim_data} d on d.sk_data = f.sk_data_inicio_atividade "
        f"where f.cnpj_completo = '{CNPJ_A}'"
    )
    assert linha[:4] == (3.9, True, True, True)
    assert linha[5:10] == ("Fundão", "4741500", "2135", "MICRO", "ATIVA")
    assert str(linha[10]) == "2022-10-15"


def test_fato_linha_o_e_filial() -> None:
    (linha,) = _consultar(
        f"select eh_matriz, eh_ativa from {{fct_estabelecimentos}} where cnpj_completo = '{CNPJ_O}'"
    )
    assert linha == (False, True)


def test_bridge_h_tem_duas_linhas_e_o_resto_nenhuma() -> None:
    linhas = _consultar(
        "select cnpj_completo, codigo_cnae_secundario, sk_cnae "
        "from {bridge_estabelecimento_cnae_secundario} order by 2"
    )
    assert linhas == [
        ("88888888000191", "4679699", 4679699),
        ("88888888000191", "4744099", 4744099),
    ]
