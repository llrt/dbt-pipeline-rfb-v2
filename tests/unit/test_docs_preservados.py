"""Guardas contra perda silenciosa de docs (mutações M5 e M6 da revisão RD).

- Os arquivos-ponte dos caminhos antigos existem até a v1.6.0, quando saem (e este teste passa a
  exigir que tenham saído).
- Toda revisão do histórico está na tabela de `docs/historico/README.md` e tem a triagem do líder
  anexada (`## Triagem do líder`).
"""

from __future__ import annotations

import re

import pytest
from test_cabecalho_docs import _ponte

from rfb_pipeline import __version__, caminhos

# Caminho antigo -> destinos para os quais a ponte tem de apontar.
PONTES = {
    caminhos.DIR_DOCS / "CAMADA_SEMANTICA.md": (caminhos.CONCEITOS, caminhos.CAMADA_SEMANTICA),
    caminhos.DIR_DOCS / "DICIONARIO_DADOS.md": (caminhos.DICIONARIO_DADOS,),
    caminhos.DIR_DOCS / "GUIA_CONSULTA_LINGUAGEM_NATURAL.md": (caminhos.GUIA_CONSULTA,),
    caminhos.DIR_DOCS / "REGRAS_NEGOCIO.md": (caminhos.CATALOGO_REGRAS,),
    caminhos.DIR_DOCS / "ESCOPO.md": (caminhos.RAIZ_REPO / "ARCHITECTURE.md",),
    caminhos.RAIZ_REPO / "RETRO.md": (caminhos.DIR_HISTORICO / "retro.md",),
}
SAIDA_DAS_PONTES = (1, 6, 0)
DIR_REVISOES = caminhos.DIR_HISTORICO / "revisoes"
NAO_REVISOES = {"pendencias.md"}


def _versao() -> tuple[int, ...]:
    return tuple(int(parte) for parte in __version__.split(".")[:3])


@pytest.mark.parametrize("ponte", PONTES, ids=lambda p: caminhos.relativo(p))
def test_ponte_existe_ate_a_v1_6_0_e_aponta_para_o_lugar_novo(ponte) -> None:
    if _versao() >= SAIDA_DAS_PONTES:
        assert not ponte.exists(), f"{caminhos.relativo(ponte)}: a ponte sai na v1.6.0"
        return
    assert ponte.is_file(), f"{caminhos.relativo(ponte)}: a ponte só sai na v1.6.0"
    texto = ponte.read_text(encoding="utf-8")
    assert _ponte(texto), f"{caminhos.relativo(ponte)}: não é mais um arquivo-ponte"
    for destino in PONTES[ponte]:
        assert f"]({caminhos.link_de(ponte, destino)}" in texto, caminhos.relativo(destino)


def test_toda_revisao_esta_no_indice_e_tem_a_triagem_do_lider() -> None:
    revisoes = {a.name for a in DIR_REVISOES.glob("*.md")} - NAO_REVISOES
    indice = (caminhos.DIR_HISTORICO / "README.md").read_text(encoding="utf-8")
    listadas = set(re.findall(r"^\| \[\w+\]\(revisoes/(\w+\.md)\)", indice, flags=re.M))
    assert revisoes == listadas, (
        "revisão fora da tabela de docs/historico/README.md (ou o contrário)"
    )
    sem_triagem = [
        nome
        for nome in sorted(revisoes)
        if not re.search(r"^## Triagem do líder", (DIR_REVISOES / nome).read_text("utf-8"), re.M)
    ]
    assert sem_triagem == [], f"revisão sem a seção `## Triagem do líder`: {sem_triagem}"
