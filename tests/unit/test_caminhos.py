"""Os caminhos de `docs/` centralizados em `rfb_pipeline.caminhos` apontam para arquivos reais."""

from __future__ import annotations

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


def test_nenhum_python_monta_caminho_de_docs_fora_de_caminhos() -> None:
    """Código, scripts e testes usam as constantes; só `caminhos.py` conhece a pasta `docs`."""
    montagem = re.compile(r"""["']docs["']\s*/|/\s*["']docs["']|["']docs/""")
    infratores = [
        arquivo.relative_to(caminhos.RAIZ_REPO).as_posix()
        for pasta in ("src", "scripts", "tests")
        for arquivo in (caminhos.RAIZ_REPO / pasta).rglob("*.py")
        if arquivo != Path(caminhos.__file__)
        and arquivo != Path(__file__)
        and montagem.search(arquivo.read_text(encoding="utf-8"))
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
    assert verificar_doc_semantica.DOC == caminhos.CAMADA_SEMANTICA
