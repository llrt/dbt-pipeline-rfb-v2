from __future__ import annotations

from rfb_pipeline.schemas import ENTIDADES_RFB, entidade_do_zip


def test_estabelecimentos_tem_30_colunas() -> None:
    assert len(ENTIDADES_RFB["estabelecimentos"].colunas) == 30


def test_empresas_tem_7_colunas() -> None:
    assert len(ENTIDADES_RFB["empresas"].colunas) == 7


def test_simples_tem_7_colunas() -> None:
    assert len(ENTIDADES_RFB["simples"].colunas) == 7


def test_dominios_tem_2_colunas() -> None:
    for nome in ("cnaes", "municipios", "naturezas", "motivos", "paises", "qualificacoes"):
        assert len(ENTIDADES_RFB[nome].colunas) == 2


def test_entidade_do_zip_nao_reconhece_socios() -> None:
    assert entidade_do_zip("Socios0.zip") is None
    assert entidade_do_zip("Socios3.zip") is None


def test_entidade_do_zip_reconhece_cada_entidade() -> None:
    assert entidade_do_zip("Empresas0.zip").nome == "empresas"
    assert entidade_do_zip("Estabelecimentos3.zip").nome == "estabelecimentos"
    assert entidade_do_zip("Simples.zip").nome == "simples"
    assert entidade_do_zip("Cnaes.zip").nome == "cnaes"
    assert entidade_do_zip("Municipios.zip").nome == "municipios"
    assert entidade_do_zip("Naturezas.zip").nome == "naturezas"
    assert entidade_do_zip("Motivos.zip").nome == "motivos"
    assert entidade_do_zip("Paises.zip").nome == "paises"
    assert entidade_do_zip("Qualificacoes.zip").nome == "qualificacoes"


def test_entidade_do_zip_nao_reconhece_arquivo_desconhecido() -> None:
    assert entidade_do_zip("ArquivoDesconhecido.zip") is None
