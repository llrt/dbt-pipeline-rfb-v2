"""`rfb regras` contra as fixtures (ADR-0020): sai com 0 mesmo com violações, cobre o catálogo e só
traz contagens. Um segundo cenário injeta, caso a caso, violações e casos de borda numa cópia do
warehouse e confere o delta exato por quebra de cada regra (RRN-04).

Roda sobre o `warehouse.duckdb` de `RAIZ_DADOS` (exportado por `make ci`).
"""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
from pathlib import Path

import duckdb
import pytest

from rfb_pipeline.cli import main
from rfb_pipeline.regras import (
    PADRAO_ANALISES,
    SUBPASTA_ANALISES,
    ler_catalogo,
    padronizar_linhas,
    traz_identificador,
)
from rfb_pipeline.relatorio import DIR_TRANSFORM, compilar_analises, executar_analises

pytestmark = pytest.mark.skipif(
    "RAIZ_DADOS" not in os.environ, reason="rode via make ci (exporta RAIZ_DADOS)"
)

RAIZ = Path(__file__).resolve().parents[2]

# (avaliados, violações) por regra nas fixtures de 2026-09, consultados no gold/raw do `make ci`
# (RRN-04). Violações: RN-05, a raiz MEI 11111111 tem a matriz A e a filial O, as duas ativas;
# RN-11, Q baixado com `dat_situacao` 00000000; RN-17, DV de L adulterado; RN-24, par repetido na
# vizinhança publicada; RN-26 e RN-28, as datas de opção sintéticas (2007-07-01 em todas as raízes
# do Simples): opção pelo MEI antes do SIMEI nas raízes 11111111 e 33333333 e opção antes do início
# da matriz em 12 raízes do Simples e nas 2 do MEI. Na RN-24, o universo não conta
# `dq_historico_testes`, que cresce a cada teste novo do build, e países e qualificações entram só
# no mês do relatório (2 linhas cada; as de 2026-08 ficam de fora).
UNIVERSO_E_VIOLACOES_FIXTURES = {
    "RN-01": (18, 0), "RN-02": (2, 0), "RN-03": (2, 0), "RN-04": (1, 0), "RN-05": (2, 1),
    "RN-06": (2, 0), "RN-07": (2, 0), "RN-08": (2, 0), "RN-09": (0, 0), "RN-10": (18, 0),
    "RN-11": (7, 1), "RN-12": (16, 0), "RN-13": (51, 0), "RN-14": (0, 0), "RN-15": (18, 0),
    "RN-16": (16, 0), "RN-17": (18, 1), "RN-18": (18, 0), "RN-19": (18, 0), "RN-20": (16, 0),
    "RN-21": (16, 0), "RN-22": (16, 0), "RN-23": (54, 0), "RN-24": (24, 1), "RN-25": (16, 0),
    "RN-26": (2, 2), "RN-27": (0, 0), "RN-28": (17, 14), "RN-29": (2, 0),
}  # fmt: skip
_HISTORICO_TESTES = "observabilidade.dq_historico_testes"
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
    assert "**29** regras avaliadas: **23** sem violação e **6** com violação." in relatorio


def test_toda_regra_do_catalogo_esta_no_relatorio_e_vice_versa(relatorio: str) -> None:
    assert set(_resumo(relatorio)) == set(ler_catalogo())


def test_violacoes_por_regra_batem_com_as_fixtures(relatorio: str) -> None:
    violacoes = {rid: v for rid, (_, v) in UNIVERSO_E_VIOLACOES_FIXTURES.items()}
    assert {rid: v for rid, (_, v) in _resumo(relatorio).items()} == violacoes
    secao_rn05 = relatorio.split("### RN-05")[1].split("###")[0]
    assert "| mais de um não baixado | 1 | 1 | 100,00 % |" in secao_rn05  # filial O ativa
    assert "| um | 1 | 0 | 0 % |" in secao_rn05  # raiz MEI 33333333
    assert "| BAIXADA | 6 | 1 | 16,67 % |" in relatorio  # RN-11: Q


