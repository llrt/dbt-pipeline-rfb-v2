from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import verificar_links_docs as v  # noqa: E402


@pytest.mark.parametrize(
    ("titulo", "esperado"),
    [
        ("Visão geral", "visão-geral"),
        ("5. Como executar comandos", "5-como-executar-comandos"),
        (
            "2.2 Concorrência: `DBT_THREADS` versus `DUCKDB_THREADS` (após F3a)",
            "22-concorrência-dbt_threads-versus-duckdb_threads-após-f3a",
        ),
        ("Gold misto — o que fazer", "gold-misto--o-que-fazer"),
        ("Link [texto](http://x.y) aqui", "link-texto-aqui"),
    ],
)
def test_slug_no_estilo_do_github(titulo: str, esperado: str) -> None:
    assert v.slug(titulo) == esperado


def test_ancoras_repetidas_ganham_sufixo_e_blocos_de_codigo_sao_ignorados() -> None:
    texto = '# A\n## Dup\n## Dup\n```\n# Fora\n```\n<a name="manual"></a>\n'
    assert v.ancoras(texto) == {"a", "dup", "dup-1", "manual"}


def _escrever(tmp_path: Path, nome: str, texto: str) -> Path:
    arquivo = tmp_path / nome
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(texto, encoding="utf-8")
    return arquivo


def test_links_validos_passam(tmp_path: Path) -> None:
    _escrever(tmp_path, "b.md", "# Título B\n## Seção Ç\n")
    a = _escrever(tmp_path, "a.md", "[x](b.md) [y](b.md#seção-ç) [z](#aqui)\n# Aqui\n[d](sub/)\n")
    (tmp_path / "sub").mkdir()
    assert v.verificar_arquivo(a) == []


def test_link_quebrado_e_reportado_com_linha(tmp_path: Path) -> None:
    a = _escrever(tmp_path, "a.md", "texto\n[x](nao-existe.md)\n")
    (problema,) = v.verificar_arquivo(a)
    assert "a.md:2: link quebrado: nao-existe.md" in problema


def test_link_com_caixa_errada_e_reportado_mesmo_em_disco_sem_caixa(tmp_path: Path) -> None:
    """RD-08: no macOS `OPERACAO.md` "existe" quando o arquivo é `operacao.md`; no Linux, não."""
    _escrever(tmp_path, "uso/operacao.md", "# Operação\n")
    a = _escrever(
        tmp_path, "a.md", "[x](uso/operacao.md)\n[y](uso/OPERACAO.md)\n[z](USO/operacao.md)\n"
    )
    problemas = v.verificar_arquivo(a)
    assert [p.split("a.md:")[1] for p in problemas] == [
        "2: link com caixa diferente do arquivo: uso/OPERACAO.md",
        "3: link com caixa diferente do arquivo: USO/operacao.md",
    ]


def test_ancora_inexistente_e_reportada(tmp_path: Path) -> None:
    _escrever(tmp_path, "b.md", "# Título\n")
    a = _escrever(tmp_path, "a.md", "[x](b.md#outra) [y](#sumiu)\n")
    problemas = v.verificar_arquivo(a)
    assert len(problemas) == 2
    assert all("âncora inexistente" in p for p in problemas)


def test_urls_externas_e_codigo_sao_ignorados(tmp_path: Path) -> None:
    a = _escrever(
        tmp_path,
        "a.md",
        "[x](https://exemplo.com/nao) [m](mailto:a@b.c) `[c](quebrado.md)`\n"
        "```\n[k](quebrado.md)\n```\n",
    )
    assert v.verificar_arquivo(a) == []


def test_main_sai_com_1_se_houver_problema(tmp_path: Path) -> None:
    ok = _escrever(tmp_path, "ok.md", "# T\n")
    ruim = _escrever(tmp_path, "ruim.md", "[x](nada.md)\n")
    assert v.main([str(ok)]) == 0
    assert v.main([str(ok), str(ruim)]) == 1


def test_repositorio_sem_links_quebrados() -> None:
    problemas = [p for a in v.arquivos_markdown() for p in v.verificar_arquivo(a)]
    assert problemas == []
