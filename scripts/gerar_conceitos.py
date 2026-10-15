"""Copia as definições (doc blocks do dbt) para a seção "Definições" de `docs/conceitos.md`.

Uso: `make conceitos` ou `uv run python scripts/gerar_conceitos.py`. Com `--verificar` não escreve
nada: falha (código 1) se o bloco gerado de `docs/conceitos.md` divergir dos doc blocks.

A fonte é `caminhos.DOC_BLOCKS_CONCEITOS` (`{% docs <nome> %}{# Título #} ... {% enddocs %}`): o
mesmo texto que os YAMLs dos modelos usam com `{{ doc('<nome>') }}` e que
`gerar_catalogo_golden.py` embute no catálogo. Lê o arquivo direto, sem o dbt; o `dbt parse`
confere à parte que todo `doc()` dos YAMLs existe.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from rfb_pipeline.caminhos import CONCEITOS, DOC_BLOCKS_CONCEITOS, relativo

FONTE = DOC_BLOCKS_CONCEITOS
SAIDA = CONCEITOS
INICIO_BLOCO = (
    "<!-- INÍCIO do bloco gerado por scripts/gerar_conceitos.py (make conceitos) a partir de "
    "transform/models/docs/conceitos.md: não edite à mão -->"
)
FIM_BLOCO = "<!-- FIM do bloco gerado das definições -->"

_RE_BLOCO = re.compile(r"\{%-?\s*docs\s+(\w+)\s*-?%\}(.*?)\{%-?\s*enddocs\s*-?%\}", re.S)
_RE_TITULO = re.compile(r"\A\s*\{#\s*(.+?)\s*#\}", re.S)


class ConceitosErro(Exception):
    """Doc block fora do padrão ou `docs/conceitos.md` sem os marcadores."""


@dataclass(frozen=True)
class Definicao:
    nome: str
    titulo: str
    texto: str


def ler_definicoes(texto: str) -> list[Definicao]:
    """Os doc blocks na ordem do arquivo; o título vem do comentário Jinja do início do bloco."""
    definicoes = []
    for nome, corpo in _RE_BLOCO.findall(texto):
        titulo = _RE_TITULO.match(corpo)
        if not titulo:
            raise ConceitosErro(f"doc block {nome}: falta o título (`{{# Título #}}` no início)")
        conteudo = corpo[titulo.end() :].strip()
        if not conteudo:
            raise ConceitosErro(f"doc block {nome}: vazio")
        definicoes.append(Definicao(nome, titulo.group(1), conteudo))
    nomes = [d.nome for d in definicoes]
    repetidos = sorted({n for n in nomes if nomes.count(n) > 1})
    if repetidos:
        raise ConceitosErro(f"doc blocks repetidos: {', '.join(repetidos)}")
    return definicoes


def carregar(caminho: Path = FONTE) -> list[Definicao]:
    return ler_definicoes(caminho.read_text(encoding="utf-8"))


def ancora(nome: str) -> str:
    return f"def-{nome.replace('_', '-')}"


def renderizar_bloco(definicoes: list[Definicao]) -> str:
    linhas = [INICIO_BLOCO, ""]
    for d in definicoes:
        linhas += [f'<a id="{ancora(d.nome)}"></a>', f"**{d.titulo}** (`{d.nome}`)", ""]
        linhas += [d.texto, ""]
    return "\n".join([*linhas, FIM_BLOCO])


def substituir_bloco(texto: str, bloco: str) -> str:
    inicio = texto.find(INICIO_BLOCO)
    fim = texto.find(FIM_BLOCO, max(inicio, 0))
    if inicio < 0 or fim < inicio:
        raise ConceitosErro(f"{relativo(SAIDA)}: faltam os marcadores do bloco gerado")
    return texto[:inicio] + bloco + texto[fim + len(FIM_BLOCO) :]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verificar", action="store_true", help="só confere se está em dia")
    parser.add_argument("--fonte", type=Path, default=FONTE)
    parser.add_argument("--saida", type=Path, default=SAIDA)
    args = parser.parse_args(argv)
    try:
        definicoes = carregar(args.fonte)
        atual = args.saida.read_text(encoding="utf-8")
        novo = substituir_bloco(atual, renderizar_bloco(definicoes))
    except ConceitosErro as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1
    if args.verificar:
        if novo != atual:
            print(
                f"{args.saida.name} desatualizado em relação aos doc blocks: rode `make conceitos` "
                "(e `make golden`) e versione o resultado",
                file=sys.stderr,
            )
            return 1
        print(f"{args.saida.name} em dia: {len(definicoes)} definições")
        return 0
    args.saida.write_text(novo, encoding="utf-8")
    print(f"{args.saida.name}: {len(definicoes)} definições atualizadas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
