#!/usr/bin/env python3
"""Confere os links relativos e as âncoras (`#secao`) de todo `.md` versionado do repositório.

Uso: `uv run python scripts/verificar_links_docs.py [arquivo.md ...]` (sem argumentos, todos os
`.md` de `git ls-files`: README, raiz, `docs/`, `.specs/`, `transform/`). Sai com 1 e lista cada
problema (`arquivo:linha: ...`) se um link relativo aponta para arquivo inexistente ou se a âncora
não existe no destino. O nome do arquivo tem de bater também na caixa (`os.listdir`), porque no
macOS o disco não distingue `OPERACAO.md` de `operacao.md` e o CI no Linux distingue. URLs externas (`http:`, `https:`, `mailto:` etc.) são ignoradas. O slug dos
cabeçalhos segue o GitHub: minúsculas, sem pontuação, espaços viram hífens, acentos são mantidos e
repetidos ganham `-1`, `-2`. Python puro, sem dependência.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote

RAIZ = Path(__file__).resolve().parents[1]

_CERCA = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
_CABECALHO = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
_LINK_INLINE = re.compile(r"(?<!\\)\[(?:[^\[\]]|\[[^\]]*\])*\]\(\s*(<[^>]*>|[^\s)]*)[^)]*\)")
_LINK_REFERENCIA = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*(<[^>]*>|\S+)")
_CODIGO_INLINE = re.compile(r"(`+).*?\1")
_ANCORA_HTML = re.compile(r"""<a\s[^>]*?(?:name|id)\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
_ESQUEMA = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


def slug(titulo: str) -> str:
    """Slug de cabeçalho no estilo do GitHub (acentos mantidos)."""
    texto = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", titulo)  # [texto](url) -> texto
    texto = re.sub(r"<[^>]+>", "", texto)  # tags HTML
    texto = texto.replace("`", "").replace("*", "")
    texto = unicodedata.normalize("NFC", texto).strip().lower()
    texto = re.sub(r"[^\w\- ]", "", texto)  # \w mantém letras acentuadas, dígitos e "_"
    return texto.replace(" ", "-")


def _linhas_fora_de_cerca(texto: str):
    """Itera `(numero, linha)` das linhas que não estão dentro de blocos de código cercados."""
    cerca = None
    for numero, linha in enumerate(texto.splitlines(), start=1):
        m = _CERCA.match(linha)
        if m:
            marca = m.group(1)
            if cerca is None:
                cerca = marca[0] * 3
            elif marca[0] * 3 == cerca and linha.strip().strip(marca[0]) == "":
                cerca = None
            continue
        if cerca is None:
            yield numero, linha


def ancoras(texto: str) -> set[str]:
    """Âncoras de um documento: slugs dos cabeçalhos (com sufixo para repetidos) e `<a name/id>`."""
    vistos: dict[str, int] = {}
    resultado: set[str] = set()
    for _, linha in _linhas_fora_de_cerca(texto):
        resultado.update(_ANCORA_HTML.findall(linha))
        m = _CABECALHO.match(linha)
        if not m:
            continue
        base = slug(m.group(2))
        n = vistos.get(base, 0)
        resultado.add(base if n == 0 else f"{base}-{n}")
        vistos[base] = n + 1
    return resultado


def links(texto: str) -> list[tuple[int, str]]:
    """`(linha, destino)` de cada link Markdown fora de blocos e de código em linha."""
    achados: list[tuple[int, str]] = []
    for numero, linha in _linhas_fora_de_cerca(texto):
        limpa = _CODIGO_INLINE.sub("", linha)
        for m in _LINK_INLINE.finditer(limpa):
            achados.append((numero, m.group(1)))
        m = _LINK_REFERENCIA.match(limpa)
        if m:
            achados.append((numero, m.group(1)))
    return [(n, d.strip("<>")) for n, d in achados]


def existe_com_a_caixa_certa(alvo: Path) -> bool:
    """`alvo` (absoluto, resolvido) existe e cada parte do caminho bate na caixa com o disco."""
    if not alvo.exists():
        return False
    base = RAIZ if alvo.is_relative_to(RAIZ) else Path(alvo.anchor)
    pasta = base
    for parte in alvo.relative_to(base).parts:
        if parte not in os.listdir(pasta):
            return False
        pasta = pasta / parte
    return True


def verificar_arquivo(arquivo: Path, cache: dict[Path, set[str]] | None = None) -> list[str]:
    """Problemas de links e âncoras de um `.md`, como `caminho:linha: mensagem`."""
    cache = {} if cache is None else cache
    texto = arquivo.read_text(encoding="utf-8")
    problemas: list[str] = []
    for numero, destino in links(texto):
        if not destino or _ESQUEMA.match(destino):
            continue
        caminho, _, ancora = destino.partition("#")
        if caminho:
            alvo = (arquivo.parent / unquote(caminho)).resolve()
            if not alvo.exists():
                problemas.append(f"{arquivo}:{numero}: link quebrado: {destino}")
                continue
            if not existe_com_a_caixa_certa(alvo):
                problemas.append(
                    f"{arquivo}:{numero}: link com caixa diferente do arquivo: {destino}"
                )
                continue
        else:
            alvo = arquivo.resolve()
        if ancora and alvo.is_file() and alvo.suffix == ".md":
            if alvo not in cache:
                cache[alvo] = ancoras(alvo.read_text(encoding="utf-8"))
            if unquote(ancora).lower() not in cache[alvo]:
                problemas.append(f"{arquivo}:{numero}: âncora inexistente: {destino}")
    return problemas


def arquivos_markdown(raiz: Path = RAIZ) -> list[Path]:
    """Todo `.md` versionado (`git ls-files`), ou todos sob a raiz se não houver git."""
    try:
        saida = subprocess.run(
            ["git", "ls-files", "-z", "--", "*.md"],
            cwd=raiz,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        return [raiz / p for p in saida.split("\0") if p and (raiz / p).is_file()]
    except (OSError, subprocess.CalledProcessError):
        return sorted(p for p in raiz.rglob("*.md") if ".venv" not in p.parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("arquivos", nargs="*", type=Path, help="padrão: todo .md versionado")
    args = parser.parse_args(argv)
    arquivos = [a.resolve() for a in args.arquivos] or arquivos_markdown()
    cache: dict[Path, set[str]] = {}
    problemas = [p for a in arquivos for p in verificar_arquivo(a, cache)]
    for p in problemas:
        print(p.replace(f"{RAIZ}/", ""), file=sys.stderr)
    if problemas:
        print(
            f"{len(problemas)} link(s)/âncora(s) com problema em {len(arquivos)} arquivos.",
            file=sys.stderr,
        )
        return 1
    print(f"links e âncoras ok em {len(arquivos)} arquivos .md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
