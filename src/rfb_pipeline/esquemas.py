"""Contrato da camada raw: entidades RFB (colunas, padrão de zip), tabelas BD e IBGE."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

COLUNAS_TECNICAS = ("_arquivo_origem", "_mes_referencia", "_data_referencia", "_ingerido_em")


@dataclass(frozen=True)
class EntidadeRFB:
    nome: str
    padrao_zip: re.Pattern[str]
    colunas: tuple[str, ...]


_COLUNAS_EMPRESAS = (
    "cnpj_raiz",
    "razao_social",
    "natureza_jur",
    "qualificacao_resp",
    "capital_soc",
    "porte",
    "ente_fed_resp",
)

_COLUNAS_ESTABELECIMENTOS = (
    "cnpj_raiz",
    "cnpj_ordem",
    "cnpj_dv",
    "ind_matriz_filial",
    "nome_fantasia",
    "situacao",
    "dat_situacao",
    "mot_situacao",
    "cidade_exterior",
    "pais",
    "dat_inicio_atividade",
    "cnae_principal",
    "cnaes_secundarios",
    "tip_logradouro",
    "logradouro",
    "num_logradouro",
    "compl_logradouro",
    "bairro",
    "cep",
    "uf",
    "municipio",
    "ddd1",
    "tel1",
    "ddd2",
    "tel2",
    "ddd_fax",
    "fax",
    "email",
    "sit_especial",
    "dat_sit_especial",
)

_COLUNAS_SIMPLES = (
    "cnpj_raiz",
    "opcao_simples",
    "dat_opcao_simples",
    "dat_exclusao_simples",
    "opcao_mei",
    "dat_opcao_mei",
    "dat_exclusao_mei",
)

_COLUNAS_DOMINIO = ("codigo", "descricao")

ENTIDADES_RFB: dict[str, EntidadeRFB] = {
    "empresas": EntidadeRFB(
        nome="empresas",
        padrao_zip=re.compile(r"^Empresas\d+\.zip$"),
        colunas=_COLUNAS_EMPRESAS,
    ),
    "estabelecimentos": EntidadeRFB(
        nome="estabelecimentos",
        padrao_zip=re.compile(r"^Estabelecimentos\d+\.zip$"),
        colunas=_COLUNAS_ESTABELECIMENTOS,
    ),
    "simples": EntidadeRFB(
        nome="simples",
        padrao_zip=re.compile(r"^Simples\.zip$"),
        colunas=_COLUNAS_SIMPLES,
    ),
    "cnaes": EntidadeRFB(
        nome="cnaes", padrao_zip=re.compile(r"^Cnaes\.zip$"), colunas=_COLUNAS_DOMINIO
    ),
    "municipios": EntidadeRFB(
        nome="municipios", padrao_zip=re.compile(r"^Municipios\.zip$"), colunas=_COLUNAS_DOMINIO
    ),
    "naturezas": EntidadeRFB(
        nome="naturezas", padrao_zip=re.compile(r"^Naturezas\.zip$"), colunas=_COLUNAS_DOMINIO
    ),
    "motivos": EntidadeRFB(
        nome="motivos", padrao_zip=re.compile(r"^Motivos\.zip$"), colunas=_COLUNAS_DOMINIO
    ),
    "paises": EntidadeRFB(
        nome="paises", padrao_zip=re.compile(r"^Paises\.zip$"), colunas=_COLUNAS_DOMINIO
    ),
    "qualificacoes": EntidadeRFB(
        nome="qualificacoes",
        padrao_zip=re.compile(r"^Qualificacoes\.zip$"),
        colunas=_COLUNAS_DOMINIO,
    ),
}


def entidade_do_zip(nome_zip: str) -> EntidadeRFB | None:
    """Identifica a entidade RFB a partir do nome do zip. `Socios*` e desconhecidos -> None."""
    for entidade in ENTIDADES_RFB.values():
        if entidade.padrao_zip.match(nome_zip):
            return entidade
    return None


ARQUIVOS_ESPERADOS_MES: tuple[str, ...] = (
    *(f"Empresas{i}.zip" for i in range(10)),
    *(f"Estabelecimentos{i}.zip" for i in range(10)),
    "Simples.zip",
    "Cnaes.zip",
    "Municipios.zip",
    "Naturezas.zip",
    "Motivos.zip",
    "Paises.zip",
    "Qualificacoes.zip",
)


def arquivos_faltantes(nomes: Iterable[str]) -> list[str]:
    """Arquivos de `ARQUIVOS_ESPERADOS_MES` ausentes em `nomes` (mês completo = lista vazia)."""
    presentes = set(nomes)
    return [n for n in ARQUIVOS_ESPERADOS_MES if n not in presentes]


@dataclass(frozen=True)
class TabelaBD:
    nome: str
    dataset: str
    tabela: str
    incremento: str | None = None  # marcador do incremento (ADR-0015)


TABELAS_BD: dict[str, TabelaBD] = {
    "municipio": TabelaBD(nome="municipio", dataset="br_bd_diretorios_brasil", tabela="municipio"),
    "cnae_2": TabelaBD(nome="cnae_2", dataset="br_bd_diretorios_brasil", tabela="cnae_2"),
    "populacao": TabelaBD(nome="populacao", dataset="br_ibge_populacao", tabela="municipio"),
    "pib": TabelaBD(nome="pib", dataset="br_ibge_pib", tabela="municipio"),
    # incremento: enriquecimento_bd
    "censo_2022_municipio": TabelaBD(
        nome="censo_2022_municipio",
        dataset="br_ibge_censo_2022",
        tabela="municipio",
        incremento="enriquecimento_bd",
    ),
    "regiao_metropolitana_2017": TabelaBD(
        nome="regiao_metropolitana_2017",
        dataset="br_geobr_mapas",
        tabela="regiao_metropolitana_2017",
        incremento="enriquecimento_bd",
    ),
    "vizinhanca_municipio": TabelaBD(
        nome="vizinhanca_municipio",
        dataset="br_bd_vizinhanca",
        tabela="municipio",
        incremento="enriquecimento_bd",
    ),
}


# incremento: enriquecimento_ibge
@dataclass(frozen=True)
class TabelaIBGE:
    """Tabela raw baixada direto do IBGE (`raw/ibge/<nome>/<nome>.parquet`); ver `ibge.py`."""

    nome: str
    origem: str  # "sidra" (API SIDRA) | "regic" (planilha do geoftp)
    # Colunas publicadas, como na fonte dbt `ibge` (sem `_arquivo_origem`/`_ingerido_em`): o esquema
    # do Parquet vazio que o modo offline publica quando falta o arquivo (`ibge.py`).
    colunas: tuple[str, ...] = ()
    incremento: str | None = "enriquecimento_ibge"


_COLUNAS_SIDRA = ("nc", "mc", "v", "d1c", "d2c", "d3c", "d4c")
_Q = tuple(f"q{i}" for i in range(1, 11))
_IA_Q = tuple(f"ia_q{i}" for i in range(1, 11))
_LADO_LIGACAO = (
    "uf_{l} mun_{l} mun_{c} nome_{l} pop2018_{s} cod_arr_{s} nome_arr_{s} hierar_mun_{s}"
)

TABELAS_IBGE: dict[str, TabelaIBGE] = {
    t.nome: t
    for t in (
        TabelaIBGE(
            nome="cempre_categorias_cnae",
            origem="sidra",
            colunas=tuple("nc nn mc mn v d1c d1n d2c d2n d3c d3n d4c d4n".split()),
        ),
        TabelaIBGE(nome="cempre_municipio_cnae", origem="sidra", colunas=_COLUNAS_SIDRA),
        TabelaIBGE(
            nome="renda_censo_2022_municipio",
            origem="sidra",
            colunas=(*_COLUNAS_SIDRA, "d5c", "d6c"),
        ),
        TabelaIBGE(
            nome="regic_2018_hierarquia",
            origem="regic",
            colunas=(
                *"coduf siguf uf grande_regiao codmun municipio categoria codap".split(),
                *"arranjo_populacional codcid hierarquia hierarquia_2 hierarquia_3".split(),
                *"hierarquia_grupo multiplas_subordinacoes".split(),
                "regiao_de_influencia_vinculacao_imediata_consolidada",
                *(f"regiao_de_influencia_{i}" for i in range(1, 5)),
            ),
        ),
        TabelaIBGE(
            nome="regic_2018_ligacoes",
            origem="regic",
            colunas=(
                "id",
                *_LADO_LIGACAO.format(l="origem", c="or", s="o").split(),
                "hierar_cid",
                "nome_hierar_cid",
                *_LADO_LIGACAO.format(l="destino", c="dest", s="d").split(),
                "hierar_cid_d",
                "nome_hierar_cid_d",
                *_Q,
                *_IA_Q,
                *"perc_lig ia x_origem y_origem x_destino y_destino".split(),
            ),
        ),
        TabelaIBGE(
            nome="regic_2018_atracao",
            origem="regic",
            colunas=(
                *"codmun nome_mun hierar_mun int_arr hierar_cid nome_hierar_cid".split(),
                *"cod_arr nome_arr pop2018 ia".split(),
                *_IA_Q,
            ),
        ),
    )
}
