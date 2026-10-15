# ruff: noqa: E501  (textos e SQL de exemplo)
"""ADR-0023: as golden queries respondem nas fixtures exatamente o que o cabeçalho diz, sem expor pessoa.

Roda depois do `make ci` (warehouse e gold de `RAIZ_DADOS`, meses 2026-08 e 2026-09):
- toda golden query SQL de `transform/analyses/golden/` compila; o SQL **portável** do catálogo (`main.<relação>`
  e `${RAIZ_DADOS}`) executa no warehouse e devolve exatamente `resposta_esperada_fixtures`, na ordem;
- todo comando `mf query` de `docs/golden_queries/semantica.yml` devolve a resposta esperada (linhas ordenadas);
- nenhuma saída tem coluna de pessoa, contato ou endereço, nem valor que pareça CPF/CNPJ (ADR-0008);
- os cabeçalhos são válidos e toda célula da matriz conceito × camada tem query ou motivo;
- `docs/golden_queries/catalogo.json` e o índice do guia estão em dia (`make golden`).
"""

from __future__ import annotations

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
_RE_DATA_ISO = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")


def _raiz() -> Path:
    return Path(os.environ["RAIZ_DADOS"])


@pytest.fixture(scope="module")
def resultados() -> dict[str, dict]:
    """Compila as golden queries e executa o SQL portável (o do catálogo) no warehouse, somente leitura."""
    raiz = _raiz()
    compilados = g.compilar(raiz)
    assert set(compilados) == set(GOLDEN), "toda golden query precisa compilar"
    saida: dict[str, dict] = {}
    with duckdb.connect(str(raiz / "warehouse.duckdb"), read_only=True) as con:
        for nome, sql in compilados.items():
            portavel = g.normalizar_sql(sql, raiz)
            assert not g.caminho_absoluto_no_sql(portavel), f"{nome}: caminho da máquina no SQL"
            executavel = portavel.replace(g.MARCADOR_RAIZ, str(raiz))
            cursor = con.execute(executavel)
            saida[nome] = g.normalizar_resultado(
                [d[0] for d in cursor.description], cursor.fetchall()
            )
    return saida


def _sem_identificador(nome: str, resultado: dict, privacidade: str) -> list[str]:
    """Colunas proibidas e valores de texto que parecem CPF/CNPJ (guarda de `regras.py`)."""
    problemas = [
        f"coluna proibida: {c}" for c in g.colunas_proibidas(resultado["colunas"], privacidade)
    ]
    if privacidade == "identifica_estabelecimento":
        return problemas
    for linha in resultado["linhas"]:
        for valor in linha:
            if (
                isinstance(valor, str)
                and not _RE_DATA_ISO.match(valor)
                and traz_identificador(valor)
            ):
                problemas.append(f"valor com cara de identificador: {valor!r}")
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
def test_golden_query_sql_nao_expoe_pessoa(resultados, nome: str) -> None:
    cabecalho, _ = GOLDEN[nome]
    assert (
        _sem_identificador(nome, resultados[nome], cabecalho.get("privacidade", "agregado")) == []
    )


@pytest.mark.parametrize("entrada", SEMANTICA, ids=[e["id"] for e in SEMANTICA])
def test_golden_query_semantica_devolve_a_resposta_esperada(entrada: dict, tmp_path: Path) -> None:
    obtido = g.executar_mf(entrada, _raiz(), tmp_path)
    assert obtido == entrada["resposta_esperada_fixtures"], (
        f"{entrada['id']}: a resposta nas fixtures mudou. Obtido:\n{obtido}"
    )
    assert _sem_identificador(entrada["id"], obtido, entrada.get("privacidade", "agregado")) == []


def test_catalogo_e_indice_do_guia_em_dia() -> None:
    """`--verificar` gera em memória e compara com `catalogo.json` e o bloco gerado do guia."""
    feito = subprocess.run(
        [sys.executable, str(RAIZ_REPO / "scripts" / "gerar_catalogo_golden.py"), "--verificar",
         "--raiz-dados", str(_raiz())],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    assert feito.returncode == 0, feito.stdout + feito.stderr
