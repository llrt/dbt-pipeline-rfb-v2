"""Todo doc vivo abre com "Para quem / Quando ler"; os gerados dizem que não se editam à mão.

Doc vivo (v1.5.0): todo `.md` versionado fora de `docs/historico/` (registro datado),
`docs/guia-dbt/` (didático, público próprio), `docs/adr/` (decisões), `.specs/`, `.github/` e
`transform/`, menos os arquivos-ponte dos caminhos antigos.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from rfb_pipeline import caminhos

FORA = (
    *(f"{caminhos.relativo(d)}/" for d in (caminhos.DIR_HISTORICO, caminhos.DIR_DOCS / "guia-dbt")),
    f"{caminhos.relativo(caminhos.DIR_ADR)}/",
    ".specs/",
    ".github/",
    "transform/",
)
GERADOS = {
    caminhos.DICIONARIO_DADOS,
    caminhos.QUALIDADE_DADOS,
    caminhos.RELATORIO_ESTUDO_CASO,
    caminhos.RELATORIO_REGRAS_NEGOCIO,
}


def _ponte(texto: str) -> bool:
    """Arquivo-ponte de um caminho antigo: título e uma linha "Movido para ..." (saem na v1.6.0)."""
    return len(texto.strip().splitlines()) <= 3 and "Movido para" in texto


def docs_vivos(raiz: Path = caminhos.RAIZ_REPO) -> list[Path]:
    saida = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", "*.md"],
        cwd=raiz, capture_output=True, text=True, check=True,
    ).stdout.split()  # fmt: skip
    arquivos = [raiz / a for a in saida if not a.startswith(FORA) and (raiz / a).is_file()]
    return sorted(a for a in arquivos if not _ponte(a.read_text(encoding="utf-8")))


def problemas_de_cabecalho(texto: str, gerado: bool = False) -> list[str]:
    linhas = texto.splitlines()
    if not linhas or not linhas[0].startswith("# "):
        return ["a primeira linha não é o título (`# ...`)"]
    resto = [linha for linha in linhas[1:] if linha.strip()]
    problemas = []
    if not resto or not resto[0].startswith("> **Para quem:**"):
        problemas.append("a primeira linha depois do título não é `> **Para quem:** …`")
    elif "**Quando ler:**" not in " ".join(resto[:3]):
        problemas.append("falta `**Quando ler:**` no cabeçalho")
    if gerado:
        topo = " ".join(linha.removeprefix(">").strip() for linha in resto[:8])
        if "Gerado por" not in topo or "não edite à mão" not in topo:
            problemas.append("doc gerado sem `> Gerado por … — não edite à mão` no topo")
    return problemas


def test_lista_de_docs_vivos_cobre_as_portas_de_entrada() -> None:
    vivos = set(docs_vivos())
    esperados = {
        caminhos.RAIZ_REPO / "README.md",
        caminhos.RAIZ_REPO / "ARCHITECTURE.md",
        caminhos.RAIZ_REPO / "CHANGELOG.md",
        caminhos.CONCEITOS,
        caminhos.OPERACAO,
        caminhos.GUIA_CONSULTA,
        caminhos.CAMADA_SEMANTICA,
        *GERADOS,
    }
    assert esperados <= vivos


@pytest.mark.parametrize("doc", docs_vivos(), ids=lambda p: caminhos.relativo(p))
def test_doc_vivo_tem_cabecalho(doc: Path) -> None:
    problemas = problemas_de_cabecalho(doc.read_text(encoding="utf-8"), doc in GERADOS)
    assert problemas == [], f"{caminhos.relativo(doc)}: " + "; ".join(problemas)


def test_guarda_detecta_cabecalho_ausente_ou_incompleto() -> None:
    bom = "# T\n\n> **Para quem:** a · **Quando ler:** b\n\ntexto\n"
    assert problemas_de_cabecalho(bom) == []
    assert problemas_de_cabecalho("# T\n\ntexto\n")
    assert problemas_de_cabecalho("# T\n\n> **Para quem:** a\n\ntexto\n")
    assert problemas_de_cabecalho(bom, gerado=True)
    gerado = "# T\n\n> **Para quem:** a · **Quando ler:** b\n\n> Gerado por x; não edite à mão.\n"
    assert problemas_de_cabecalho(gerado, gerado=True) == []
    assert _ponte("# X\n\nMovido para [y](y.md) na v1.5.0; este aviso sai na v1.6.0.\n")
