"""Caminhos de `docs/` que o código, os scripts e os testes leem ou gravam, num lugar só.

Mover um documento é mudar a constante aqui; nada mais no código cita `docs/...` (as mensagens
usam `relativo()`). Os links dentro dos `.md` são conferidos por `scripts/verificar_links_docs.py`.
"""

from __future__ import annotations

import os
from pathlib import Path

RAIZ_REPO = Path(__file__).resolve().parents[2]
DIR_DOCS = RAIZ_REPO / "docs"
DIR_ADR = DIR_DOCS / "adr"

# Relatórios que `rfb relatorio` e `rfb regras` gravam por padrão.
RELATORIO_ESTUDO_CASO = DIR_DOCS / "RELATORIO_ESTUDO_CASO.md"
RELATORIO_REGRAS_NEGOCIO = DIR_DOCS / "RELATORIO_REGRAS_NEGOCIO.md"

# Documentos gerados ou conferidos por scripts e testes.
CATALOGO_REGRAS = DIR_DOCS / "REGRAS_NEGOCIO.md"
DICIONARIO_DADOS = DIR_DOCS / "DICIONARIO_DADOS.md"
QUALIDADE_DADOS = DIR_DOCS / "QUALIDADE_DADOS.md"
CAMADA_SEMANTICA = DIR_DOCS / "CAMADA_SEMANTICA.md"
GUIA_CONSULTA = DIR_DOCS / "GUIA_CONSULTA_LINGUAGEM_NATURAL.md"
OPERACAO = DIR_DOCS / "OPERACAO.md"
CENARIOS_DE_USO = DIR_DOCS / "CENARIOS_DE_USO.md"

# Golden queries (ADR-0023) e ontologia.
DIR_GOLDEN = DIR_DOCS / "golden_queries"
GOLDEN_MATRIZ = DIR_GOLDEN / "matriz.yml"
GOLDEN_SEMANTICA = DIR_GOLDEN / "semantica.yml"
GOLDEN_CATALOGO = DIR_GOLDEN / "catalogo.json"
ONTOLOGIA = DIR_DOCS / "ontologia" / "rfb_cnpj.ttl"


def link_de(origem: Path, alvo: Path) -> str:
    """Alvo do link Markdown de um arquivo (`origem`) para `alvo`, ambos caminhos do repositório."""
    return Path(os.path.relpath(alvo, origem.parent)).as_posix()


def relativo(caminho: Path) -> str:
    """Caminho relativo à raiz do repositório, com `/`, para mensagens e textos de ajuda."""
    return caminho.relative_to(RAIZ_REPO).as_posix()
