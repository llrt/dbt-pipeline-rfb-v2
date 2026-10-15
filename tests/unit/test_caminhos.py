"""Os caminhos de `docs/` centralizados em `rfb_pipeline.caminhos` apontam para arquivos reais."""

from __future__ import annotations

import pytest

from rfb_pipeline import caminhos


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
