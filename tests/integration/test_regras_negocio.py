"""`rfb regras` contra as fixtures (ADR-0020): sai com 0 mesmo com violações, cobre o catálogo e só
traz contagens. Um segundo cenário injeta uma violação de cada regra numa cópia do warehouse e
confere que todas as analyses a detectam.

Roda sobre o `warehouse.duckdb` de `RAIZ_DADOS` (exportado por `make ci`).
"""

from __future__ import annotations

import importlib.util
import os
import re
from pathlib import Path

import duckdb
import pytest

from rfb_pipeline.cli import main
from rfb_pipeline.regras import (
    PADRAO_ANALISES,
    SUBPASTA_ANALISES,
    cruzar_com_catalogo,
    ler_catalogo,
)
from rfb_pipeline.relatorio import DIR_TRANSFORM, compilar_analises, executar_analises

pytestmark = pytest.mark.skipif(
    "RAIZ_DADOS" not in os.environ, reason="rode via make ci (exporta RAIZ_DADOS)"
)

RAIZ = Path(__file__).resolve().parents[2]

# Violações esperadas por regra nas fixtures de 2026-09 (consultadas no gold/raw do `make ci`):
# RN-05: raiz MEI 11111111 tem a matriz A e a filial O, as duas ativas; RN-11: Q baixado com
# `dat_situacao` 00000000; RN-17: DV de L adulterado; RN-24: par repetido na vizinhança publicada.
VIOLACOES_FIXTURES = {f"RN-{n:02d}": 0 for n in range(1, 25)} | {
    "RN-05": 1,
    "RN-11": 1,
    "RN-17": 1,
    "RN-24": 1,
}
_RE_RESUMO = re.compile(r"^\| \[(RN-\d{2})\]\([^)]*\) \| [^|]+ \| [^|]+ \| ([\d.]+) \| ([\d.]+) \|")


@pytest.fixture(scope="module")
def relatorio(tmp_path_factory: pytest.TempPathFactory) -> str:
    saida = tmp_path_factory.mktemp("regras") / "relatorio-regras.md"
    assert main(["regras", "--saida", str(saida), "--target", "ci"]) == 0  # mesmo com violações
    return saida.read_text(encoding="utf-8")


def _resumo(texto: str) -> dict[str, tuple[int, int]]:
    linhas = {}
    for linha in texto.splitlines():
        achado = _RE_RESUMO.match(linha)
        if achado:
            avaliados, violacoes = (int(v.replace(".", "")) for v in achado.group(2, 3))
            linhas[achado.group(1)] = (avaliados, violacoes)
    return linhas


def test_regras_sai_com_zero_mesmo_com_violacoes(relatorio: str) -> None:
    assert any(v for _, v in _resumo(relatorio).values()), "as fixtures têm regras violadas"
    assert "**24** regras avaliadas: **20** sem violação e **4** com violação." in relatorio


def test_toda_regra_do_catalogo_esta_no_relatorio_e_vice_versa(relatorio: str) -> None:
    assert set(_resumo(relatorio)) == set(ler_catalogo())


def test_violacoes_por_regra_batem_com_as_fixtures(relatorio: str) -> None:
    assert {rid: v for rid, (_, v) in _resumo(relatorio).items()} == VIOLACOES_FIXTURES
    assert "| mais de um não baixado | 1 | 1 | 100,00 % |" in relatorio  # RN-05: filial O ativa
    assert "| BAIXADA | 6 | 1 | 16,67 % |" in relatorio  # RN-11: Q


