"""Os caminhos de `docs/` centralizados em `rfb_pipeline.caminhos` apontam para arquivos reais."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest

from rfb_pipeline import caminhos

sys.path.insert(0, str(caminhos.RAIZ_REPO / "scripts"))


@pytest.mark.parametrize(
    "constante",
    [
        "CATALOGO_REGRAS",
        "DICIONARIO_DADOS",
        "QUALIDADE_DADOS",
        "CAMADA_SEMANTICA",
        "CONCEITOS",
        "DOC_BLOCKS_CONCEITOS",
        "GUIA_CONSULTA",
        "OPERACAO",
        "CENARIOS_DE_USO",
        "GOLDEN_MATRIZ",
        "GOLDEN_SEMANTICA",
        "GOLDEN_CATALOGO",
        "ONTOLOGIA",
    ],
)
def test_documento_existe(constante: str) -> None:
    assert getattr(caminhos, constante).is_file()


def test_saidas_padrao_dos_relatorios_ficam_em_docs() -> None:
    for saida in (caminhos.RELATORIO_ESTUDO_CASO, caminhos.RELATORIO_REGRAS_NEGOCIO):
        assert saida.is_relative_to(caminhos.DIR_DOCS)
        assert saida.suffix == ".md"


def test_relativo_e_link_de() -> None:
    assert caminhos.relativo(caminhos.DIR_DOCS / "adr") == "docs/adr"
    origem = caminhos.DIR_DOCS / "a" / "b.md"
    assert caminhos.link_de(origem, caminhos.DIR_DOCS / "adr" / "x.md") == "../adr/x.md"
    assert caminhos.link_de(origem, caminhos.RAIZ_REPO / "README.md") == "../../README.md"


_PASTA_DOCS = re.compile(r"(?:^|/)docs(?:/|$)")


def montagens_de_caminho_de_docs(codigo: str) -> list[int]:
    """Linhas em que um literal com a pasta `docs` entra na montagem de um caminho (RD-07).

    Pega o literal (`"docs"`, `"docs/x.md"`, `".../docs/..."`) como operando de `/` ou `+`, como
    argumento de chamada (`os.path.join`, `Path`, `joinpath`), como trecho de f-string ou atribuído
    direto a um nome. Docstrings e literais dentro de listas, conjuntos e comparações não contam.
    """
    arvore = ast.parse(codigo)
    pais = {filho: pai for pai in ast.walk(arvore) for filho in ast.iter_child_nodes(pai)}
    linhas = []
    for no in ast.walk(arvore):
        if not (isinstance(no, ast.Constant) and isinstance(no.value, str)):
            continue
        if " " in no.value.strip() or not _PASTA_DOCS.search(no.value):
            continue
        pai = pais.get(no)
        if (
            isinstance(pai, ast.BinOp) and isinstance(pai.op, ast.Div | ast.Add)
            or isinstance(pai, ast.Call) and no in pai.args
            or isinstance(pai, ast.JoinedStr)
            or isinstance(pai, ast.Assign | ast.AnnAssign) and pai.value is no
        ):  # fmt: skip
            linhas.append(no.lineno)
    return linhas


def test_guarda_pega_toda_montagem_de_caminho_de_docs() -> None:
    """Mutações da RD: f-string (M2), `os.path.join` (M3) e `/` (controle) são pegos."""
    for codigo in (
        'ANTIGO = f"{RAIZ}/docs/QUALIDADE_DADOS.md"',
        'ANTIGO = os.path.join(str(RAIZ), "docs", "QUALIDADE_DADOS.md")',
        'ANTIGO = RAIZ / "docs/QUALIDADE_DADOS.md"',
        'ANTIGO = RAIZ / "docs" / "x.md"',
        'ANTIGO = Path(RAIZ).joinpath("docs")',
        'ANTIGO = str(RAIZ) + "/docs/x.md"',
        'ANTIGO = "docs/x.md"',
    ):
        assert montagens_de_caminho_de_docs(codigo) == [1], codigo
    for codigo in (
        '"""Gera `docs/x.md`."""',
        'PASTAS = {"marts", "docs"}',
        'assert relativo(p) == "docs/adr"',
        'print("veja a documentação em docs")',
    ):
        assert montagens_de_caminho_de_docs(codigo) == [], codigo


def test_nenhum_python_monta_caminho_de_docs_fora_de_caminhos() -> None:
    """Código, scripts e testes usam as constantes; só `caminhos.py` conhece a pasta `docs`."""
    infratores = [
        f"{arquivo.relative_to(caminhos.RAIZ_REPO).as_posix()}:{linha}"
        for pasta in ("src", "scripts", "tests")
        for arquivo in (caminhos.RAIZ_REPO / pasta).rglob("*.py")
        if arquivo != Path(caminhos.__file__) and arquivo != Path(__file__)
        for linha in montagens_de_caminho_de_docs(arquivo.read_text(encoding="utf-8"))
    ]
    assert infratores == []


def test_padroes_dos_scripts_e_da_cli_vem_das_constantes() -> None:
    import gerar_catalogo_golden
    import gerar_dicionario_dados
    import gerar_qualidade_dados
    import verificar_doc_semantica

    assert gerar_dicionario_dados.SAIDA == caminhos.DICIONARIO_DADOS
    assert gerar_qualidade_dados.SAIDA == caminhos.QUALIDADE_DADOS
    assert gerar_catalogo_golden.GUIA == caminhos.GUIA_CONSULTA
    assert gerar_catalogo_golden.CATALOGO == caminhos.GOLDEN_CATALOGO
    assert verificar_doc_semantica.DOCS == (caminhos.CONCEITOS, caminhos.CAMADA_SEMANTICA)
