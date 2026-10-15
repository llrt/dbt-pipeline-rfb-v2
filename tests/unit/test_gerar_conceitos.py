"""Definições com fonte única (v1.5.0): doc blocks do dbt → `conceitos.md`, YAMLs e catálogo.

Em `conceitos.md`, cada definição aparece uma vez, no lugar do conceito, e o complemento escrito à
mão não a repete (RD-01, RD-02).
"""

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


def test_conceitos_md_em_dia() -> None:
    """Mudou um doc block sem `make conceitos`: este teste falha (o catálogo falha no `make ci`)."""
    atual = CONCEITOS.read_text(encoding="utf-8")
    assert g.atualizar(atual, g.carregar()) == atual, (
        "conceitos.md desatualizado: rode `make conceitos` (e `make golden`)"
    )


def test_complemento_escrito_a_mao_nao_repete_o_doc_block() -> None:
    """RD-02: a definição existe num lugar só; o texto à mão em volta não repete os seus valores."""
    assert g.repeticoes(CONCEITOS.read_text(encoding="utf-8"), g.carregar()) == []


def _doc(*subsecoes: str) -> str:
    return (
        "# T\n\n" + "\n".join(subsecoes) + f"\n## Glossário\n\n{g.INICIO_INDICE}\n{g.FIM_INDICE}\n"
    )


def _lugar(nome: str, conteudo: str = "") -> str:
    return f"<!-- definição: {nome} -->\n{conteudo}<!-- fim da definição: {nome} -->\n"


DEFS = [
    g.Definicao(
        "mei", "MEI", "Até **R$ 81 mil** (LC 123/2006, art. 18-A).\n\nUm empregado (art. 18-C)."
    ),
    g.Definicao("porte", "Porte", "ME até R$ 360 mil; código 2135 em 2026."),
]


def test_preenche_cada_lugar_e_o_indice() -> None:
    texto = _doc("### MEI\n", _lugar("mei", "> velho\n"), "### Porte\n", _lugar("porte"))
    novo = g.atualizar(texto, DEFS)
    assert (
        '<a id="def-mei"></a>\n> Até **R$ 81 mil** (LC 123/2006, art. 18-A).\n>\n> Um empregado'
        in novo
    )
    assert "velho" not in novo
    assert "[MEI](#def-mei) · [Porte](#def-porte)" in novo
    assert g.atualizar(novo, DEFS) == novo


@pytest.mark.parametrize(
    ("lugares", "erro"),
    [
        ([_lugar("mei")], "doc block porte sem lugar"),
        ([_lugar("mei"), _lugar("porte"), _lugar("mei")], "mei com mais de um lugar"),
        ([_lugar("mei"), _lugar("porte"), _lugar("outro")], "sem doc block: outro"),
        ([_lugar("mei"), "<!-- definição: porte -->\n> x\n"], "sem o `<!-- fim"),
    ],
)
def test_recusa_lugar_faltando_repetido_ou_solto(lugares: list[str], erro: str) -> None:
    with pytest.raises(g.ConceitosErro, match=erro):
        g.atualizar(_doc(*lugares), DEFS)


def test_valores_juntam_formatos_e_ignoram_anos_e_normas() -> None:
    assert g.valores("até R$ 81 mil (LC 123/2006, art. 18-A)") == {"81000", "art. 18-A"}
    assert g.valores("R$ 81.000,00 e 81.000") == {"81000"}
    assert g.valores("R$ 4,8 milhões") == {"4800000"}
    assert g.valores("em 2026, IN 2.119, CGSN 140, art. 100 e Lei 8.934") == {"art. 100"}
    assert g.valores("[IN 2.119, art. 9º, parágrafo único] e arts. 24 e 31") == {
        "art. 9º, parágrafo único",
        "art. 24",
    }
    assert g.valores("o código 2135 e a ordem 0001; 99 % e 12/09/2026") == {"2135", "0001"}


@pytest.mark.parametrize(
    ("complemento", "repetido"),
    [
        ("O limite é de R$ 81.000,00 no ano anterior.", "81000"),
        ("Segundo o [LC 123, art. 18-A], ...", "art. 18-A"),
        ("Fora do doc block, a regra do art. 18-C vale.", "art. 18-C"),
    ],
)
def test_repeticao_do_doc_block_no_complemento_e_pega(complemento: str, repetido: str) -> None:
    texto = g.atualizar(
        _doc("### MEI\n", _lugar("mei"), complemento, "### Porte\n", _lugar("porte")), DEFS
    )
    (problema,) = g.repeticoes(texto, DEFS)
    assert problema.startswith("MEI: o complemento repete") and repetido in problema


def test_complemento_pode_detalhar_sem_repetir() -> None:
    complemento = "No ano de abertura, R$ 6.750,00 por mês [LC 123, art. 18-A, § 2º]; até 2027."
    texto = g.atualizar(
        _doc("### MEI\n", _lugar("mei"), complemento, "### Porte\n", _lugar("porte")), DEFS
    )
    assert g.repeticoes(texto, DEFS) == []


def test_main_verificar_reprova_repeticao(tmp_path) -> None:
    fonte = tmp_path / "docs.md"
    fonte.write_text("{% docs mei %}{# MEI #}\nAté R$ 81 mil.\n{% enddocs %}\n", encoding="utf-8")
    saida = tmp_path / "conceitos.md"
    saida.write_text(_doc("### MEI\n", _lugar("mei"), "R$ 81.000,00\n"), encoding="utf-8")
    assert g.main(["--fonte", str(fonte), "--saida", str(saida)]) == 1
    assert g.main(["--verificar", "--fonte", str(fonte), "--saida", str(saida)]) == 1
    saida.write_text(
        saida.read_text(encoding="utf-8").replace("R$ 81.000,00", "R$ 6.750,00"), "utf-8"
    )
    assert g.main(["--verificar", "--fonte", str(fonte), "--saida", str(saida)]) == 0


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
