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
DIR_REFERENCIA = DIR_DOCS / "referencia"
DIR_HISTORICO = DIR_DOCS / "historico"

# Relatórios que `rfb relatorio` e `rfb regras` gravam por padrão.
RELATORIO_ESTUDO_CASO = DIR_DOCS / "relatorios" / "estudo-caso.md"
RELATORIO_REGRAS_NEGOCIO = DIR_DOCS / "relatorios" / "regras-negocio.md"

# Documentos gerados ou conferidos por scripts e testes.
CONCEITOS = DIR_DOCS / "conceitos.md"
CATALOGO_REGRAS = DIR_REFERENCIA / "regras-negocio.md"
DICIONARIO_DADOS = DIR_REFERENCIA / "dicionario-dados.md"
QUALIDADE_DADOS = DIR_REFERENCIA / "qualidade-dados.md"
CAMADA_SEMANTICA = DIR_REFERENCIA / "camada-semantica.md"
GUIA_CONSULTA = DIR_DOCS / "uso" / "consulta-agente.md"
OPERACAO = DIR_DOCS / "operacao.md"
CENARIOS_DE_USO = DIR_DOCS / "uso" / "cenarios.md"

# Golden queries (ADR-0023) e ontologia.
DIR_GOLDEN = DIR_REFERENCIA / "golden_queries"
GOLDEN_MATRIZ = DIR_GOLDEN / "matriz.yml"
GOLDEN_SEMANTICA = DIR_GOLDEN / "semantica.yml"
GOLDEN_CATALOGO = DIR_GOLDEN / "catalogo.json"
ONTOLOGIA = DIR_REFERENCIA / "ontologia" / "rfb_cnpj.ttl"

# Doc blocks do dbt com as definições curtas dos conceitos (fonte de `CONCEITOS` e do catálogo).
DOC_BLOCKS_CONCEITOS = RAIZ_REPO / "transform" / "models" / "docs" / "conceitos.md"


def link_de(origem: Path, alvo: Path) -> str:
    """Alvo do link Markdown de um arquivo (`origem`) para `alvo`, ambos caminhos do repositório."""
    return Path(os.path.relpath(alvo, origem.parent)).as_posix()


def relativo(caminho: Path) -> str:
    """Caminho relativo à raiz do repositório, com `/`, para mensagens e textos de ajuda."""
    return caminho.relative_to(RAIZ_REPO).as_posix()
