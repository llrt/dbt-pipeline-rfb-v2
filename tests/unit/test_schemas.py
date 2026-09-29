from __future__ import annotations

from rfb_pipeline.schemas import COLUNAS_TECNICAS, ENTIDADES_RFB, entidade_do_zip

# Lista LITERAL de ARCHITECTURE.md §4.2 (não derivada de schemas.py): renomear/reordenar uma
# coluna em schemas.py precisa quebrar este teste (R1-10; mutações M18/M19).
COLUNAS_SPEC = {
    "empresas": "cnpj_raiz razao_social natureza_jur qualificacao_resp capital_soc porte "
    "ente_fed_resp",
    "estabelecimentos": "cnpj_raiz cnpj_ordem cnpj_dv ind_matriz_filial nome_fantasia situacao "
    "dat_situacao mot_situacao cidade_exterior pais dat_inicio_atividade cnae_principal "
    "cnaes_secundarios tip_logradouro logradouro num_logradouro compl_logradouro bairro cep uf "
    "municipio ddd1 tel1 ddd2 tel2 ddd_fax fax email sit_especial dat_sit_especial",
    "simples": "cnpj_raiz opcao_simples dat_opcao_simples dat_exclusao_simples opcao_mei "
    "dat_opcao_mei dat_exclusao_mei",
    **dict.fromkeys(
        ("cnaes", "municipios", "naturezas", "motivos", "paises", "qualificacoes"),
        "codigo descricao",
    ),
}


def test_colunas_de_cada_entidade_sao_exatamente_as_da_spec() -> None:
    assert set(ENTIDADES_RFB) == set(COLUNAS_SPEC)
    for nome, esperado in COLUNAS_SPEC.items():
        assert ENTIDADES_RFB[nome].colunas == tuple(esperado.split()), nome


def test_colunas_tecnicas_sao_as_da_spec() -> None:
    assert COLUNAS_TECNICAS == (
        "_arquivo_origem",
        "_mes_referencia",
        "_data_referencia",
        "_ingerido_em",
    )


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
