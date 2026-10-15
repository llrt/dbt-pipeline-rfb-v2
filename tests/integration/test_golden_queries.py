# ruff: noqa: E501  (textos e SQL de exemplo)
"""ADR-0023: as golden queries respondem nas fixtures exatamente o que o cabeçalho diz, sem expor pessoa.

Roda depois do `make ci` (warehouse e gold de `RAIZ_DADOS`, meses 2026-08 e 2026-09):
- toda golden query SQL de `transform/analyses/golden/` compila; o SQL **portável** do catálogo (`main.<relação>`
  e `${RAIZ_DADOS}`) executa no warehouse e devolve exatamente `resposta_esperada_fixtures`, na ordem;
- o SQL que o MetricFlow gera para cada golden query de `docs/golden_queries/semantica.yml` (campo `sql` do
  catálogo) executa numa conexão somente leitura e devolve a resposta esperada (linhas ordenadas, RGQ-01);
- nenhuma saída tem coluna de pessoa, contato ou endereço, nem coluna **derivada** de uma (linhagem do SQL compilado,
  com alias, função ou CTE), nem valor que pareça CPF/CNPJ, em texto, mascarado ou como número (ADR-0008, RGQ-04);
- a checagem pós-execução que o guia dá ao agente (bloco `python` da seção 7) recusa o que deve e aceita as
  respostas de todas as golden queries;
- os cabeçalhos são válidos e toda célula da matriz conceito × camada tem query ou motivo;
- `docs/golden_queries/catalogo.json` e o índice do guia estão em dia (`make golden`).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

RAIZ_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ_REPO / "scripts"))

import gerar_catalogo_golden as g  # noqa: E402

from rfb_pipeline.regras import traz_identificador  # noqa: E402

pytestmark = pytest.mark.skipif(
    "RAIZ_DADOS" not in os.environ, reason="rode via make ci (exporta RAIZ_DADOS)"
)

GOLDEN = g.carregar_golden()
SEMANTICA = g.carregar_semantica()
CATALOGO = {
    q["id"]: q for q in json.loads(g.CATALOGO.read_text(encoding="utf-8"))["golden_queries"]
}
_RE_DATA_ISO = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")


def _raiz() -> Path:
    return Path(os.environ["RAIZ_DADOS"])


@pytest.fixture(scope="module")
def compilados() -> dict[str, str]:
    """O SQL compilado de cada golden query SQL (`dbt compile`), na forma portável do catálogo."""
    raiz = _raiz()
    brutos = g.compilar(raiz)
    assert set(brutos) == set(GOLDEN), "toda golden query precisa compilar"
    return {nome: g.normalizar_sql(sql, raiz) for nome, sql in brutos.items()}


@pytest.fixture(scope="module")
def resultados(compilados: dict[str, str]) -> dict[str, dict]:
    """Executa o SQL portável (o do catálogo) de cada golden query no warehouse, somente leitura."""
    raiz = _raiz()
    saida: dict[str, dict] = {}
    with duckdb.connect(str(raiz / "warehouse.duckdb"), read_only=True) as con:
        for nome, portavel in compilados.items():
            assert not g.caminho_absoluto_no_sql(portavel), f"{nome}: caminho da máquina no SQL"
            executavel = portavel.replace(g.MARCADOR_RAIZ, str(raiz))
            cursor = con.execute(executavel)
            saida[nome] = g.normalizar_resultado(
                [d[0] for d in cursor.description], cursor.fetchall()
            )
    return saida


def _sem_identificador(nome: str, resultado: dict, privacidade: str) -> list[str]:
    """Colunas proibidas e valores que parecem CPF/CNPJ: texto (guarda de `regras.py`), CPF mascarado e número
    de 11 ou 14 dígitos com dígito verificador válido (RGQ-04)."""
    problemas = [
        f"coluna proibida: {c}" for c in g.colunas_proibidas(resultado["colunas"], privacidade)
    ]
    for linha in resultado["linhas"]:
        for valor in linha:
            if isinstance(valor, str) and g.RE_CPF_MASCARADO.search(valor):
                problemas.append(f"valor com CPF mascarado (nome de pessoa): {valor!r}")
            if privacidade == "identifica_estabelecimento":
                continue
            if (
                isinstance(valor, str)
                and not _RE_DATA_ISO.match(valor)
                and traz_identificador(valor)
            ):
                problemas.append(f"valor com cara de identificador: {valor!r}")
            if (
                isinstance(valor, int)
                and not isinstance(valor, bool)
                and g.numero_identificador(valor)
            ):
                problemas.append(f"número com cara de CPF/CNPJ: {valor!r}")
    return [f"{nome}: {p}" for p in problemas]


def test_cabecalhos_validos_e_matriz_coberta() -> None:
    assert g.problemas_gerais(g.carregar_matriz(), GOLDEN, SEMANTICA) == []


@pytest.mark.parametrize("nome", sorted(GOLDEN))
def test_golden_query_sql_devolve_a_resposta_esperada(resultados, nome: str) -> None:
    cabecalho, _ = GOLDEN[nome]
    obtido = resultados[nome]
    assert obtido == cabecalho["resposta_esperada_fixtures"], (
        f"{nome}: a resposta nas fixtures mudou. Obtido:\n{obtido}"
    )


@pytest.mark.parametrize("nome", sorted(GOLDEN))
def test_golden_query_sql_nao_expoe_pessoa(compilados, resultados, nome: str) -> None:
    """Pelo resultado (nome de coluna e valor) e pela linhagem do SQL compilado (alias, função, CTE)."""
    cabecalho, _ = GOLDEN[nome]
    privacidade = cabecalho.get("privacidade", "agregado")
    assert _sem_identificador(nome, resultados[nome], privacidade) == []
    assert g.colunas_derivadas_proibidas(compilados[nome], privacidade) == [], nome


@pytest.mark.parametrize("entrada", SEMANTICA, ids=[e["id"] for e in SEMANTICA])
def test_golden_query_semantica_sql_devolve_a_resposta_esperada(entrada: dict) -> None:
    """O SQL do MetricFlow que está no catálogo (o que o agente executa) roda somente leitura e responde o esperado.

    O `--verificar` de `test_catalogo_e_indice_do_guia_em_dia` garante que esse SQL é o que o `mf` gera hoje.
    """
    sql = CATALOGO[entrada["id"]]["sql"]
    with duckdb.connect(str(_raiz() / "warehouse.duckdb"), read_only=True) as con:
        cursor = con.execute(sql)
        obtido = g.resultado_sql_semantico([d[0] for d in cursor.description], cursor.fetchall())
    assert obtido == entrada["resposta_esperada_fixtures"], (
        f"{entrada['id']}: a resposta nas fixtures mudou. Obtido:\n{obtido}"
    )
    privacidade = entrada.get("privacidade", "agregado")
    assert _sem_identificador(entrada["id"], obtido, privacidade) == []
    assert g.colunas_derivadas_proibidas(sql, privacidade) == [], entrada["id"]


def test_catalogo_e_indice_do_guia_em_dia(manifesto_e_catalogo) -> None:
    """`--verificar` gera em memória e compara com `catalogo.json` e os blocos gerados do guia (índice e esquema).

    O esquema (métricas, dimensões, relações) vem do `dbt docs generate` da fixture `manifesto_e_catalogo`.
    """
    manifesto, _ = manifesto_e_catalogo
    feito = subprocess.run(
        [sys.executable, str(RAIZ_REPO / "scripts" / "gerar_catalogo_golden.py"), "--verificar",
         "--raiz-dados", str(_raiz()), "--alvo-dbt", str(manifesto.parent)],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    assert feito.returncode == 0, feito.stdout + feito.stderr


@pytest.mark.parametrize(
    "metrica", ["qtd_ativos", "aberturas", "taxa_sobrevivencia_3a", "pessoal_ocupado_cempre"]
)  # uma métrica de cada modelo semântico
def test_dimensoes_do_catalogo_sao_as_que_o_mf_aceita(metrica: str) -> None:
    """RGQ-02: as dimensões que o catálogo diz que a métrica aceita são as de `mf list dimensions` (na cópia)."""
    catalogo = json.loads(g.CATALOGO.read_text(encoding="utf-8"))
    (definicao,) = [m for m in catalogo["metricas"] if m["nome"] == metrica]
    esperadas = {"metric_time"} | {
        d["nome"] for d in catalogo["dimensoes"] if d["entidade"] in definicao["entidades"]
    }
    with g.mf_sobre_copia(_raiz()) as mf:
        saida = mf(["list", "dimensions", "--metrics", metrica])
    listadas = {linha.split("•", 1)[1].strip() for linha in saida.splitlines() if "•" in linha}
    assert listadas == esperadas


def _checagem_do_guia():
    """A função `checar_saida` do bloco `python` marcado `# checagem: privacidade` da seção 7 do guia."""
    texto = g.GUIA.read_text(encoding="utf-8")
    (bloco,) = re.findall(r"```python\n(# checagem: privacidade\n.*?)```", texto, re.S)
    espaco: dict = {}
    exec(compile(bloco, "guia:checagem", "exec"), espaco)  # noqa: S102 — código versionado do próprio guia
    return espaco["checar_saida"]


@pytest.mark.parametrize(
    ("colunas", "linhas"),
    [
        (["maior_raiz"], [[14141414]]),  # M1 da RGQ: CNPJ básico como inteiro, nome de coluna livre
        (
            ["titular"],
            [["PINTE BEM ***.***.***-**"]],
        ),  # M2 da RGQ: nome de empresário com outro alias
        (["exemplo"], [["11.222.333/0001-81"]]),
        (["exemplo"], [[11222333000181]]),
        (["exemplo"], [[52998224725]]),
        (["nome"], [["TINTAS"]]),
        (["estabelecimento__nome_fantasia"], [["X"]]),
        (["telefone1"], [["2799"]]),
    ],
)
def test_checagem_do_guia_recusa_identificador(colunas: list[str], linhas: list[list]) -> None:
    """RGQ-04: a checagem pós-execução que o guia manda o agente rodar pega os vazamentos que a RGQ achou."""
    assert _checagem_do_guia()(colunas, linhas)


def test_checagem_do_guia_concorda_com_o_ci_e_aceita_as_golden_queries(resultados) -> None:
    """A checagem do guia dá o mesmo veredito de coluna que o CI em toda coluna do esquema e aceita toda resposta."""
    checar = _checagem_do_guia()
    catalogo = json.loads(g.CATALOGO.read_text(encoding="utf-8"))
    colunas = {c["nome"] for r in catalogo["relacoes"] for c in r["colunas"]}
    colunas |= {d["nome"] for d in catalogo["dimensoes"]}
    divergentes = [
        c for c in sorted(colunas) if bool(checar([c], [])) != bool(g.colunas_proibidas([c]))
    ]
    assert divergentes == []
    for nome, (cabecalho, _) in GOLDEN.items():
        identifica = cabecalho.get("privacidade") == "identifica_estabelecimento"
        resultado = resultados[nome]
        assert checar(resultado["colunas"], resultado["linhas"], identifica) == [], nome
    for entrada in SEMANTICA:
        resultado = entrada["resposta_esperada_fixtures"]
        assert checar(resultado["colunas"], resultado["linhas"]) == [], entrada["id"]


EXEMPLOS = g.exemplos_sql_do_guia(g.GUIA.read_text(encoding="utf-8"))


def test_guia_tem_exemplos_sql_marcados() -> None:
    assert len(EXEMPLOS) >= 3


@pytest.mark.parametrize("exemplo", sorted(EXEMPLOS))
def test_exemplo_sql_do_guia_executa_nas_fixtures(exemplo: str) -> None:
    """RGQ-07: o SQL escrito à mão nos exemplos do guia compila e executa nas fixtures, somente leitura, sem expor pessoa."""
    sql = EXEMPLOS[exemplo]
    with duckdb.connect(str(_raiz() / "warehouse.duckdb"), read_only=True) as con:
        cursor = con.execute(sql)
        colunas, linhas = [d[0] for d in cursor.description], cursor.fetchall()
    assert _checagem_do_guia()(colunas, linhas) == []
    assert g.colunas_derivadas_proibidas(sql) == []
    assert g.municipio_sem_uf(sql) == []


def test_ids_citados_no_guia_e_nos_cabecalhos_existem() -> None:
    """RGQ-07: todo `gq_*` citado no guia inteiro (fora do bloco gerado também) e nos cabeçalhos existe."""
    ids = [*GOLDEN, *(e["id"] for e in SEMANTICA)]
    assert g.problemas_do_guia(g.GUIA.read_text(encoding="utf-8"), ids) == []
    assert g.ids_citados_inexistentes([*(c for c, _ in GOLDEN.values()), *SEMANTICA], ids) == []
