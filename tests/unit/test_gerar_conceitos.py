"""Definições com fonte única (v1.5.0): doc blocks do dbt → `conceitos.md`, YAMLs e catálogo."""

from __future__ import annotations

import re
import sys

import pytest

from rfb_pipeline.caminhos import CONCEITOS, RAIZ_REPO

sys.path.insert(0, str(RAIZ_REPO / "scripts"))

import gerar_catalogo_golden  # noqa: E402
import gerar_conceitos as g  # noqa: E402

YAMLS = sorted((RAIZ_REPO / "transform" / "models").rglob("*.yml"))
_RE_DOC = re.compile(r"""\{\{\s*doc\(\s*['"](\w+)['"]\s*\)\s*\}\}""")


def test_le_titulo_e_texto_dos_doc_blocks() -> None:
    texto = (
        "{# cabeçalho #}\n{% docs a %}{# Título A #}\nTexto **A**.\n{% enddocs %}\n"
        "{% docs b %}{# B #}\nB.{% enddocs %}"
    )
    assert g.ler_definicoes(texto) == [
        g.Definicao("a", "Título A", "Texto **A**."),
        g.Definicao("b", "B", "B."),
    ]


@pytest.mark.parametrize(
    ("texto", "erro"),
    [
        ("{% docs a %}sem título{% enddocs %}", "falta o título"),
        ("{% docs a %}{# A #}{% enddocs %}", "vazio"),
        ("{% docs a %}{# A #}x{% enddocs %}{% docs a %}{# A #}y{% enddocs %}", "repetidos"),
    ],
)
def test_recusa_doc_block_fora_do_padrao(texto: str, erro: str) -> None:
    with pytest.raises(g.ConceitosErro, match=erro):
        g.ler_definicoes(texto)


def test_bloco_gerado_de_conceitos_md_em_dia() -> None:
    """Mudou um doc block sem `make conceitos`: este teste falha (o catálogo falha no `make ci`)."""
    atual = CONCEITOS.read_text(encoding="utf-8")
    assert g.substituir_bloco(atual, g.renderizar_bloco(g.carregar())) == atual, (
        "conceitos.md desatualizado: rode `make conceitos` (e `make golden`)"
    )


def test_todo_doc_dos_yamls_existe_e_todo_doc_block_e_usado() -> None:
    """`doc('x')` sem bloco quebra o `dbt parse`; bloco sem uso não chega ao dicionário."""
    nomes = {d.nome for d in g.carregar()}
    usados = {n for y in YAMLS for n in _RE_DOC.findall(y.read_text(encoding="utf-8"))}
    assert usados - nomes == set(), "doc() sem doc block"
    assert nomes - usados == set(), "doc block sem uso nos YAMLs"


def test_todo_doc_block_esta_ligado_a_um_conceito_da_matriz() -> None:
    assert (
        gerar_catalogo_golden.problemas_de_definicoes(
            gerar_catalogo_golden.carregar_matriz(), g.carregar()
        )
        == []
    )


def test_matriz_recusa_definicao_inexistente_e_bloco_solto() -> None:
    definicoes = [g.Definicao("a", "A", "a"), g.Definicao("b", "B", "b")]
    matriz = {"conceitos": [{"id": "x", "definicoes": ["a", "zzz"]}]}
    problemas = gerar_catalogo_golden.problemas_de_definicoes(matriz, definicoes)
    assert any("'zzz'" in p for p in problemas)
    assert any("doc block 'b'" in p for p in problemas)