def _fixtures_sinteticas():
    caminho = RAIZ / "scripts" / "gerar_fixtures.py"
    spec = importlib.util.spec_from_file_location("gerar_fixtures_regras", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _celulas_de_quebra(texto: str) -> list[str]:
    """Células de quebra das tabelas de "Regras com violação" (as três últimas são contagens)."""
    secao = texto.split("## Regras com violação")[1].split("## Interpretação")[0]
    linhas = [x for x in secao.splitlines() if x.startswith("| ") and not x.startswith("| ---")]
    return [c.strip() for x in linhas for c in x.strip("|").split("|")[:-3]]


def test_relatorio_nao_traz_identificador_nem_nome(relatorio: str) -> None:
    """ADR-0008 (mutação b, RRN-01): sem CPF, CNPJ ou raiz, com ou sem máscara, nem nome."""
    assert not re.search(r"(?<![0-9])([0-9]{11}|[0-9]{14})(?![0-9])", relatorio)
    assert not re.search(r"[0-9]{2}\.[0-9]{3}\.[0-9]{3}(/[0-9A-Z]{4}-[0-9]{2})?", relatorio)
    assert not re.search(r"[0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]{2}", relatorio)
    celulas = _celulas_de_quebra(relatorio)
    assert "mais de um não baixado" in celulas
    assert [c for c in celulas if traz_identificador(c)] == []
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

# Cada caso injeta linhas numa cópia nova do warehouse, em raízes novas (9xxxxxxx), longe do
# estudo de caso, e confere o delta **exato** (avaliados, violações) por quebra das regras listadas
# (RRN-04). Linhas novas copiam uma linha existente e trocam só as colunas da regra
# (`select * replace`). A base de Estabelecimentos é a matriz ATIVA 11111111000191 (início e
# situação em 2022-10-15, CNAE 4741500, sem secundários); a do Simples, a raiz 11111111 (opção pelo
# Simples e pelo MEI em 2007-07-01, sem exclusão); a de Empresas, a mesma raiz (natureza 2135, porte
# MICRO, capital 1.000, sem ente). Extrato de 2026-09-12.
_BASE_EST = "(select * from int_estabelecimentos__enriquecidos order by cnpj_completo limit 1)"
_BASE_STG = "(select * from stg_rfb__estabelecimentos order by cnpj_completo limit 1)"
_BASE_SIMPLES = "(select * from stg_rfb__simples order by cnpj_raiz limit 1)"
_BASE_EMPRESA = "(select * from stg_rfb__empresas order by cnpj_raiz limit 1)"
_SOCIEDADE_LIMITADA = "2062 Sociedade Empresária Limitada"


def _est(cnpj: str, **colunas: str) -> str:
    trocas = {"cnpj_completo": f"'{cnpj}'", "cnpj_raiz": f"'{cnpj[:8]}'", **colunas}
    replace = ", ".join(f"{v} as {k}" for k, v in trocas.items())
    tabela = "int_estabelecimentos__enriquecidos"
    return f"insert into {tabela} select * replace ({replace}) from {_BASE_EST}"


def _replace(tabela: str, base: str, **colunas: str) -> str:
    replace = ", ".join(f"{v} as {k}" for k, v in colunas.items())
    return f"insert into {tabela} select * replace ({replace}) from {base}"


def _simples(raiz: str, **colunas: str) -> str:
    return _replace("stg_rfb__simples", _BASE_SIMPLES, cnpj_raiz=f"'{raiz}'", **colunas)


def _empresa(raiz: str, **colunas: str) -> str:
    return _replace("stg_rfb__empresas", _BASE_EMPRESA, cnpj_raiz=f"'{raiz}'", **colunas)


def _stg(cnpj: str, **colunas: str) -> str:
    return _replace("stg_rfb__estabelecimentos", _BASE_STG, cnpj_completo=f"'{cnpj}'", **colunas)


Delta = dict[str, dict[tuple[str, ...], tuple[int, int]]]

# (caso, comandos, {regra: {quebra: (Δ avaliados, Δ violações)}}). A mutação que cada caso de borda
# mata está entre parênteses (RRN, tabela "Mutações").
CASOS: list[tuple[str, list[str], Delta]] = [
    ("CNAE principal fora do domínio", [_est("90000001000101", cnae_principal="'9999999'")],
     {"RN-01": {("ATIVA",): (1, 1)}}),
    ("CNAE secundário fora do domínio",
     [_est("90000002000101", cnaes_secundarios_lista="['9999999']")],
     {"RN-02": {("ATIVA",): (1, 1)}}),
    ("baixado com secundário igual ao principal (M10)",
     [_est("90000003000101", cnaes_secundarios_lista="[cnae_principal]", situacao_codigo="8")],
     {"RN-03": {("BAIXADA",): (1, 1)}}),
    ("secundário repetido",
     [_est("90000004000101", cnaes_secundarios_lista="['4741500', '4741500']")],
     {"RN-04": {("ATIVA",): (1, 1)}}),
    ("MEI com matriz e filial ativas",
     [_simples("90000005"), _est("90000005000101"),
      _est("90000005000202", matriz_filial_codigo="2")],
     {"RN-05": {("mais de um não baixado",): (1, 1)}}),
    ("MEI com filial baixada (M2)",
     [_simples("90000105"), _est("90000105000101"),
      _est("90000105000202", matriz_filial_codigo="2", situacao_codigo="8")],
     {"RN-05": {("mais de um, no máximo um não baixado",): (1, 0)}}),
    ("MEI com um ATIVO e outro de situação nula",
     [_simples("90000205"), _est("90000205000101"),
      _est("90000205000202", matriz_filial_codigo="2", situacao_codigo="null")],
     {"RN-05": {("indeterminado (situação desconhecida)",): (1, 0)}}),
    ("MEI sem opção pelo Simples", [_simples("90000006", opcao_simples="false")],
     {"RN-06": {(): (1, 1)}}),
    ("MEI de porte DEMAIS", [_simples("90000007"), _empresa("90000007", porte_codigo="5")],
     {"RN-07": {("DEMAIS",): (1, 1)}}),
    ("MEI sociedade limitada",
     [_simples("90000008"), _empresa("90000008", natureza_juridica_codigo="'2062'")],
     {"RN-08": {(_SOCIEDADE_LIMITADA,): (1, 1)}, "RN-29": {(_SOCIEDADE_LIMITADA,): (1, 1)}}),
    ("MEI EIRELI: não é sociedade",
     [_simples("90000108"), _empresa("90000108", natureza_juridica_codigo="'2305'")],
     {"RN-08": {("2305 Empresa Individual de Responsabilidade Limitada (de Natureza "
                 "Empresária)",): (1, 1)},
      "RN-29": {("2305 Empresa Individual de Responsabilidade Limitada (de Natureza "
                 "Empresária)",): (1, 0)}}),
    ("MEI com natureza fora do domínio",
     [_simples("90000208"), _empresa("90000208", natureza_juridica_codigo="'9999'")],
     {"RN-08": {("9999 (fora do domínio)",): (1, 1)}}),
    ("exclusão do Simples antes da opção",
     [_simples("90000009", dat_opcao_simples="date '2020-01-01'",
               dat_exclusao_simples="date '2019-01-01'")],
     {"RN-09": {("Simples Nacional",): (1, 1)}}),
    ("exclusão no mesmo dia da opção, nos dois regimes (fronteira)",
     [_simples("90000109", dat_opcao_simples="date '2020-01-01'",
               dat_exclusao_simples="date '2020-01-01'", dat_opcao_mei="date '2020-01-01'",
               dat_exclusao_mei="date '2020-01-01'")],
     {"RN-09": {("Simples Nacional",): (1, 0), ("MEI",): (1, 0)}}),
    ("ATIVO com motivo de baixa",
     [_stg("90000010000101", situacao_codigo="2", motivo_situacao_codigo="'01'")],
     {"RN-10": {("ATIVA",): (1, 1)}}),
    ("INAPTO com motivo nulo (M4)",
     [_stg("90000110000101", situacao_codigo="4", motivo_situacao_codigo="null")],
     {"RN-10": {("INAPTA",): (1, 1)}}),
    ("INAPTO sem data", [_est("90000011000101", situacao_codigo="4", dat_situacao="null::date")],
     {"RN-11": {("INAPTA",): (1, 1)}}),
    ("NULO sem data (M9)",
     [_est("90000111000101", situacao_codigo="1", dat_situacao="null::date")],
     {"RN-11": {("NULA",): (1, 1)}}),
    ("situação antes do início",
     [_est("90000012000101", dat_inicio_atividade="date '2020-01-02'",
           dat_situacao="date '2020-01-01'")],
     {"RN-12": {("ATIVA",): (1, 1)}}),
    ("situação no mesmo dia do início (fronteira)",
     [_est("90000112000101", dat_inicio_atividade="date '2020-01-01'",
           dat_situacao="date '2020-01-01'")],
     {"RN-12": {("ATIVA",): (1, 0)}}),
    ("início dois dias depois do extrato",
     [_est("90000013000101", dat_inicio_atividade="_data_referencia + 2")],
     {"RN-13": {("início de atividade", "além do limite"): (1, 1),
                ("situação cadastral", "até a data do extrato"): (1, 0)}}),
    ("início exatamente na data do extrato (fronteira)",
     [_est("90000313000101", dat_inicio_atividade="_data_referencia")],
     {"RN-13": {("início de atividade", "até a data do extrato"): (1, 0),
                ("situação cadastral", "até a data do extrato"): (1, 0)}}),
    ("situação no dia seguinte ao extrato",
     [_est("90000113000101", dat_situacao="_data_referencia + 1")],
     {"RN-13": {("início de atividade", "até a data do extrato"): (1, 0),
                ("situação cadastral", "dia seguinte ao extrato"): (1, 0)}}),
    ("opção pelo Simples em 1º/1/2027 (fronteira) e pelo MEI depois (M3)",
     [_simples("90000213", dat_opcao_simples="date '2027-01-01'",
               dat_opcao_mei="date '2027-01-02'")],
     {"RN-13": {("opção pelo Simples", "opção até 1º de janeiro seguinte"): (1, 0),
                ("opção pelo MEI", "além do limite"): (1, 1)}}),
    ("matriz baixada, filial ativa",
     [_est("90000014000101", situacao_codigo="8"),
      _est("90000014000202", matriz_filial_codigo="2")],
     {"RN-14": {("ATIVA",): (1, 1)}}),
    ("matriz baixada, filial nula (M1)",
     [_est("90000114000101", situacao_codigo="8"),
      _est("90000114000202", matriz_filial_codigo="2", situacao_codigo="1")],
     {"RN-14": {("NULA",): (1, 0)}}),
    ("situação especial sem data",
     [_stg("90000015000101", situacao_especial="'X'", dat_situacao_especial="null::date")],
     {"RN-15": {("ATIVA",): (1, 1)}}),
    ("duas matrizes", [_est("90000016000101"), _est("90000016000202")],
     {"RN-16": {("2 ou mais",): (1, 1)}}),
    ("raiz só com filial (M5)", [_est("90000116000202", matriz_filial_codigo="2")],
     {"RN-16": {("0",): (1, 1)}}),
    ("CNPJ alfanumérico com DV inválido", [_est("9000001700019Z")],
     {"RN-17": {("ATIVA",): (1, 1)}}),
    ("DV inválido numa raiz com DV válido (M6)",
     [_est("90000117000168"), _est("90000117000200", matriz_filial_codigo="2")],
     {"RN-17": {("ATIVA",): (2, 1)}}),
    ("estabelecimento sem empresa", [_est("90000018000101", tem_empresa="false")],
     {"RN-18": {("ATIVA",): (1, 1)}}),
    ("município fora do domínio", [_est("90000019000101", municipio_rfb_codigo="'0000'")],
     {"RN-19": {("ATIVA",): (1, 1)}}),
    ("ente federativo numa sociedade",
     [_empresa("90000020", natureza_juridica_codigo="'2062'",
               ente_federativo_responsavel="'BAHIA'")],
     {"RN-20": {("demais grupos", _SOCIEDADE_LIMITADA): (1, 1)}}),
    ("capital negativo", [_empresa("90000021", capital_social="-1")],
     {"RN-21": {("MICRO",): (1, 1)}}),
    ("Simples duplicado", [f"insert into stg_rfb__simples select * from {_BASE_SIMPLES}"],
     {"RN-22": {(): (1, 1)}}),
    ("marts duplicados",
     ["insert into agg_empresas select * from agg_empresas limit 1",
      "insert into mart_dinamica_mercado select * from mart_dinamica_mercado limit 1",
      "insert into mart_sobrevivencia_coorte select * from mart_sobrevivencia_coorte limit 1"],
     {"RN-23": {("agg_empresas",): (1, 1), ("mart_dinamica_mercado",): (1, 1),
                ("mart_sobrevivencia_coorte",): (1, 1)}}),
    ("exceção de município duplicada",
     ["insert into excecoes_conhecidas_municipio "
      "select * from excecoes_conhecidas_municipio limit 1"],
     {"RN-24": {("excecoes_conhecidas_municipio",): (1, 1)}}),
    ("opção pelo Simples antes de 1º/7/2007 e no dia",
     [_simples("90000025", dat_opcao_simples="date '2007-06-30'"),
      _simples("90000125", dat_opcao_simples="date '2007-07-01'")],
     {"RN-25": {(): (2, 1)}}),
    ("opção pelo MEI antes de 1º/7/2009 e no dia",
     [_simples("90000026", dat_opcao_mei="date '2009-06-30'"),
      _simples("90000126", dat_opcao_mei="date '2009-07-01'")],
     {"RN-26": {(): (2, 1)}}),
    ("filial que começa depois da baixa da matriz",
     [_est("90000027000101", situacao_codigo="8", dat_situacao="date '2020-01-01'"),
      _est("90000027000202", matriz_filial_codigo="2", dat_inicio_atividade="date '2021-01-01'"),
      _est("90000027000303", matriz_filial_codigo="2", dat_inicio_atividade="date '2019-01-01'")],
     {"RN-27": {("BAIXADA",): (2, 1)}}),
    ("filial que começa no dia da baixa da matriz (fronteira)",
     [_est("90000127000101", situacao_codigo="8", dat_situacao="date '2020-01-01'"),
      _est("90000127000202", matriz_filial_codigo="2", dat_inicio_atividade="date '2020-01-01'")],
     {"RN-27": {("BAIXADA",): (1, 0)}}),
    ("opção pelo Simples antes do início da matriz",
     [_simples("90000028", dat_opcao_simples="date '2020-01-01'", dat_opcao_mei="null::date"),
      _est("90000028000101", dat_inicio_atividade="date '2021-01-01'")],
     {"RN-28": {("Simples Nacional",): (1, 1)}}),
    ("opção no dia do início da matriz, nos dois regimes (fronteira)",
     [_simples("90000128", dat_opcao_simples="date '2021-01-01'",
               dat_opcao_mei="date '2021-01-01'"),
      _est("90000128000101", dat_inicio_atividade="date '2021-01-01'")],
     {"RN-28": {("Simples Nacional",): (1, 0), ("MEI",): (1, 0)}}),
]  # fmt: skip


@pytest.fixture(scope="module")
def sqls() -> dict[str, str]:
    raiz = Path(os.environ["RAIZ_DADOS"])
    return compilar_analises(
        DIR_TRANSFORM, raiz, "ci", subpasta=SUBPASTA_ANALISES, padrao=PADRAO_ANALISES
    )


@pytest.fixture(scope="module")
def copia_base(sqls: dict[str, str], tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Cópia das relações lidas pelas analyses (catálogo `warehouse`, o nome do arquivo)."""
    origem = Path(os.environ["RAIZ_DADOS"]) / "warehouse.duckdb"
    copia = tmp_path_factory.mktemp("base") / "warehouse.duckdb"
    relacoes = sorted(
        {r for sql in sqls.values() for r in re.findall(r'"warehouse"\."main"\."(\w+)"', sql)}
    )
    with duckdb.connect(str(copia)) as con:
        con.execute(f"attach '{origem}' as origem (read_only)")
        for relacao in relacoes:
            con.execute(f"create table main.{relacao} as select * from origem.main.{relacao}")
        con.execute("detach origem")
    return copia


def _por_quebra(warehouse: Path, sqls: dict[str, str]) -> dict[str, dict[tuple, tuple]]:
    """`{regra: {quebra: (avaliados, violações)}}`, com a guarda de privacidade de `rfb regras`."""
    resultado = {}
    for analise, tabela in executar_analises(warehouse, sqls).items():
        rid, linhas = padronizar_linhas(analise, tabela)
        resultado[rid] = {tuple(v for _, v in x.quebra): (x.avaliados, x.violacoes) for x in linhas}
    return resultado


def test_copia_base_reproduz_as_fixtures(copia_base: Path, sqls: dict[str, str]) -> None:
    por_quebra = _por_quebra(copia_base, sqls)
    por_quebra["RN-24"].pop((_HISTORICO_TESTES,))
    totais = {
        rid: (sum(a for a, _ in q.values()), sum(v for _, v in q.values()))
        for rid, q in por_quebra.items()
    }
    assert totais == UNIVERSO_E_VIOLACOES_FIXTURES


def test_todo_caso_cobre_regras_do_catalogo() -> None:
    cobertas = {rid for _, _, esperado in CASOS for rid in esperado}
    assert cobertas == set(ler_catalogo())


@pytest.mark.parametrize(("caso", "comandos", "esperado"), CASOS, ids=[c[0] for c in CASOS])
def test_cada_regra_detecta_a_violacao_injetada(
    caso: str, comandos: list[str], esperado: Delta, copia_base: Path, sqls: dict[str, str],
    tmp_path: Path,
) -> None:  # fmt: skip
    """Regra a regra (RRN-04): o delta por quebra é exatamente o esperado, nem mais nem menos."""
    catalogo = ler_catalogo()
    alvo = {catalogo[rid].analise: sqls[catalogo[rid].analise] for rid in esperado}
    copia = tmp_path / "warehouse.duckdb"
    shutil.copyfile(copia_base, copia)
    antes = _por_quebra(copia, alvo)
    with duckdb.connect(str(copia)) as con:
        for comando in comandos:
            con.execute(comando)
    depois = _por_quebra(copia, alvo)
    for rid, quebras in esperado.items():
        delta = {}
        for quebra in set(antes[rid]) | set(depois[rid]):
            a0, v0 = antes[rid].get(quebra, (0, 0))
            a1, v1 = depois[rid].get(quebra, (0, 0))
            if (a1 - a0, v1 - v0) != (0, 0):
                delta[quebra] = (a1 - a0, v1 - v0)
        assert delta == quebras, f"{caso}: {rid}"


_FONTES_RFB_RN24 = ("paises", "qualificacoes")


def _duplicar_no_mes(raw: Path, mes: str, arquivo: str) -> None:
    """Grava, na partição de `mes` de cada fonte RFB da RN-24, um Parquet com uma linha repetida."""
    with duckdb.connect() as con:
        for tabela in _FONTES_RFB_RN24:
            pasta = raw / tabela / f"mes_referencia={mes}"
            origem = f"{raw}/{tabela}/mes_referencia=*/*.parquet"
            con.execute(
                f"copy (select * from read_parquet('{origem}') where _mes_referencia = '{mes}' "
                f"order by codigo limit 1) to '{pasta / arquivo}' (format parquet)"
            )


def test_rn24_conta_so_o_mes_do_relatorio(
    copia_base: Path, sqls: dict[str, str], tmp_path: Path
) -> None:
    """Países e qualificações valem no mês do relatório: um duplicado num mês antigo não conta,
    um no mês do relatório conta. Lê uma cópia das partições raw, não as do `make ci`."""
    raiz = Path(os.environ["RAIZ_DADOS"])
    analise = ler_catalogo()["RN-24"].analise
    raw = tmp_path / "raw" / "rfb"
    for tabela in _FONTES_RFB_RN24:
        shutil.copytree(raiz / "raw" / "rfb" / tabela, raw / tabela)
    alvo = {analise: sqls[analise].replace(f"{raiz}/raw/rfb/", f"{raw}/")}
    assert alvo[analise] != sqls[analise]
    with duckdb.connect(str(copia_base), read_only=True) as con:
        (mes,) = con.execute(
            "select max(_mes_referencia) from int_estabelecimentos__enriquecidos"
        ).fetchone()
    meses = sorted(p.name.split("=")[1] for p in (raw / "paises").iterdir())
    antigo = meses[0]
    assert antigo < mes, "as fixtures têm um mês antigo nas fontes RFB"

    def _delta(antes: dict, depois: dict) -> dict:
        return {
            q: (depois[q][0] - antes[q][0], depois[q][1] - antes[q][1])
            for q in depois
            if depois[q] != antes[q]
        }

    antes = _por_quebra(copia_base, alvo)["RN-24"]
    _duplicar_no_mes(raw, antigo, "duplicado-antigo.parquet")
    depois_antigo = _por_quebra(copia_base, alvo)["RN-24"]
    assert _delta(antes, depois_antigo) == {}, "duplicado de mês antigo contou na RN-24"
    _duplicar_no_mes(raw, mes, "duplicado-corrente.parquet")
    depois_corrente = _por_quebra(copia_base, alvo)["RN-24"]
    assert _delta(depois_antigo, depois_corrente) == {
        ("rfb.paises",): (1, 1),
        ("rfb.qualificacoes",): (1, 1),
    }
