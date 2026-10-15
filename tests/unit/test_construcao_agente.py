# ruff: noqa: E501  (textos e nomes de exemplo)
"""Guia de construção do agente: campos do catálogo citados existem; a versão e os tamanhos batem."""

from __future__ import annotations

import json
import re
import sys

import pytest

from rfb_pipeline import __version__, caminhos

sys.path.insert(0, str(caminhos.RAIZ_REPO / "scripts"))

import gerar_catalogo_golden as g  # noqa: E402

DOC = caminhos.GUIA_CONSTRUCAO_AGENTE
# Seções em que todo identificador entre crases fora de bloco de código é campo do catálogo (RGA-06).
SECOES = (("## 3. O que indexar", "## 4."), ("## 5. Ferramentas", "## 7."))
_BLOCO_DE_CODIGO = re.compile(r"```.*?```", re.S)
_IDENTIFICADOR = re.compile(r"`([a-z_][a-z0-9_]*(?:\[\])?(?:\.[a-z_][a-z0-9_]*(?:\[\])?)*)`")
# Identificadores dessas seções que não são campo do catálogo: ferramentas e funções do agente, nomes do DuckDB e do
# sistema de arquivos, valores de campo e o campo do manifesto da ingestão. Campo novo do catálogo não entra aqui.
NAO_SAO_CAMPOS = {
    "agregado", "identifica_estabelecimento",  # valores de `privacidade`
    "buscar_golden", "descrever_relacao", "executar_sql_leitura", "checar_saida", "filtros",
    "conectar_somente_leitura", "exigir_leitura", "conferir_esquema", "comparar_resposta", "bloqueadas",
    "allowed_directories", "lock_configuration", "enable_external_access", "information_schema",
    "information_schema.columns", "main", "read_csv", "read_parquet", "read_text", "json.dumps", "mf", "python",
    "catalogo.json", "warehouse.duckdb", "rfb.empresas", "dq_resumo_execucao", "versao_pipeline",
}  # fmt: skip


def _catalogo() -> dict:
    return json.loads(caminhos.GOLDEN_CATALOGO.read_text(encoding="utf-8"))


def _filhos(catalogo: dict) -> dict:
    """`{campo: subcampos}` de todo campo do catálogo, em qualquer nível; `None` = os campos do topo."""
    filhos: dict = {None: set(catalogo)}

    def andar(no: object, pai: str | None) -> None:
        if isinstance(no, dict):
            for chave, valor in no.items():
                filhos.setdefault(chave, set())
                if pai is not None:
                    filhos[pai].add(chave)
                andar(valor, chave)
        elif isinstance(no, list):
            for item in no:
                andar(item, pai)

    andar(catalogo, None)
    return filhos


def identificadores(texto: str) -> list[str]:
    """Os identificadores entre crases das seções conferidas, fora dos blocos de código."""
    trechos = [texto[texto.index(a) : texto.index(b, texto.index(a))] for a, b in SECOES]
    return _IDENTIFICADOR.findall(_BLOCO_DE_CODIGO.sub("", "\n".join(trechos)))


def campos_inexistentes(texto: str, catalogo: dict) -> list[str]:
    """Identificadores das seções conferidas que nem são campo do catálogo (`campo`, `campo[].sub`) nem exceção."""
    filhos = _filhos(catalogo)
    ausentes = []
    for citado in identificadores(texto):
        if citado in NAO_SAO_CAMPOS:
            continue
        raiz, *resto = citado.replace("[]", "").split(".")
        pai = raiz
        if raiz not in filhos:
            ausentes.append(citado)
            continue
        for sub in resto:
            if sub not in filhos[pai]:
                ausentes.append(citado)
                break
            pai = sub
    return ausentes


def test_campos_citados_existem_no_catalogo() -> None:
    texto = DOC.read_text(encoding="utf-8")
    assert len(identificadores(texto)) >= 60
    assert campos_inexistentes(texto, _catalogo()) == []


@pytest.mark.parametrize(
    "citado", ["`campo_que_nao_existe`", "`conceitos[].definicao`", "`relacoes[].colunas[].tipos`"]
)
def test_guarda_detecta_campo_inexistente(citado: str) -> None:
    texto = f"## 3. O que indexar\n| `sql` | {citado} |\n## 4. Prompt\n## 5. Ferramentas\n## 7.\n"
    assert campos_inexistentes(texto, _catalogo()) == [citado.strip("`")]


def test_catalogo_traz_a_versao_do_projeto() -> None:
    assert _catalogo()["versao_projeto"] == __version__


def test_bloco_de_tamanhos_em_dia() -> None:
    """RGA-10: os tamanhos do §3 são os do catálogo e do guia versionados (o `make golden` os gera)."""
    texto_catalogo = caminhos.GOLDEN_CATALOGO.read_text(encoding="utf-8")
    bloco = g.renderizar_tamanhos(
        json.loads(texto_catalogo),
        texto_catalogo,
        caminhos.GUIA_CONSULTA.read_text(encoding="utf-8"),
    )
    assert bloco in DOC.read_text(encoding="utf-8"), "rode `make golden`"


def test_semantica_traz_as_tabelas_do_sql() -> None:
    """RGA-04: a golden query semântica também traz `tabelas`, as relações `main.<x>` que o seu `sql` lê."""
    for consulta in _catalogo()["golden_queries"]:
        if consulta["camada"] == "semantica":
            assert consulta["tabelas"] == g.relacoes_do_sql_portavel(consulta["sql"]) != [], (
                consulta["id"]
            )