def _fixtures_sinteticas():
    caminho = RAIZ / "scripts" / "gerar_fixtures.py"
    spec = importlib.util.spec_from_file_location("gerar_fixtures_regras", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_relatorio_nao_traz_identificador_nem_nome(relatorio: str) -> None:
    """ADR-0008 (mutação b): sem sequência de 11 ou 14 dígitos, CNPJ, razão social ou fantasia."""
    assert not re.search(r"(?<![0-9])([0-9]{11}|[0-9]{14})(?![0-9])", relatorio)
    fixtures = _fixtures_sinteticas()
    nomes = {razao.strip(" \\") for razao, *_ in fixtures._EMPRESA_POR_RAIZ.values()}
    nomes |= {e["nome_fantasia"] for e in fixtures._ESTABELECIMENTOS_RAW if e["nome_fantasia"]}
    raizes = {e["raiz"] for e in fixtures._ESTABELECIMENTOS_RAW}
    for proibido in nomes | raizes:
        assert proibido not in relatorio, proibido


def test_relatorio_e_deterministico(relatorio: str, tmp_path: Path) -> None:
    saida = tmp_path / "b.md"
    assert main(["regras", "--saida", str(saida), "--target", "ci"]) == 0
    assert saida.read_text(encoding="utf-8") == relatorio


# ---------------------------------------------------------------------------- detecção

# Uma violação de cada regra, em raízes novas (9xxxxxxx), longe do estudo de caso. Linhas novas
# copiam uma linha existente e trocam só as colunas da regra (`select * replace`).
_BASE_EST = "(select * from int_estabelecimentos__enriquecidos order by cnpj_completo limit 1)"
_BASE_STG = "(select * from stg_rfb__estabelecimentos order by cnpj_completo limit 1)"
_BASE_SIMPLES = "(select * from stg_rfb__simples order by cnpj_raiz limit 1)"
_BASE_EMPRESA = "(select * from stg_rfb__empresas order by cnpj_raiz limit 1)"


def _est(cnpj: str, **colunas: str) -> str:
    trocas = {"cnpj_completo": f"'{cnpj}'", "cnpj_raiz": f"'{cnpj[:8]}'", **colunas}
    replace = ", ".join(f"{v} as {k}" for k, v in trocas.items())
    tabela = "int_estabelecimentos__enriquecidos"
    return f"insert into {tabela} select * replace ({replace}) from {_BASE_EST}"


def _replace(tabela: str, base: str, **colunas: str) -> str:
    replace = ", ".join(f"{v} as {k}" for k, v in colunas.items())
    return f"insert into {tabela} select * replace ({replace}) from {base}"


INJECOES = {
    "RN-01": [_est("90000001000101", cnae_principal="'9999999'")],
    "RN-02": [_est("90000002000101", cnaes_secundarios_lista="['9999999']")],
    "RN-03": [_est("90000003000101", cnaes_secundarios_lista="[cnae_principal]")],
    "RN-04": [_est("90000004000101", cnaes_secundarios_lista="['4741500', '4741500']")],
    "RN-05": [
        _replace("stg_rfb__simples", _BASE_SIMPLES, cnpj_raiz="'90000005'", opcao_mei="true",
                 opcao_simples="true"),
        _est("90000005000101", matriz_filial_codigo="1", situacao_codigo="2"),
        _est("90000005000202", matriz_filial_codigo="2", situacao_codigo="2"),
    ],
    "RN-06": [_replace("stg_rfb__simples", _BASE_SIMPLES, cnpj_raiz="'90000006'", opcao_mei="true",
                       opcao_simples="false")],
    "RN-07": [
        _replace("stg_rfb__simples", _BASE_SIMPLES, cnpj_raiz="'90000007'", opcao_mei="true",
                 opcao_simples="true"),
        _replace("stg_rfb__empresas", _BASE_EMPRESA, cnpj_raiz="'90000007'", porte_codigo="5",
                 natureza_juridica_codigo="'2062'"),
    ],
    "RN-08": [],  # coberta pela empresa da RN-07 (natureza 2062)
    "RN-09": [_replace("stg_rfb__simples", _BASE_SIMPLES, cnpj_raiz="'90000009'",
                       dat_opcao_simples="date '2020-01-01'",
                       dat_exclusao_simples="date '2019-01-01'")],
    "RN-10": [_replace("stg_rfb__estabelecimentos", _BASE_STG, cnpj_completo="'90000010000101'",
                       situacao_codigo="2", motivo_situacao_codigo="'01'")],
    "RN-11": [_est("90000011000101", situacao_codigo="4", dat_situacao="null::date")],
    "RN-12": [_est("90000012000101", dat_inicio_atividade="date '2020-01-02'",
                   dat_situacao="date '2020-01-01'")],
    "RN-13": [_est("90000013000101", dat_inicio_atividade="_data_referencia + 1")],
    "RN-14": [
        _est("90000014000101", matriz_filial_codigo="1", situacao_codigo="8"),
        _est("90000014000202", matriz_filial_codigo="2", situacao_codigo="2"),
    ],
    "RN-15": [_replace("stg_rfb__estabelecimentos", _BASE_STG, cnpj_completo="'90000015000101'",
                       situacao_especial="'X'", dat_situacao_especial="null::date")],
    "RN-16": [
        _est("90000016000101", matriz_filial_codigo="1"),
        _est("90000016000202", matriz_filial_codigo="1"),
    ],
    "RN-17": [_est("9000001700019Z")],
    "RN-18": [_est("90000018000101", tem_empresa="false")],
    "RN-19": [_est("90000019000101", municipio_rfb_codigo="'0000'")],
    "RN-20": [_replace("stg_rfb__empresas", _BASE_EMPRESA, cnpj_raiz="'90000020'",
                       natureza_juridica_codigo="'2062'", ente_federativo_responsavel="'BAHIA'")],
    "RN-21": [_replace("stg_rfb__empresas", _BASE_EMPRESA, cnpj_raiz="'90000021'",
                       capital_social="-1")],
    "RN-22": [f"insert into stg_rfb__simples select * from {_BASE_SIMPLES}"],
    "RN-23": [
        "insert into agg_empresas select * from agg_empresas limit 1",
        "insert into mart_dinamica_mercado select * from mart_dinamica_mercado limit 1",
        "insert into mart_sobrevivencia_coorte select * from mart_sobrevivencia_coorte limit 1",
    ],
    "RN-24": [
        "insert into excecoes_conhecidas_municipio "
        "select * from excecoes_conhecidas_municipio limit 1"
    ],
}  # fmt: skip


@pytest.fixture(scope="module")
def sqls() -> dict[str, str]:
    raiz = Path(os.environ["RAIZ_DADOS"])
    return compilar_analises(
        DIR_TRANSFORM, raiz, "ci", subpasta=SUBPASTA_ANALISES, padrao=PADRAO_ANALISES
    )


def _violacoes(warehouse: Path, sqls: dict[str, str]) -> dict[str, int]:
    linhas = cruzar_com_catalogo(ler_catalogo(), executar_analises(warehouse, sqls))
    return {rid: sum(x.violacoes for x in ls) for rid, ls in linhas.items()}


def test_cada_regra_detecta_a_violacao_injetada(sqls: dict[str, str], tmp_path: Path) -> None:
    """Cópia das relações lidas pelas analyses (catálogo `warehouse`), uma violação por regra."""
    assert set(INJECOES) == set(ler_catalogo())
    origem = Path(os.environ["RAIZ_DADOS"]) / "warehouse.duckdb"
    copia = tmp_path / "warehouse.duckdb"  # o nome do arquivo é o catálogo do SQL compilado
    relacoes = sorted(
        {r for sql in sqls.values() for r in re.findall(r'"warehouse"\."main"\."(\w+)"', sql)}
    )
    with duckdb.connect(str(copia)) as con:
        con.execute(f"attach '{origem}' as origem (read_only)")
        for relacao in relacoes:
            con.execute(f"create table main.{relacao} as select * from origem.main.{relacao}")
        con.execute("detach origem")
    antes = _violacoes(copia, sqls)
    assert antes == VIOLACOES_FIXTURES
    with duckdb.connect(str(copia)) as con:
        for comandos in INJECOES.values():
            for comando in comandos:
                con.execute(comando)
    depois = _violacoes(copia, sqls)
    sem_deteccao = sorted(rid for rid in antes if depois[rid] <= antes[rid])
    assert sem_deteccao == []
