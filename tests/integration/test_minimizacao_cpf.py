"""CPF mascarado nos nomes do gold (ADR-0008, emenda R4-01).

Fixtures: C (EI, `PINTE BEM 52998224725`, CPF depois de um espaço) chega a `bh_empresas`; P
(`TINTAS ARACRUZ IND11144477735`, CPF colado) é fornecedor de Fundão em
`mart_fornecedores_proximos`.
Lê `RAIZ_DADOS` do ambiente, exportado pelo `make ci`.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import duckdb
import pytest
from test_bh_empresas import _status_dos_testes

pytestmark = pytest.mark.skipif(
    "RAIZ_DADOS" not in os.environ, reason="rode via make ci (exporta RAIZ_DADOS)"
)

MASCARA = "***.***.***-**"
_RE_TRECHO_11 = re.compile(r"(?<![0-9])[0-9]{11}(?![0-9])")


def _cpf_valido(digitos: str) -> bool:
    numeros = [int(d) for d in digitos]
    for posicao in (9, 10):
        soma = sum(n * (posicao + 1 - i) for i, n in enumerate(numeros[:posicao]))
        if (soma * 10 % 11) % 10 != numeros[posicao]:
            return False
    return True


def _raw(entidade: str, onde: str, colunas: str = "*") -> list[tuple]:
    raw = Path(os.environ["RAIZ_DADOS"]) / "raw" / "rfb" / entidade
    with duckdb.connect() as con:
        return con.sql(
            f"select {colunas} from read_parquet('{raw}/*/*.parquet') "
            f"where _mes_referencia = '2026-09' and {onde}"
        ).fetchall()


def test_raw_preserva_o_cpf_da_fonte() -> None:
    """O raw é o arquivo como publicado (ADR-0008); a máscara só vale do gold em diante."""
    assert _raw("empresas", "cnpj_raiz = '33333333'", "razao_social") == [
        ("PINTE BEM 52998224725",)
    ]
    assert _cpf_valido("52998224725") and _cpf_valido("11144477735")


def test_bh_empresas_mascara_o_cpf_do_empresario_individual(consultar) -> None:
    linhas = consultar(
        "select nome, natureza_juridica from {bh_empresas} where cnpj_raiz = '33333333'"
    )
    assert linhas == [(f"PINTE BEM {MASCARA}", "EMPRESÁRIO (INDIVIDUAL)")]


def test_fornecedores_mascara_o_cpf_colado_ao_nome(consultar) -> None:
    linhas = consultar(
        "select nome, municipio from {mart_fornecedores_proximos} "
        "where cnpj_completo like '17171717%'"
    )
    assert linhas == [(f"TINTAS ARACRUZ IND{MASCARA}", "Aracruz")]


@pytest.mark.parametrize("mart", ["bh_empresas", "mart_fornecedores_proximos"])
def test_nenhum_nome_do_gold_tem_cpf_valido(consultar, mart: str) -> None:
    nomes = [nome for (nome,) in consultar(f"select nome from {{{mart}}} where nome is not null")]
    assert nomes
    com_cpf = [n for n in nomes if any(_cpf_valido(t) for t in _RE_TRECHO_11.findall(n))]
    assert com_cpf == []


def test_testes_da_mascara_e_paridade_passam() -> None:
    status = _status_dos_testes()
    sem_cpf = {nome: s for nome, s in status.items() if nome.startswith("sem_cpf_no_nome_")}
    assert sem_cpf == {
        "sem_cpf_no_nome_bh_empresas_nome": ("pass", 0),
        "sem_cpf_no_nome_mart_fornecedores_proximos_nome": ("pass", 0),
    }
    assert status["mascarar_cpf_no_nome_casos"] == ("pass", 0)
    assert status["paridade_bh_empresas"] == ("pass", 0)
