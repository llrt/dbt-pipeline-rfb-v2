"""Guia de construção do agente: campos do catálogo citados existem; a versão bate."""

from __future__ import annotations

import json
import re

from rfb_pipeline import __version__, caminhos

DOC = caminhos.GUIA_CONSTRUCAO_AGENTE
# Primeira coluna de tabela com um campo entre crases, só na seção "O que indexar".
_CAMPO_EM_TABELA = re.compile(r"^\|\s*`([a-z_][a-z0-9_\[\].]*)`\s*\|", re.M)


def _catalogo() -> dict:
    return json.loads(caminhos.GOLDEN_CATALOGO.read_text(encoding="utf-8"))


def _secao_indexar(texto: str) -> str:
    inicio = texto.index("## 3. O que indexar")
    return texto[inicio : texto.index("## 4.", inicio)]


def campos_inexistentes(texto: str, catalogo: dict) -> list[str]:
    """Campos citados na primeira coluna das tabelas de "O que indexar" que o catálogo não tem."""
    golden = {campo for g in catalogo["golden_queries"] for campo in g}
    ausentes = []
    for citado in _CAMPO_EM_TABELA.findall(_secao_indexar(texto)):
        raiz, *resto = citado.replace("[]", "").split(".")
        if raiz not in catalogo and raiz not in golden:
            ausentes.append(citado)
            continue
        if not resto:
            continue
        itens = catalogo.get(raiz) or []
        subcampos = {c for item in itens for c in item}
        if resto[0] not in subcampos:
            ausentes.append(citado)
    return ausentes


def test_campos_citados_existem_no_catalogo() -> None:
    texto = DOC.read_text(encoding="utf-8")
    assert len(_CAMPO_EM_TABELA.findall(_secao_indexar(texto))) >= 10
    assert campos_inexistentes(texto, _catalogo()) == []


def test_guarda_detecta_campo_inexistente() -> None:
    texto = "## 3. O que indexar\n| `campo_que_nao_existe` | x |\n| `sql` | y |\n## 4. Prompt\n"
    assert campos_inexistentes(texto, _catalogo()) == ["campo_que_nao_existe"]


def test_catalogo_traz_a_versao_do_projeto() -> None:
    assert _catalogo()["versao_projeto"] == __version__
