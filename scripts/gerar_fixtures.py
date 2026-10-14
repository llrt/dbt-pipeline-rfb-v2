"""Gerador determinístico de fixtures sintéticas RFB/CNPJ, Base dos Dados e IBGE.

Reproduz o formato real dos arquivos publicados no WebDAV da RFB para o mês
2026-09 (zips com um único arquivo interno, latin-1, separador `;`, todos os
campos entre aspas, fim de linha LF) e os csv.gz da Base dos Dados
(API downloadTable: UTF-8, vírgula, cabecalho), além das respostas da API SIDRA e das planilhas
REGIC do IBGE em `ibge/` (formato lido por `rfb_pipeline.ibge`). Duas execuções produzem bytes
idênticos: timestamps de zip/gzip são fixados e a ordem de escrita é estável.

O cenário de dados (municípios, CNAEs, naturezas, empresas e estabelecimentos)
reproduz exatamente os valores descritos em
`.specs/features/rfb-dbt-port/spec.md` §"Cenário de fixtures com respostas
conhecidas", fonte de verdade dos valores esperados pelos testes downstream.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path

import openpyxl

MES_REFERENCIA = "2026-09"
DATA_REFERENCIA_TAG = "D60912"  # último dígito do ano (2026 -> 6) + 0912
ZIP_DATE_TIME = (2026, 9, 12, 0, 0, 0)

# Segundo mês (spec §"Segundo mês"): idêntico a 2026-09, sem a linha O, com a linha R SUSPENSA
# (e não BAIXADA) e com nomes internos D60810.
MES_ANTERIOR = "2026-08"
DATA_REFERENCIA_TAG_ANTERIOR = "D60810"
ZIP_DATE_TIME_ANTERIOR = (2026, 8, 10, 0, 0, 0)
ID_ESTABELECIMENTO_AUSENTE_NO_ANTERIOR = "O"
GZIP_MTIME = 0

CODIFICACAO_RFB = "latin-1"
CODIFICACAO_BD = "utf-8"


def calcular_dv_cnpj(base12: str) -> str:
    """Calcula os 2 dígitos verificadores oficiais do CNPJ para uma base de 12 dígitos."""
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    soma1 = sum(int(d) * p for d, p in zip(base12, pesos1, strict=True))
    resto1 = soma1 % 11
    dv1 = 0 if resto1 < 2 else 11 - resto1

    base13 = base12 + str(dv1)
    soma2 = sum(int(d) * p for d, p in zip(base13, pesos2, strict=True))
    resto2 = soma2 % 11
    dv2 = 0 if resto2 < 2 else 11 - resto2

    return f"{dv1}{dv2}"


def dv_invalido(dv_correto: str) -> str:
    """Retorna um DV de 2 dígitos garantidamente diferente do correto."""
    primeiro = (int(dv_correto[0]) + 1) % 10
    return f"{primeiro}{dv_correto[1]}"


def _escrever_csv_rfb(colunas: list[str], linhas: list[list[str]]) -> bytes:
    memoria_intermediaria = io.StringIO(newline="")
    writer = csv.writer(
        memoria_intermediaria,
        delimiter=";",
        quotechar='"',
        quoting=csv.QUOTE_ALL,
        lineterminator="\n",
    )
    for linha in linhas:
        writer.writerow(linha)
    return memoria_intermediaria.getvalue().encode(CODIFICACAO_RFB)


def _escrever_zip(
    destino: Path, nome_interno: str, conteudo: bytes, date_time: tuple = ZIP_DATE_TIME
) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destino, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        info = zipfile.ZipInfo(nome_interno, date_time=date_time)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o600 << 16
        zf.writestr(info, conteudo)


def gerar_zip_rfb(
    saida_dir: Path,
    nome_zip: str,
    nome_interno: str,
    colunas: list[str],
    linhas: list[list[str]],
    mes: str = MES_REFERENCIA,
    date_time: tuple = ZIP_DATE_TIME,
) -> Path:
    conteudo = _escrever_csv_rfb(colunas, linhas)
    destino = saida_dir / "rfb" / mes / nome_zip
    _escrever_zip(destino, nome_interno, conteudo, date_time)
    return destino


def gerar_csv_gz_bd(
    saida_dir: Path, nome_tabela: str, cabecalho: list[str], linhas: list[list[str]]
) -> Path:
    memoria_intermediaria = io.StringIO(newline="")
    writer = csv.writer(
        memoria_intermediaria,
        delimiter=",",
        quotechar='"',
        quoting=csv.QUOTE_MINIMAL,
        lineterminator="\n",
    )
    writer.writerow(cabecalho)
    for linha in linhas:
        writer.writerow(linha)
    conteudo = memoria_intermediaria.getvalue().encode(CODIFICACAO_BD)

    destino = saida_dir / "bd" / f"{nome_tabela}.csv.gz"
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "wb") as fh:
        with gzip.GzipFile(fileobj=fh, mode="wb", mtime=GZIP_MTIME, filename="") as gz:
            gz.write(conteudo)
    return destino


# ---------------------------------------------------------------------------
# Domínios RFB (codigo, descricao) — spec §"Cenário de fixtures"
# ---------------------------------------------------------------------------

DOMINIO_MUNICIPIOS = [
    ("5643", "FUNDAO"),
    ("5663", "LINHARES"),
    ("5611", "ARACRUZ"),
    ("5699", "SERRA"),
    ("5705", "VITORIA"),
    ("2701", "AGUA BRANCA"),
    ("1003", "AGUA BRANCA"),
    ("1901", "AGUA BRANCA"),
    ("9707", "EXTERIOR"),
    ("1182", "BOA ESPERANCA DO NORTE"),
]

DOMINIO_CNAES = [
    ("4741500", "Comercio varejista de tintas, vernizes e materiais para pintura"),
    ("2071100", "Fabricacao de tintas, vernizes, esmaltes e lacas"),
    ("4679601", "Comercio atacadista de tintas, vernizes e materiais para pintura"),
    ("4679699", "Comercio atacadista de materiais de construcao em geral"),
    ("4711302", "Comercio varejista de mercadorias em geral - minimercados e mercearias"),
    ("4744099", "Comercio varejista de materiais de construcao em geral"),
    ("0111301", "Cultivo de arroz"),
    ("3511500", "Geracao de energia eletrica"),
]

DOMINIO_NATUREZAS = [
    ("2062", "Sociedade Empresária Limitada"),
    ("2135", "Empresário (Individual)"),
    ("2305", "Empresa Individual de Responsabilidade Limitada (de Natureza Empresária)"),
    ("0000", "Natureza Jurídica não informada"),
    ("8885", "Natureza Jurídica não informada"),
]

DOMINIO_MOTIVOS = [
    ("00", "SEM MOTIVO"),
    ("01", "EXTINCAO POR ENCERRAMENTO LIQUIDACAO VOLUNTARIA"),
]

DOMINIO_PAISES = [
    ("249", "ESTADOS UNIDOS"),
    ("586", "PORTUGAL"),
]

DOMINIO_QUALIFICACOES = [
    ("49", "Sócio-Administrador"),
    ("22", "Sócio"),
]


# ---------------------------------------------------------------------------
# Cenário de estabelecimentos/empresas — spec §"Cenário de fixtures", tabela A-O
# ---------------------------------------------------------------------------

# id, cnpj_raiz, cnpj_ordem, ind_matriz_filial, nome_fantasia, situacao,
# dat_situacao (None -> usa dat_inicio_atividade; "" -> vazio literal),
# mot_situacao, municipio, cnae_principal, cnaes_secundarios, dat_inicio_atividade,
# uf, pais, cidade_exterior
_ESTABELECIMENTOS_RAW = [
    dict(
        id="A",
        raiz="11111111",
        ordem="0001",
        matriz_filial="1",
        nome_fantasia="TINTAS FUNDÃO",
        situacao="02",
        dat_situacao=None,
        mot_situacao="00",
        municipio="5643",
        cnae_principal="4741500",
        cnaes_secundarios="",
        dat_inicio="20221015",
        uf="ES",
        pais="",
        cidade_exterior="",
    ),
    dict(
        id="B",
        raiz="22222222",
        ordem="0001",
        matriz_filial="1",
        nome_fantasia="",
        situacao="08",
        dat_situacao="20190510",
        mot_situacao="01",
        municipio="5643",
        cnae_principal="4741500",
        cnaes_secundarios="",
        dat_inicio="20150301",
        uf="ES",
        pais="",
        cidade_exterior="",
    ),
    dict(
        id="C",
        raiz="33333333",
        ordem="0001",
        matriz_filial="1",
        nome_fantasia="",
        situacao="08",
        dat_situacao="20210815",
        mot_situacao="01",
        municipio="5643",
        cnae_principal="4741500",
        cnaes_secundarios="",
        dat_inicio="20200110",
        uf="ES",
        pais="",
        cidade_exterior="",
    ),
    dict(
        id="D",
        raiz="44444444",
        ordem="0001",
        matriz_filial="1",
        nome_fantasia="",
        situacao="04",
        dat_situacao="20230101",
        mot_situacao="01",
        municipio="5643",
        cnae_principal="4741500",
        cnaes_secundarios="",
        dat_inicio="20100601",
        uf="ES",
        pais="",
        cidade_exterior="",
    ),
    dict(
        id="E",
        raiz="55555555",
        ordem="0001",
        matriz_filial="1",
        nome_fantasia="",
        situacao="08",
        dat_situacao="20240301",
        mot_situacao="01",
        municipio="5643",
        cnae_principal="4741500",
        cnaes_secundarios="",
        dat_inicio="20180101",
        uf="ES",
        pais="",
        cidade_exterior="",
    ),
    dict(
        id="F",
        raiz="66666666",
        ordem="0001",
        matriz_filial="1",
        nome_fantasia="",
        situacao="02",
        dat_situacao=None,
        mot_situacao="00",
        municipio="5699",
        cnae_principal="2071100",
        cnaes_secundarios="",
        dat_inicio="20000101",
        uf="ES",
        pais="",
        cidade_exterior="",
    ),
    dict(
        id="G",
        raiz="77777777",
        ordem="0001",
        matriz_filial="1",
        nome_fantasia="",
        situacao="02",
        dat_situacao=None,
        mot_situacao="00",
        municipio="5705",
        cnae_principal="4679601",
        cnaes_secundarios="",
        dat_inicio="20050505",
        uf="ES",
        pais="",
        cidade_exterior="",
    ),
    dict(
        id="H",
        raiz="88888888",
        ordem="0001",
        matriz_filial="1",
        nome_fantasia="",
        situacao="02",
        dat_situacao=None,
        mot_situacao="00",
        municipio="5663",
        cnae_principal="4711302",
        cnaes_secundarios="4679699,4744099",
        dat_inicio="20120312",
        uf="ES",
        pais="",
        cidade_exterior="",
    ),
    dict(
        id="I",
        raiz="99999999",
        ordem="0001",
        matriz_filial="1",
        nome_fantasia="",
        situacao="08",
        dat_situacao="20200101",
        mot_situacao="01",
        municipio="5611",
        cnae_principal="4679601",
        cnaes_secundarios="",
        dat_inicio="20080101",
        uf="ES",
        pais="",
        cidade_exterior="",
    ),
    dict(
        id="J",
        raiz="12121212",
        ordem="0001",
        matriz_filial="1",
        nome_fantasia="",
        situacao="02",
        dat_situacao=None,
        mot_situacao="00",
        municipio="2701",
        cnae_principal="2071100",
        cnaes_secundarios="",
        dat_inicio="20190101",
        uf="AL",
        pais="",
        cidade_exterior="",
    ),
    dict(
        id="K",
        raiz="13131313",
        ordem="0001",
        matriz_filial="1",
        nome_fantasia="",
        situacao="02",
        dat_situacao=None,
        mot_situacao="00",
        municipio="9707",
        cnae_principal="4711302",
        cnaes_secundarios="",
        dat_inicio="20210101",
        uf="EX",
        pais="249",
        cidade_exterior="MIAMI",
    ),
    dict(
        id="L",
        raiz="14141414",
        ordem="0001",
        matriz_filial="1",
        nome_fantasia="",
        situacao="02",
        dat_situacao=None,
        mot_situacao="00",
        municipio="5699",
        cnae_principal="3511500",
        cnaes_secundarios="",
        dat_inicio="20160101",
        uf="ES",
        pais="",
        cidade_exterior="",
    ),
    dict(
        id="M",
        raiz="15151515",
        ordem="0001",
        matriz_filial="1",
        nome_fantasia="",
        situacao="02",
        dat_situacao="00000000",
        mot_situacao="00",
        municipio="1182",
        cnae_principal="4711302",
        cnaes_secundarios="",
        dat_inicio="20231201",
        uf="RN",
        pais="",
        cidade_exterior="",
    ),
    dict(
        id="N",
        raiz="16161616",
        ordem="0001",
        matriz_filial="1",
        nome_fantasia="",
        situacao="02",
        dat_situacao=None,
        mot_situacao="00",
        municipio="5643",
        cnae_principal="0111301",
        cnaes_secundarios="",
        dat_inicio="20000229",
        uf="ES",
        pais="",
        cidade_exterior="",
    ),
    dict(
        id="O",
        raiz="11111111",
        ordem="0002",
        matriz_filial="2",
        nome_fantasia="TINTAS FUNDAO\nFILIAL SERRA",
        situacao="02",
        dat_situacao=None,
        mot_situacao="00",
        municipio="5699",
        cnae_principal="4741500",
        cnaes_secundarios="",
        dat_inicio="20240115",
        uf="ES",
        pais="",
        cidade_exterior="",
    ),
    # P (R3-04): fabricante ativo na microrregião de Fundão, fora do município; mata a mutação que
    # tira o `upper` da comparação de microrregião na analysis q4.
    dict(
        id="P",
        raiz="17171717",
        ordem="0001",
        matriz_filial="1",
        nome_fantasia="",
        situacao="02",
        dat_situacao=None,
        mot_situacao="00",
        municipio="5611",
        cnae_principal="2071100",
        cnaes_secundarios="",
        dat_inicio="20180301",
        uf="ES",
        pais="",
        cidade_exterior="",
    ),
    # Q (FSEM): baixado sem data de início nem data da situação (`00000000`, chave -1 nas duas),
    # longe do estudo de caso; não gera abertura nem encerramento em `mart_dinamica_mercado` nem
    # nas métricas `aberturas`/`encerramentos` (mata a mutação que tira o filtro de data válida).
    dict(
        id="Q",
        raiz="18181818",
        ordem="0001",
        matriz_filial="1",
        nome_fantasia="",
        situacao="08",
        dat_situacao="00000000",
        mot_situacao="01",
        municipio="1901",
        cnae_principal="0111301",
        cnaes_secundarios="",
        dat_inicio="00000000",
        uf="PB",
        pais="",
        cidade_exterior="",
    ),
    # R (FRSEM, RSEM-01): filial de J em Água Branca/PB, SUSPENSA no extrato de 2026-08 e
    # BAIXADA no de 2026-09 (campos `*_anterior`). Longe do estudo de caso: o recorte
    # PB × SUSPENSA só existe no penúltimo mês e documenta a fotografia do
    # `non_additive_dimension` com filtro.
    dict(
        id="R",
        raiz="12121212",
        ordem="0002",
        matriz_filial="2",
        nome_fantasia="",
        situacao="08",
        dat_situacao="20260820",
        mot_situacao="01",
        situacao_anterior="03",
        dat_situacao_anterior="20260302",
        mot_situacao_anterior="00",
        municipio="1901",
        cnae_principal="0111301",
        cnaes_secundarios="",
        dat_inicio="20190603",
        uf="PB",
        pais="",
        cidade_exterior="",
    ),
]

# cnpj_raiz -> (razao_social, natureza_jur, porte, capital_soc) — nível empresa.
# 16 raízes (A-N, P, Q); O reaproveita a raiz de A (11111111) e R, a de J (12121212).
_EMPRESA_POR_RAIZ = {
    "11111111": ("TINTAS FUNDAO LTDA", "2135", "01", "1000,00"),  # A
    "22222222": ("COLORIR TINTAS", "2062", "03", "1000,00"),  # B
    # Empresário individual: razão social "NOME + CPF" (CPF sintético com DV válido; ADR-0008,
    # emenda R4-01): `nome` sai mascarado em `bh_empresas`. Com espaço antes do CPF.
    "33333333": ("PINTE BEM 52998224725", "2135", "01", "1000,50"),  # C
    "44444444": ("CASA DAS CORES", "2062", "05", "1000,00"),  # D
    "55555555": ("TINTAS CAPIXABA", "2305", "", "1000,00"),  # E
    "66666666": ("FABRICA DE TINTAS SERRA SA", "2062", "05", "1000,00"),  # F
    # Espaço à esquerda e sem nome fantasia (R2-01): o staging aplica trim; o original não.
    "77777777": (" ATACADO VITORIA TINTAS", "2062", "03", "1000,00"),  # G
    "88888888": ("MERCADO LINHARES", "2062", "03", "1000,00"),  # H
    "99999999": ("ATACADO ARACRUZ", "2062", "01", "1000,00"),  # I
    "12121212": ("TINTAS SERTAO", "2062", "01", "1000,00"),  # J
    # Razão social termina em "\" no arquivo original (quirk de escape RFB).
    "13131313": ("EMPRESA EXTERIOR LTDA\\", "2062", "00", "1000,00"),  # K
    "14141414": ("ENERGIA NOVA", "2062", "05", "1000,00"),  # L
    "15151515": ("BOA ESPERANCA COMERCIO", "2135", "01", "1000,00"),  # M
    "16161616": ("AGRO FUNDAO", "2135", "00", "1000,00"),  # N
    # CPF colado ao nome (sem espaço; R4-01): exercita a máscara em `mart_fornecedores_proximos`.
    "17171717": ("TINTAS ARACRUZ IND11144477735", "2062", "03", "1000,00"),  # P
    "18181818": ("SITIO AGUA BRANCA", "2062", "01", "1000,00"),  # Q
}

# Raízes optantes pelo MEI/Simples (A e C); demais N; toda raiz é optante do Simples.
_RAIZES_MEI = {"11111111", "33333333"}


# ---------------------------------------------------------------------------
# Base dos Dados — csv.gz (UTF-8, vírgula, cabecalho)
# ---------------------------------------------------------------------------

CABECALHO_MUNICIPIO_BD = [
    "id_municipio",
    "id_municipio_6",
    "id_municipio_tse",
    "id_municipio_rf",
    "id_municipio_bcb",
    "nome",
    "capital_uf",
    "id_comarca",
    "id_regiao_saude",
    "nome_regiao_saude",
    "id_regiao_imediata",
    "nome_regiao_imediata",
    "id_regiao_intermediaria",
    "nome_regiao_intermediaria",
    "id_microrregiao",
    "nome_microrregiao",
    "id_mesorregiao",
    "nome_mesorregiao",
    "id_regiao_metropolitana",
    "nome_regiao_metropolitana",
    "ddd",
    "id_uf",
    "sigla_uf",
    "nome_uf",
    "nome_regiao",
    "amazonia_legal",
    "centroide",
]

# id_municipio, id_municipio_rf, nome, uf, id_uf, capital_uf, ddd, nome_regiao,
# micro (id, nome), meso (id, nome), reg. imediata (id, nome), reg. intermediária
# (id, nome), regiao_metropolitana (id, nome) ou ("", ""), centroide
_MUNICIPIOS_BD = [
    dict(
        id="3202207",
        id_rf="5643",
        nome="Fundão",
        uf="ES",
        id_uf="32",
        capital=False,
        ddd="27",
        regiao="Sudeste",
        micro=("32007", "Linhares"),
        meso=("3202", "Litoral Norte Espírito-santense"),
        reg_imediata=("320005", "Vitória"),
        reg_intermediaria=("3202", "Vitória"),
        rm=("3205", "Região Metropolitana da Grande Vitória"),
        centroide="POINT(-40.3557928987053 -19.9687204052472)",
    ),
    dict(
        id="3203205",
        id_rf="5663",
        nome="Linhares",
        uf="ES",
        id_uf="32",
        capital=False,
        ddd="27",
        regiao="Sudeste",
        micro=("32007", "Linhares"),
        meso=("3202", "Litoral Norte Espírito-santense"),
        reg_imediata=("320002", "Linhares"),
        reg_intermediaria=("3203", "São Mateus"),
        rm=("", ""),
        centroide="POINT(-40.0286164065601 -19.3821001934877)",
    ),
    dict(
        id="3200607",
        id_rf="5611",
        nome="Aracruz",
        uf="ES",
        id_uf="32",
        capital=False,
        ddd="27",
        regiao="Sudeste",
        micro=("32007", "Linhares"),
        meso=("3202", "Litoral Norte Espírito-santense"),
        reg_imediata=("320002", "Linhares"),
        reg_intermediaria=("3203", "São Mateus"),
        rm=("", ""),
        centroide="POINT(-40.1758978602985 -19.7659695292442)",
    ),
    dict(
        id="3205002",
        id_rf="5699",
        nome="Serra",
        uf="ES",
        id_uf="32",
        capital=False,
        ddd="27",
        regiao="Sudeste",
        micro=("32014", "Vitória"),
        meso=("3203", "Central Espírito-santense"),
        reg_imediata=("320005", "Vitória"),
        reg_intermediaria=("3202", "Vitória"),
        rm=("3205", "Região Metropolitana da Grande Vitória"),
        centroide="POINT(-40.3011804058758 -20.1284748148379)",
    ),
    dict(
        id="3205309",
        id_rf="5705",
        nome="Vitória",
        uf="ES",
        id_uf="32",
        capital=True,
        ddd="27",
        regiao="Sudeste",
        micro=("32014", "Vitória"),
        meso=("3203", "Central Espírito-santense"),
        reg_imediata=("320005", "Vitória"),
        reg_intermediaria=("3202", "Vitória"),
        rm=("3205", "Região Metropolitana da Grande Vitória"),
        centroide="POINT(-39.176338320945 -20.3338472806447)",
    ),
    dict(
        id="2700102",
        id_rf="2701",
        nome="Água Branca",
        uf="AL",
        id_uf="27",
        capital=False,
        ddd="82",
        regiao="Nordeste",
        micro=("2701", "Serrana do Sertão Alagoano"),
        meso=("2702", "Sertão Alagoano"),
        reg_imediata=("270013", "Delmiro Gouveia"),
        reg_intermediaria=("2703", "Arapiraca"),
        rm=("", ""),
        centroide="POINT(-37.9018536858562 -9.27325871173002)",
    ),
    dict(
        id="2200202",
        id_rf="1003",
        nome="Água Branca",
        uf="PI",
        id_uf="22",
        capital=False,
        ddd="86",
        regiao="Nordeste",
        micro=("2202", "Médio Parnaíba Piauiense"),
        meso=("2203", "Centro-Norte Piauiense"),
        reg_imediata=("220007", "Amarante - Água Branca - Regeneração"),
        reg_intermediaria=("2204", "Teresina"),
        rm=("", ""),
        centroide="POINT(-42.6280034656636 -5.91391372089572)",
    ),
    dict(
        id="2500106",
        id_rf="1901",
        nome="Água Branca",
        uf="PB",
        id_uf="25",
        capital=False,
        ddd="83",
        regiao="Nordeste",
        micro=("2504", "Serra do Teixeira"),
        meso=("2505", "Sertão Paraibano"),
        reg_imediata=("250006", "Patos"),
        reg_intermediaria=("2506", "Patos"),
        rm=("", ""),
        centroide="POINT(-37.6623099941963 -7.47069089510134)",
    ),
]

_NOME_UF = {"ES": "Espírito Santo", "AL": "Alagoas", "PI": "Piauí", "PB": "Paraíba"}


def gerar_municipio_bd(saida_dir: Path) -> Path:
    linhas = []
    for m in _MUNICIPIOS_BD:
        micro_id, micro_nome = m["micro"]
        meso_id, meso_nome = m["meso"]
        reg_imed_id, reg_imed_nome = m["reg_imediata"]
        reg_inter_id, reg_inter_nome = m["reg_intermediaria"]
        rm_id, rm_nome = m["rm"]
        linhas.append(
            [
                m["id"],
                m["id"][:6],
                "",
                m["id_rf"],
                "",
                m["nome"],
                "true" if m["capital"] else "false",
                "",
                "",
                "",
                reg_imed_id,
                reg_imed_nome,
                reg_inter_id,
                reg_inter_nome,
                micro_id,
                micro_nome,
                meso_id,
                meso_nome,
                rm_id,
                rm_nome,
                m["ddd"],
                m["id_uf"],
                m["uf"],
                _NOME_UF[m["uf"]],
                m["regiao"],
                "false",
                m["centroide"],
            ]
        )
    return gerar_csv_gz_bd(saida_dir, "municipio", CABECALHO_MUNICIPIO_BD, linhas)


CABECALHO_CNAE2_BD = [
    "subclasse",
    "descricao_subclasse",
    "classe",
    "descricao_classe",
    "grupo",
    "descricao_grupo",
    "divisao",
    "descricao_divisao",
    "secao",
    "descricao_secao",
    "indicador_cnae_2_0",
    "indicador_cnae_2_1",
    "indicador_cnae_2_2",
    "indicador_cnae_2_3",
]

# subclasse, descricao_subclasse, descricao_classe, descricao_grupo,
# descricao_divisao, secao, descricao_secao
_CNAE2_BD = [
    (
        "4741500",
        "Comercio varejista de tintas, vernizes e materiais para pintura",
        "Comercio varejista de tintas e materiais para pintura",
        "Comercio varejista de material de construcao",
        "Comercio varejista, exceto de\nveiculos automotores e motocicletas",
        "G",
        "Comercio; reparacao de veiculos automotores e motocicletas",
    ),
    (
        "2071100",
        "Fabricacao de tintas, vernizes, esmaltes e lacas",
        "Fabricacao de tintas, vernizes, esmaltes e lacas",
        "Fabricacao de produtos quimicos diversos",
        "Fabricacao de produtos quimicos",
        "C",
        "Industrias de transformacao",
    ),
    (
        "4679601",
        "Comercio atacadista de tintas, vernizes e materiais para pintura",
        "Comercio atacadista de madeira e materiais de construcao",
        "Comercio atacadista especializado em outros produtos",
        "Comercio por atacado, exceto veiculos automotores e motocicletas",
        "G",
        "Comercio; reparacao de veiculos automotores e motocicletas",
    ),
    (
        "4679699",
        "Comercio atacadista de materiais de construcao em geral",
        "Comercio atacadista de madeira e materiais de construcao",
        "Comercio atacadista especializado em outros produtos",
        "Comercio por atacado, exceto veiculos automotores e motocicletas",
        "G",
        "Comercio; reparacao de veiculos automotores e motocicletas",
    ),
    (
        "4711302",
        "Comercio varejista de mercadorias em geral - minimercados e mercearias",
        "Comercio varejista de mercadorias em geral, com predominancia de produtos alimenticios",
        "Comercio varejista nao especializado",
        "Comercio varejista",
        "G",
        "Comercio; reparacao de veiculos automotores e motocicletas",
    ),
    (
        "4744099",
        "Comercio varejista de materiais de construcao em geral",
        "Comercio varejista de material de construcao",
        "Comercio varejista de material de construcao",
        "Comercio varejista, exceto de\nveiculos automotores e motocicletas",
        "G",
        "Comercio; reparacao de veiculos automotores e motocicletas",
    ),
    (
        "0111301",
        "Cultivo de arroz",
        "Cultivo de cereais",
        "Producao de lavouras temporarias",
        "Agricultura, pecuaria e servicos relacionados",
        "A",
        "Agricultura, pecuaria, producao florestal, pesca e aquicultura",
    ),
]


def gerar_cnae2_bd(saida_dir: Path) -> Path:
    linhas = []
    for subclasse, desc_sub, desc_classe, desc_grupo, desc_divisao, secao, desc_secao in _CNAE2_BD:
        classe = subclasse[:5]
        grupo = subclasse[:3]
        divisao = subclasse[:2]
        linhas.append(
            [
                subclasse,
                desc_sub,
                classe,
                desc_classe,
                grupo,
                desc_grupo,
                divisao,
                desc_divisao,
                secao,
                desc_secao,
                "true",
                "true",
                "true",
                "true",
            ]
        )
    return gerar_csv_gz_bd(saida_dir, "cnae_2", CABECALHO_CNAE2_BD, linhas)


CABECALHO_POPULACAO_BD = ["ano", "sigla_uf", "id_municipio", "populacao"]

_POPULACAO_BD = [
    ("2024", "ES", "3202207", "20000"),
    ("2024", "ES", "3203205", "180000"),
    ("2024", "ES", "3200607", "100000"),
    ("2024", "ES", "3205002", "520000"),
    ("2024", "ES", "3205309", "330000"),
    ("2024", "AL", "2700102", "10000"),
    ("2024", "PI", "2200202", "10000"),
    ("2024", "PB", "2500106", "10000"),
    ("2023", "ES", "3202207", "19000"),
]


def gerar_populacao_bd(saida_dir: Path) -> Path:
    return gerar_csv_gz_bd(
        saida_dir, "populacao", CABECALHO_POPULACAO_BD, [list(r) for r in _POPULACAO_BD]
    )


CABECALHO_PIB_BD = [
    "id_municipio",
    "ano",
    "pib",
    "impostos_liquidos",
    "va",
    "va_agropecuaria",
    "va_industria",
    "va_servicos",
    "va_adespss",
]

# id_municipio, pib (R$), aproximadamente proporcional à população 2024
_PIB_BD = [
    ("3202207", "350000", "35000", "315000", "20000", "150000", "100000", "45000"),
    ("3203205", "2800000", "280000", "2520000", "400000", "900000", "1000000", "220000"),
    ("3200607", "1700000", "170000", "1530000", "80000", "900000", "450000", "100000"),
    ("3205002", "9500000", "950000", "8550000", "50000", "4000000", "3800000", "700000"),
    ("3205309", "18000000", "1800000", "16200000", "5000", "3000000", "11000000", "2195000"),
    ("2700102", "150000", "15000", "135000", "30000", "40000", "50000", "15000"),
    ("2200202", "140000", "14000", "126000", "35000", "35000", "45000", "11000"),
    ("2500106", "145000", "14500", "130500", "32000", "38000", "47000", "13500"),
]


def gerar_pib_bd(saida_dir: Path) -> Path:
    linhas = [
        [id_municipio, "2021", pib, impostos, va, agro, industria, servicos, adespss]
        for id_municipio, pib, impostos, va, agro, industria, servicos, adespss in _PIB_BD
    ]
    return gerar_csv_gz_bd(saida_dir, "pib", CABECALHO_PIB_BD, linhas)


# incremento: enriquecimento_bd
CABECALHO_CENSO_2022_BD = [
    "id_municipio",
    "sigla_uf",
    "domicilios",
    "populacao",
    "area",
    "taxa_alfabetizacao",
    "idade_mediana",
    "razao_sexo",
    "indice_envelhecimento",
    "populacao_indigena",
    "populacao_indigena_terra_indigena",
    "populacao_quilombola",
    "populacao_quilombola_territorio_quilombola",
]

# id_municipio, uf, domicílios, população, área (km²), taxa de alfabetização, idade mediana,
# razão de sexo, índice de envelhecimento, indígena, indígena em TI (quilombolas: 0 em todos).
# Fundão = valores reais do Censo 2022; os demais são sintéticos. Água Branca/PI (2200202) fica
# de fora de propósito: denominadores ausentes devem virar NULL.
_CENSO_2022_BD = [
    ("3202207", "ES", "6715", "17951", "287", "0.93371", "37", "97.67", "67.68", "30", "0"),
    ("3203205", "ES", "55000", "166786", "3502", "0.9391", "34", "96.9", "40.5", "100", "0"),
    ("3200607", "ES", "40000", "94765", "1436", "0.94", "35", "99", "45.1", "2500", "2400"),
    ("3205002", "ES", "160000", "520653", "553", "0.97", "34", "94.5", "49.2", "400", "0"),
    ("3205309", "ES", "140000", "322869", "93", "0.98", "40", "85.9", "100.4", "300", "0"),
    ("2700102", "AL", "3300", "9873", "454", "0.62", "28", "98", "25", "0", "0"),
    ("2500106", "PB", "3200", "9000", "236", "0.7", "30", "97", "30", "0", "0"),
]


def gerar_censo_2022_bd(saida_dir: Path) -> Path:
    return gerar_csv_gz_bd(
        saida_dir,
        "censo_2022_municipio",
        CABECALHO_CENSO_2022_BD,
        [[*r, "0", "0"] for r in _CENSO_2022_BD],
    )


# incremento: enriquecimento_bd
CABECALHO_REGIAO_METROPOLITANA_BD = [
    "nome_regiao_metropolitana",
    "tipo",
    "subcategoria_metropolitana",
    "id_municipio",
    "sigla_uf",
    "legislacao",
    "data_legislacao",
    "geometria",
]

_GEOMETRIA_SINTETICA = "POLYGON((-40.5 -20.5, -40.0 -20.5, -40.0 -19.8, -40.5 -19.8, -40.5 -20.5))"

# Fundão, Serra e Vitória pertencem à RM Grande Vitória (como nos dados reais, que ainda trazem
# Vila Velha, Cariacica, Guarapari e Viana — fora do cenário). Linhares e Aracruz ficam de fora.
_REGIAO_METROPOLITANA_BD = [
    ("RM Grande Vitória", "RM", "", "3202207", "ES", "Lei Complementar 318", "2005-01-18"),
    ("RM Grande Vitória", "RM", "", "3205002", "ES", "Lei Complementar 318", "2005-01-18"),
    ("RM Grande Vitória", "RM", "", "3205309", "ES", "Lei Complementar 318", "2005-01-18"),
]


def gerar_regiao_metropolitana_bd(saida_dir: Path) -> Path:
    return gerar_csv_gz_bd(
        saida_dir,
        "regiao_metropolitana_2017",
        CABECALHO_REGIAO_METROPOLITANA_BD,
        [[*r, _GEOMETRIA_SINTETICA] for r in _REGIAO_METROPOLITANA_BD],
    )


# incremento: enriquecimento_bd
CABECALHO_VIZINHANCA_BD = ["ano", "id_municipio_1", "id_municipio_2"]

# Ano mais recente = 2020. Propositalmente "sujo": pares só em uma direção (o modelo simetriza),
# uma linha duplicada, um autopar e um par de 2019 que não deve aparecer.
# Vizinhos conformados de Fundão: Aracruz e Serra.
_VIZINHANCA_BD = [
    ("2019", "3202207", "3203205"),
    ("2020", "3202207", "3200607"),
    ("2020", "3202207", "3200607"),
    ("2020", "3202207", "3205002"),
    ("2020", "3205002", "3205309"),
    ("2020", "3205309", "3205002"),
    ("2020", "3200607", "3203205"),
    ("2020", "3203205", "3203205"),
]


def gerar_vizinhanca_bd(saida_dir: Path) -> Path:
    return gerar_csv_gz_bd(
        saida_dir,
        "vizinhanca_municipio",
        CABECALHO_VIZINHANCA_BD,
        [list(r) for r in _VIZINHANCA_BD],
    )


# ---------------------------------------------------------------------------
# IBGE — respostas SIDRA (JSON) e planilhas REGIC 2018 (xlsx), como `rfb_pipeline.ibge` as lê
# incremento: enriquecimento_ibge
# ---------------------------------------------------------------------------

XLSX_DATE_TIME = (2020, 7, 31, 16, 30, 0)
_MUNICIPIOS_IBGE = (
    "3202207",
    "3203205",
    "3200607",
    "3205002",
    "3205309",
    "2700102",
    "2200202",
    "2500106",
)  # noqa: E501
_PERIODO_CEMPRE = "2024"
_TOTAL_CEMPRE = "117897"
# Categorias da classificação 12762 (CNAE 2.0) com os ids reais da SIDRA. `20.5` é um grupo que a
# SIDRA marca como nível 4: não é classe (`NN.NN-N`) e não pode ser baixado (contaria em dobro).
_CATEGORIAS_CEMPRE = [
    ("117897", "Total", "11867005"),
    ("116833", "01.11-3 Cultivo de cereais", "47099"),
    ("117065", "20.5 Fabricação de defensivos agrícolas e desinfestantes domissanitários", "579"),
    ("117066", "20.51-7 Fabricação de defensivos agrícolas", "295"),
    ("117073", "20.71-1 Fabricação de tintas, vernizes, esmaltes e lacas", "1894"),
    ("117299", "35.11-5 Geração de energia elétrica", "14887"),
    ("117363", "G Comércio; reparação de veículos automotores e motocicletas", "3319852"),
    (
        "117424",
        "46.79-6 Comércio atacadista especializado de materiais de construção não especificados anteriormente e de materiais de construção em geral",  # noqa: E501
        "16511",
    ),
    ("117438", "47 Comércio varejista", "2291295"),
    (
        "117440",
        "47.11-3 Comércio varejista de mercadorias em geral, com predominância de produtos alimentícios - hipermercados e supermercados",  # noqa: E501
        "55169",
    ),
    ("117452", "47.4 Comércio varejista de material de construção", "293179"),
    ("117453", "47.41-5 Comércio varejista de tintas e materiais para pintura", "15716"),
    (
        "117456",
        "47.44-0 Comércio varejista de ferragens, madeira e materiais de construção",
        "231116",
    ),
]
_CLASSES_CEMPRE = ["116833", "117066", "117073", "117299", "117424", "117440", "117453", "117456"]
_VARIAVEIS_CEMPRE = (
    ("706", "1020"),
    ("707", "45"),
    ("708", "45"),
    ("662", "40"),
)  # (variável, unidade)
# (município, categoria) -> (unidades locais, pessoal ocupado, assalariado, salários em mil R$);
# o que não está aqui é `-` (zero absoluto). Fundão: Total e 47.41-5 reais (CEMPRE 2024); Serra e
# Vitória em 47.41-5: as 4 variáveis reais. `X` = sigilo, `...` = não disponível, `..` = não se
# aplica.
_VALORES_CEMPRE = {
    ("3202207", "117897"): ("1054", "5125", "3831", "96332"),
    ("3202207", "117456"): ("20", "90", "60", "1700"),
    ("3202207", "117440"): ("4", "60", "55", "1500"),
    ("3203205", "117897"): ("6200", "41000", "33000", "1150000"),
    ("3203205", "117453"): ("12", "X", "X", "X"),
    ("3203205", "116833"): ("5", "12", "8", "..."),
    ("3200607", "117897"): ("3900", "30500", "26000", "980000"),
    ("3200607", "117453"): ("3", "X", "X", "X"),
    ("3200607", "117299"): ("1", "..", "..", ".."),
    ("3205002", "117897"): ("16000", "160000", "140000", "5100000"),
    ("3205002", "117453"): ("33", "196", "167", "6358"),
    ("3205002", "117073"): ("2", "X", "X", "X"),
    ("3205002", "117424"): ("10", "80", "70", "2500"),
    ("3205309", "117897"): ("21000", "290000", "250000", "11200000"),
    ("3205309", "117453"): ("25", "164", "144", "5892"),
    ("3205309", "117424"): ("8", "50", "45", "1800"),
    ("2700102", "117897"): ("150", "900", "600", "15000"),
    ("2200202", "117897"): ("220", "1500", "1100", "26000"),
    ("2500106", "117897"): ("90", "600", "400", "9000"),
}
# Renda do Censo 2022 (tabela 10295): moradores, média e mediana do rendimento domiciliar per capita
# (R$). Fundão e Vitória reais; demais sintéticos; Água Branca/PI com mediana `...`.
_RENDA_2022 = {
    "3202207": ("17961", "1406.78", "1040.00"),
    "3203205": ("166000", "1650.20", "1100.00"),
    "3200607": ("94500", "1580.35", "1050.00"),
    "3205002": ("518000", "1720.10", "1200.00"),
    "3205309": ("321973", "3351.64", "1750.00"),
    "2700102": ("19300", "520.40", "330.00"),
    "2200202": ("16800", "610.15", "..."),
    "2500106": ("9800", "540.90", "350.00"),
}

_CABECALHO_REGIC_HIERARQUIA = [
    "coduf", "siguf", "UF", "Grande Região", "codmun", "Município", "Categoria", "codap",
    "Arranjo Populacional", "codcid", "Hierarquia", "Hierarquia 2", "Hierarquia 3",
    "Hierarquia - grupo", "Múltiplas Subordinações",
    "Região de influência - vínculação imediata consolidada", "Região de influência 1",
    "Região de influência 2", "Região de influência 3", "Região de influência 4",
]  # fmt: skip
_AP_VITORIA = "Arranjo Populacional de Vitória/ES"
_INTEGRANTE_VITORIA = (
    "Metrópole (1C) - Município integrante do Arranjo Populacional de Vitória/ES",
    "Metrópole - Integrante de Arranjo Populacional",
    "1C - Integrante de Arranjo Populacional",
    "1 - Metrópole - Integrante de Arranjo Populacional",
)
_VINCULO_VITORIA = (f"{_AP_VITORIA} - Metrópole (1C)", _AP_VITORIA, None, None, None)
# Linhas reais da REGIC 2018 (aba `Hierarquia e região`) dos municípios das fixtures.
_REGIC_HIERARQUIA = [
    (
        "22",
        "PI",
        "Piauí",
        "Nordeste",
        "2200202",
        "Água Branca",
        "Município isolado",
        None,
        None,
        "2200202",
        "Centro de Zona A (4A)",
        "Centro de Zona A",
        "4A",
        "4 - Centro de Zona",
        1,
        "Arranjo Populacional de Teresina/PI - Capital Regional A (2A)",
        "Arranjo Populacional de Teresina/PI",
        None,
        None,
        None,
    ),
    (
        "25",
        "PB",
        "Paraíba",
        "Nordeste",
        "2500106",
        "Água Branca",
        "Município isolado",
        None,
        None,
        "2500106",
        "Centro Local (5)",
        "Centro Local",
        "5",
        "5 - Centro Local",
        2,
        "Arranjo Populacional de Patos/PB - Centro Sub-Regional A (3A); Tabira (PE) - Centro de Zona B (4B)",  # noqa: E501
        "Arranjo Populacional de Patos/PB",
        "Tabira (PE)",
        None,
        None,
    ),
    (
        "27",
        "AL",
        "Alagoas",
        "Nordeste",
        "2700102",
        "Água Branca",
        "Município isolado",
        None,
        None,
        "2700102",
        "Centro Local (5)",
        "Centro Local",
        "5",
        "5 - Centro Local",
        1,
        "Delmiro Gouveia (AL) - Centro Sub-Regional B (3B)",
        "Delmiro Gouveia (AL)",
        None,
        None,
        None,
    ),
    (
        "32",
        "ES",
        "Espírito Santo",
        "Sudeste",
        "3200607",
        "Aracruz",
        "Município isolado",
        None,
        None,
        "3200607",
        "Centro Sub-Regional B (3B)",
        "Centro Sub-Regional B",
        "3B",
        "3 - Centro Sub-Regional",
        1,
        *_VINCULO_VITORIA,
    ),
    (
        "32",
        "ES",
        "Espírito Santo",
        "Sudeste",
        "3202207",
        "Fundão",
        "Arranjo Populacional",
        "3205309",
        _AP_VITORIA,
        "3205309",
        *_INTEGRANTE_VITORIA,
        1,
        *_VINCULO_VITORIA,
    ),
    (
        "32",
        "ES",
        "Espírito Santo",
        "Sudeste",
        "3203205",
        "Linhares",
        "Município isolado",
        None,
        None,
        "3203205",
        "Centro Sub-Regional A (3A)",
        "Centro Sub-Regional A",
        "3A",
        "3 - Centro Sub-Regional",
        1,
        *_VINCULO_VITORIA,
    ),
    (
        "32",
        "ES",
        "Espírito Santo",
        "Sudeste",
        "3205002",
        "Serra",
        "Arranjo Populacional",
        "3205309",
        _AP_VITORIA,
        "3205309",
        *_INTEGRANTE_VITORIA,
        1,
        *_VINCULO_VITORIA,
    ),
    (
        "32",
        "ES",
        "Espírito Santo",
        "Sudeste",
        "3205309",
        "Vitória",
        "Arranjo Populacional",
        "3205309",
        _AP_VITORIA,
        "3205309",
        *_INTEGRANTE_VITORIA,
        1,
        *_VINCULO_VITORIA,
    ),
]

_CABECALHO_REGIC_ATRACAO = [
    "CODMUN", "NOME_MUN", "HIERAR_MUN", "INT_ARR", "HIERAR_CID", "NOME_HIERAR_CID", "COD_ARR",
    "NOME_ARR", "POP2018", "IA", *(f"IA_Q{i}" for i in range(1, 11)),
]  # fmt: skip
_HIERAR_INTEGRANTE = "Município integrante do Arranjo Populacional de Vitória/ES - Metrópole (1C)"
# (município, nome, hierarquia do município, integra arranjo?, código e nome da hierarquia da
# cidade, população 2018, IA, IA_Q1..IA_Q10) — valores reais arredondados.
_REGIC_ATRACAO = [
    (
        "3205309",
        "Vitória",
        _HIERAR_INTEGRANTE,
        "SIM",
        "1C",
        "Metrópole",
        358267,
        1315461.60605983,
        (
            817684.7,
            978672.3,
            1030736.68,
            1766212.5,
            919613.63,
            913435.43,
            949170.18,
            2957936.63,
            2537671.75,
            281181.21,
        ),
    ),
    (
        "3205002",
        "Serra",
        _HIERAR_INTEGRANTE,
        "SIM",
        "1C",
        "Metrópole",
        507598,
        81584.2276825206,
        (
            95136.28,
            84504.37,
            96407.45,
            140490.93,
            45170.03,
            169616.4,
            117383.92,
            0,
            7407.47,
            59725.43,
        ),
    ),
    (
        "3203205",
        "Linhares",
        "Centro Subregional A (3A)",
        "NÃO",
        "3A",
        "Centro Subregional A",
        170364,
        85805.2174216831,
        (
            84418.9,
            174779.93,
            132565.7,
            64871.64,
            105233.94,
            132475.9,
            83798.07,
            0,
            18143.43,
            61764.66,
        ),
    ),
    (
        "3202207",
        "Fundão",
        _HIERAR_INTEGRANTE,
        "SIM",
        "1C",
        "Metrópole",
        21061,
        4580.80969216309,
        (0, 0, 0, 0, 0, 0, 0, 0, 0, 45808.0969216309),
    ),
    (
        "3200607",
        "Aracruz",
        "Centro Subregional B (3B)",
        "NÃO",
        "3B",
        "Centro Subregional B",
        99305,
        14592.5630619228,
        (21580.27, 20749.57, 18241.58, 3510.17, 37738.63, 14338.82, 19267.52, 0, 824.33, 9674.75),
    ),
    (
        "2700102",
        "Água Branca",
        "Centro Local (5)",
        "NÃO",
        "5",
        "Centro Local",
        20162,
        1259.49666666667,
        (0, 0, 0, 0, 0, 4015.63, 7412.87, 0, 0, 0),
    ),
    (
        "2500106",
        "Água Branca",
        "Centro Local (5)",
        "NÃO",
        "5",
        "Centro Local",
        10161,
        2605.34054189714,
        (1217.83, 1217.83, 0, 0, 0, 8684.45, 6881.97, 0, 0, 6272.5),
    ),
    (
        "2200202",
        "Água Branca",
        "Centro de Zona A (4A)",
        "NÃO",
        "4A",
        "Centro de Zona A",
        17349,
        25331.0973656827,
        (54645.47, 45399.87, 23399.92, 866.97, 22901.27, 26959.01, 25712.77, 0, 0, 35194.04),
    ),
    # pseudo-destino "Outros / Não circula jornal" (no real: `CODMUN` 0, sem hierarquia e população)
    (
        "0",
        "Outros / Não circula jornal",
        None,
        None,
        None,
        None,
        None,
        2379854.69235186,
        (
            1394139.13,
            1324777.16,
            1172195.21,
            1125295.7,
            1621141.86,
            1750225.56,
            2065193.26,
            959544.76,
            33672992.69,
            0,
        ),
    ),  # fmt: skip
]

_CABECALHO_REGIC_LIGACOES = [
    "ID", "UF_ORIGEM", "MUN_ORIGEM", "MUN_OR", "NOME_ORIGEM", "POP2018_O", "COD_ARR_O",
    "NOME_ARR_O", "HIERAR_MUN_O", "HIERAR_CID", "NOME_HIERAR_CID", "UF_DESTINO", "MUN_DESTINO",
    "MUN_DEST", "NOME_DESTINO", "POP2018_D", "COD_ARR_D", "NOME_ARR_D", "HIERAR_MUN_D",
    "HIERAR_CID_D", "NOME_HIERAR_CID_D", *(f"Q{i}" for i in range(1, 11)),
    *(f"IA_Q{i}" for i in range(1, 11)), "PERC_LIG", "IA", "X_ORIGEM", "Y_ORIGEM", "X_DESTINO",
    "Y_DESTINO",
]  # fmt: skip
_SEDES = {  # longitude, latitude da sede municipal
    "3202207": (-40.4067, -19.9329), "3203205": (-40.0683, -19.398),
    "3200607": (-40.2648, -19.825), "3205002": (-40.3079, -20.1209),
    "3205309": (-40.3128, -20.3155),
}  # fmt: skip
# (origem, destino, Q1..Q10, PERC_LIG) — reais. Fundão -> Serra e Fundão -> Vitória são os oráculos
# (Q1 vestuário e calçados, Q2 móveis e eletroeletrônicos). Vitória não tem ligação de origem.
_REGIC_LIGACOES = [
    (
        "3202207",
        "3205309",
        (
            30,
            38.3333333333333,
            26.6666666666667,
            43.3333333333333,
            18.3333333333333,
            30,
            25,
            100,
            0,
            20.5,
        ),
        31.1,
    ),
    (
        "3202207",
        "3205002",
        (
            46.6666666666667,
            45,
            11.6666666666667,
            28.3333333333333,
            31.6666666666667,
            20,
            15,
            0,
            0,
            30.2,
        ),
        25.4,
    ),
    (
        "3202207",
        "3200607",
        (
            16.6666666666667,
            16.6666666666667,
            28.3333333333333,
            16.6666666666667,
            23.3333333333333,
            18.3333333333333,
            8.33333333333333,
            0,
            0,
            12.5675012272951,
        ),
        15.1,
    ),
    (
        "3202207",
        "3203205",
        (0, 0, 0, 0, 0, 0, 0, 0, 6.66666666666667, 0),
        0.666666666666667,
    ),
    (
        "3203205",
        "3205309",
        (
            65,
            88.3333333333333,
            60,
            73.3333333333333,
            80,
            71.6666666666667,
            70,
            100,
            100,
            11.2757731958763,
        ),
        71.9,
    ),
    (
        "3200607",
        "3205309",
        (60, 58.3333333333333, 60, 80, 60, 40, 60, 100, 86.6666666666667, 21.2719298245614),
        62.6,
    ),
    (
        "3200607",
        "3205002",
        (
            13.3333333333333,
            13.3333333333333,
            5,
            5,
            6.66666666666667,
            36.6666666666667,
            40,
            0,
            0,
            9.75877192982456,
        ),
        12.9,
    ),
    # Destino `0` = "Outros / Não circula jornal": a parcela dos deslocamentos para lugares não
    # listados (no real, 3.888 origens têm essa linha; Fundão não). Sintético, no formato do real.
    ("3203205", "0", (0, 3.33, 0, 3.33, 8.33, 6.67, 8.33, 0, 6.67, 0), 0.0366666666666667),
]
_DESTINO_OUTROS = "0"
_NOME_OUTROS = "Outros / Não circula jornal"


def _escrever_json_ibge(saida_dir: Path, nome: str, registros: list[dict]) -> Path:
    destino = saida_dir / "ibge" / f"{nome}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(registros, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destino


def gerar_cempre_categorias_ibge(saida_dir: Path) -> Path:
    """Resposta SIDRA `/t/9528/n1/all/v/706/p/last 1/c12762/all/f/a/h/n` (com nomes)."""
    registros = [
        {
            "NC": "1",
            "NN": "Brasil",
            "MC": "1020",
            "MN": "Unidades",
            "V": total,
            "D1C": "1",
            "D1N": "Brasil",
            "D2C": "706",
            "D2N": "Número de unidades locais",
            "D3C": _PERIODO_CEMPRE,
            "D3N": _PERIODO_CEMPRE,
            "D4C": categoria,
            "D4N": nome,
        }  # fmt: skip
        for categoria, nome, total in _CATEGORIAS_CEMPRE
    ]
    return _escrever_json_ibge(saida_dir, "cempre_categorias_cnae", registros)


def gerar_cempre_municipio_ibge(saida_dir: Path) -> Path:
    """Respostas SIDRA `/t/9528/n6/all/v/706,707,708,662/p/2024/c12762/<cats>/f/c/h/n`, juntas."""
    registros = []
    for categoria in [*_CLASSES_CEMPRE, _TOTAL_CEMPRE]:
        for municipio in _MUNICIPIOS_IBGE:
            valores = _VALORES_CEMPRE.get((municipio, categoria), ("-", "-", "-", "-"))
            for (variavel, unidade), valor in zip(_VARIAVEIS_CEMPRE, valores, strict=True):
                registros.append(
                    {
                        "NC": "6",
                        "MC": unidade,
                        "V": valor,
                        "D1C": municipio,
                        "D2C": variavel,
                        "D3C": _PERIODO_CEMPRE,
                        "D4C": categoria,
                    }  # fmt: skip
                )
    return _escrever_json_ibge(saida_dir, "cempre_municipio_cnae", registros)


def gerar_renda_ibge(saida_dir: Path) -> Path:
    """Resposta SIDRA `/t/10295/n6/all/v/13604,13431,13534/p/2022/c2/6794/c86/95251/c58/95253`."""
    registros = []
    for municipio in _MUNICIPIOS_IBGE:
        moradores, media, mediana = _RENDA_2022[municipio]
        for variavel, unidade, valor in (
            ("13604", "45", moradores),
            ("13431", "38", media),
            ("13534", "38", mediana),
        ):
            registros.append(
                {
                    "NC": "6",
                    "MC": unidade,
                    "V": valor,
                    "D1C": municipio,
                    "D2C": variavel,
                    "D3C": "2022",
                    "D4C": "6794",
                    "D5C": "95251",
                    "D6C": "95253",
                }  # fmt: skip
            )
    return _escrever_json_ibge(saida_dir, "renda_censo_2022_municipio", registros)


def _xlsx_deterministico(abas: list[tuple[str, list[str], list[tuple]]]) -> bytes:
    """xlsx com as `abas` (nome, cabeçalho, linhas), regravado com datas fixas (bytes estáveis)."""
    livro = openpyxl.Workbook()
    livro.remove(livro.active)
    for nome, cabecalho, linhas in abas:
        aba = livro.create_sheet(nome)
        aba.append(cabecalho)
        for linha in linhas:
            aba.append(list(linha))
    momento = datetime(*XLSX_DATE_TIME)
    livro.properties.created = momento
    livro.properties.modified = momento
    bruto = io.BytesIO()
    livro.save(bruto)
    return _rezipar(bruto.getvalue())


_RE_DATA_CORE = re.compile(rb"(<dcterms:(?:created|modified)[^>]*>)[^<]*(</dcterms:)")


def _rezipar(conteudo_zip: bytes) -> bytes:
    """Regrava um xlsx com ordem, datas das entradas e datas de `docProps/core.xml` fixas.

    O `save()` do openpyxl grava a hora atual nas entradas do zip e em `dcterms:modified` (ignora
    `properties.modified`): sem isto, duas gerações em segundos diferentes dariam bytes diferentes.
    """
    fixa = datetime(*XLSX_DATE_TIME).strftime("%Y-%m-%dT%H:%M:%SZ").encode("ascii")
    saida = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(conteudo_zip)) as origem:
        with zipfile.ZipFile(saida, "w", compression=zipfile.ZIP_DEFLATED) as destino:
            for nome in sorted(origem.namelist()):
                conteudo = origem.read(nome)
                if nome == "docProps/core.xml":
                    conteudo = _RE_DATA_CORE.sub(rb"\g<1>" + fixa + rb"\g<2>", conteudo)
                info = zipfile.ZipInfo(nome, date_time=XLSX_DATE_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o600 << 16
                destino.writestr(info, conteudo)
    return saida.getvalue()


def _linha_ligacao(origem: str, destino: str, qs: tuple, perc_lig: float) -> tuple:
    atracao = {m[0]: m for m in _REGIC_ATRACAO}

    def lado(municipio: str) -> tuple:
        _, nome, hierar_mun, integra, hierar_cid, nome_hierar, pop, *_ = atracao[municipio]
        arranjo = ("3205309", _AP_VITORIA) if integra == "SIM" else (None, None)
        return (municipio, int(municipio), nome, pop, *arranjo, hierar_mun, hierar_cid, nome_hierar)

    o = lado(origem)
    if destino == _DESTINO_OUTROS:  # como no real: sem UF, população, hierarquia nem sede
        uf_d, sede_d = None, (None, None)
        d = ("0", 0, _NOME_OUTROS, None, None, None, None, None, None)
    else:
        uf_d, d, sede_d = "ES", lado(destino), _SEDES[destino]
    pop_o = o[3]
    ias = [round(q * pop_o / 100, 4) for q in qs]
    return (
        int(origem + destino), "ES", *o[:9], uf_d, *d[:9], *qs, *ias, perc_lig,
        round(perc_lig * pop_o / 100, 4), *_SEDES[origem], *sede_d,
    )  # fmt: skip


def gerar_regic_ibge(saida_dir: Path) -> tuple[Path, Path]:
    """`REGIC2018_Municipios_Hierarquia_e_regiao.xlsx` e o zip de ligações e atração (geoftp)."""
    pasta = saida_dir / "ibge"
    pasta.mkdir(parents=True, exist_ok=True)
    notas = ("Notas, fonte e dicionário", ["Notas:"], [("Fixture sintética (REGIC 2018).",)])
    hierarquia = pasta / "REGIC2018_Municipios_Hierarquia_e_regiao.xlsx"
    hierarquia.write_bytes(
        _xlsx_deterministico(
            [("Hierarquia e região", _CABECALHO_REGIC_HIERARQUIA, _REGIC_HIERARQUIA), notas]
        )
    )
    atracao = _xlsx_deterministico(
        [
            (
                "BD_MUN_QUEST",
                _CABECALHO_REGIC_ATRACAO,
                [
                    (
                        int(m[0]),
                        *m[1:6],
                        *(("3205309", _AP_VITORIA) if m[3] == "SIM" else (None, None)),
                        m[6],
                        m[7],
                        *m[8],
                    )
                    for m in _REGIC_ATRACAO
                ],  # fmt: skip
            ),
            ("Descrição de variáveis", ["VARIÁVEL", "DESCRIÇÃO"], [("CODMUN", "Geocódigo")]),
        ]
    )
    ligacoes = _xlsx_deterministico(
        [
            (
                "BD_LIG_MUN_QUEST",
                _CABECALHO_REGIC_LIGACOES,
                [_linha_ligacao(o, d, qs, p) for o, d, qs, p in _REGIC_LIGACOES],
            ),
            ("Descrição das variáveis ", ["VARIÁVEL", "DESCRIÇÃO"], [("Q1", "Vestuário")]),
        ]
    )
    pacote = pasta / "REGIC2018_Municipios_Ligacoes_e_atracao_xlsx.zip"
    with zipfile.ZipFile(pacote, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for nome, conteudo in (
            ("REGIC2018_Quest_Atracao_Municipios.xlsx", atracao),
            ("REGIC2018_Quest_Ligacoes_entre_Municipios.xlsx", ligacoes),
        ):
            info = zipfile.ZipInfo(nome, date_time=XLSX_DATE_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, conteudo)
    return hierarquia, pacote


def main(argv: list[str] | None = None) -> int:
    analisador = argparse.ArgumentParser(description="Gera fixtures sintéticas RFB/BD/IBGE.")
    analisador.add_argument(
        "--saida",
        type=Path,
        default=Path("tests/fixtures/generated"),
        help="Diretório de saída (default: tests/fixtures/generated)",
    )
    argumentos = analisador.parse_args(argv)

    gerar_fixtures(argumentos.saida)
    print(f"fixtures geradas em {argumentos.saida}")
    return 0


COLUNAS_ESTABELECIMENTOS = [
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
]

COLUNAS_EMPRESAS = [
    "cnpj_raiz",
    "razao_social",
    "natureza_jur",
    "qualificacao_resp",
    "capital_soc",
    "porte",
    "ente_fed_resp",
]

COLUNAS_SIMPLES = [
    "cnpj_raiz",
    "opcao_simples",
    "dat_opcao_simples",
    "dat_exclusao_simples",
    "opcao_mei",
    "dat_opcao_mei",
    "dat_exclusao_mei",
]

COLUNAS_DOMINIO = ["codigo", "descricao"]


def construir_linhas_estabelecimentos(mes: str = MES_REFERENCIA) -> list[list[str]]:
    linhas = []
    for est in _ESTABELECIMENTOS_RAW:
        if mes == MES_ANTERIOR and est["id"] == ID_ESTABELECIMENTO_AUSENTE_NO_ANTERIOR:
            continue
        dv_correto = calcular_dv_cnpj(est["raiz"] + est["ordem"])
        dv = dv_invalido(dv_correto) if est["id"] == "L" else dv_correto
        sufixo = "_anterior" if mes == MES_ANTERIOR and "situacao_anterior" in est else ""
        situacao, mot_situacao = est["situacao" + sufixo], est["mot_situacao" + sufixo]
        dat_situacao = est["dat_situacao" + sufixo]
        if dat_situacao is None:
            dat_situacao = est["dat_inicio"]
        linhas.append(
            [
                est["raiz"],
                est["ordem"],
                dv,
                est["matriz_filial"],
                est["nome_fantasia"],
                situacao,
                dat_situacao,
                mot_situacao,
                est["cidade_exterior"],
                est["pais"],
                est["dat_inicio"],
                est["cnae_principal"],
                est["cnaes_secundarios"],
                "RUA",
                "CENTRAL",
                "100",
                "",
                "CENTRO",
                "29000000",
                est["uf"],
                est["municipio"],
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ]
        )
    return linhas


# Linha "fantasma" (R4-05, Fix 7): repete a raiz de B sem razão social, natureza 0000 e porte,
# qualificação e capital zerados, como a raiz 08314885 do extrato real de 2026-09 (B8). O staging
# e a paridade ficam com uma linha por raiz (`empresa_preferida_por_raiz`); sem a dedup, o
# estabelecimento B sairia duplicado. Vem antes da linha boa: a escolha não depende da ordem.
RAIZ_EMPRESA_FANTASMA = "22222222"
LINHA_EMPRESA_FANTASMA = [RAIZ_EMPRESA_FANTASMA, "", "0000", "00", "0,00", "00", ""]


def construir_linhas_empresas() -> list[list[str]]:
    linhas = [list(LINHA_EMPRESA_FANTASMA)]
    for raiz, (razao_social, natureza_jur, porte, capital_soc) in _EMPRESA_POR_RAIZ.items():
        linhas.append([raiz, razao_social, natureza_jur, "49", capital_soc, porte, ""])
    return linhas


def construir_linhas_simples() -> list[list[str]]:
    linhas = []
    for raiz in _EMPRESA_POR_RAIZ:
        optante_mei = raiz in _RAIZES_MEI
        opcao = "S" if optante_mei else "N"
        linhas.append(
            [
                raiz,
                "S",
                "20070701",
                "00000000",
                opcao,
                "20070701" if optante_mei else "00000000",
                "00000000",
            ]
        )
    return linhas


def _gerar_rfb_mes(saida_dir: Path, mes: str, tag: str, date_time: tuple) -> None:
    def zip_rfb(nome_zip: str, nome_interno: str, colunas: list[str], linhas: list) -> None:
        gerar_zip_rfb(saida_dir, nome_zip, nome_interno, colunas, linhas, mes, date_time)

    # Domínios RFB
    dominios = [
        ("Cnaes.zip", "CNAECSV", DOMINIO_CNAES),
        ("Municipios.zip", "MUNICCSV", DOMINIO_MUNICIPIOS),
        ("Naturezas.zip", "NATJUCSV", DOMINIO_NATUREZAS),
        ("Motivos.zip", "MOTICSV", DOMINIO_MOTIVOS),
        ("Paises.zip", "PAISCSV", DOMINIO_PAISES),
        ("Qualificacoes.zip", "QUALSCSV", DOMINIO_QUALIFICACOES),
    ]
    for nome_zip, sufixo, dominio in dominios:
        zip_rfb(
            nome_zip,
            f"F.K03200$Z.{tag}.{sufixo}",
            COLUNAS_DOMINIO,
            [list(row) for row in dominio],
        )

    # Empresas / estabelecimentos / simples
    zip_rfb(
        "Empresas0.zip",
        f"K3241.K03200Y0.{tag}.EMPRECSV",
        COLUNAS_EMPRESAS,
        construir_linhas_empresas(),
    )
    zip_rfb(
        "Estabelecimentos0.zip",
        f"K3241.K03200Y0.{tag}.ESTABELE",
        COLUNAS_ESTABELECIMENTOS,
        construir_linhas_estabelecimentos(mes),
    )
    zip_rfb(
        "Simples.zip",
        f"F.K03200$W.SIMPLES.CSV.{tag}",
        COLUNAS_SIMPLES,
        construir_linhas_simples(),
    )


def gerar_fixtures(saida_dir: Path) -> None:
    _gerar_rfb_mes(saida_dir, MES_REFERENCIA, DATA_REFERENCIA_TAG, ZIP_DATE_TIME)
    _gerar_rfb_mes(saida_dir, MES_ANTERIOR, DATA_REFERENCIA_TAG_ANTERIOR, ZIP_DATE_TIME_ANTERIOR)

    # Base dos Dados
    gerar_municipio_bd(saida_dir)
    gerar_cnae2_bd(saida_dir)
    gerar_populacao_bd(saida_dir)
    gerar_pib_bd(saida_dir)
    gerar_censo_2022_bd(saida_dir)  # incremento: enriquecimento_bd
    gerar_regiao_metropolitana_bd(saida_dir)  # incremento: enriquecimento_bd
    gerar_vizinhanca_bd(saida_dir)  # incremento: enriquecimento_bd

    # IBGE — incremento: enriquecimento_ibge
    gerar_cempre_categorias_ibge(saida_dir)
    gerar_cempre_municipio_ibge(saida_dir)
    gerar_renda_ibge(saida_dir)
    gerar_regic_ibge(saida_dir)


if __name__ == "__main__":
    raise SystemExit(main())
