"""Gerador determinístico de fixtures sintéticas RFB/CNPJ e Base dos Dados.

Reproduz o formato real dos arquivos publicados no WebDAV da RFB para o mês
2026-09 (zips com um único arquivo interno, latin-1, separador `;`, todos os
campos entre aspas, fim de linha LF) e os csv.gz da Base dos Dados
(API downloadTable: UTF-8, vírgula, cabecalho). Duas execuções produzem bytes
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
import zipfile
from pathlib import Path

MES_REFERENCIA = "2026-09"
DATA_REFERENCIA_TAG = "D60912"  # último dígito do ano (2026 -> 6) + 0912
ZIP_DATE_TIME = (2026, 9, 12, 0, 0, 0)

# Segundo mês (spec §"Segundo mês"): idêntico a 2026-09, sem a linha O e com nomes internos D60810.
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
]

# cnpj_raiz -> (razao_social, natureza_jur, porte, capital_soc) — nível empresa.
# 14 raízes (A-N); O reaproveita a raiz de A (11111111).
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


def main(argv: list[str] | None = None) -> int:
    analisador = argparse.ArgumentParser(description="Gera fixtures sintéticas RFB/BD.")
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
        dat_situacao = est["dat_situacao"]
        if dat_situacao is None:
            dat_situacao = est["dat_inicio"]
        linhas.append(
            [
                est["raiz"],
                est["ordem"],
                dv,
                est["matriz_filial"],
                est["nome_fantasia"],
                est["situacao"],
                dat_situacao,
                est["mot_situacao"],
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


def construir_linhas_empresas() -> list[list[str]]:
    linhas = []
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


if __name__ == "__main__":
    raise SystemExit(main())
