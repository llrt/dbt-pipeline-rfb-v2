"""Contrato da camada raw: entidades RFB (colunas, padrão de zip) e tabelas da Base dos Dados."""

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
