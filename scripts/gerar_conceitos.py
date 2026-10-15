"""Copia as definições (doc blocks do dbt) para o lugar de cada conceito em `docs/conceitos.md`.

Uso: `make conceitos` ou `uv run python scripts/gerar_conceitos.py`. Com `--verificar` não escreve
nada: falha (código 1) se `docs/conceitos.md` divergir dos doc blocks.

A fonte é `caminhos.DOC_BLOCKS_CONCEITOS` (`{% docs <nome> %}{# Título #} ... {% enddocs %}`): o
mesmo texto que os YAMLs dos modelos usam com `{{ doc('<nome>') }}` e que
`gerar_catalogo_golden.py` embute no catálogo. Lê o arquivo direto, sem o dbt; o `dbt parse`
confere à parte que todo `doc()` dos YAMLs existe.

Em `docs/conceitos.md` (v1.5.0, RD-01), cada doc block tem **um** lugar, na subseção que explica o
conceito, entre `<!-- definição: <nome> ... -->` e `<!-- fim da definição: <nome> -->`. O script
preenche o lugar com a definição (em citação; a âncora `#def-<nome>` vai no marcador) e o índice
de termos entre os marcadores do índice. O texto escrito à mão em volta é o complemento e **não
repete** valores do doc block da mesma subseção (números de 3 ou mais dígitos, valores em R$ e
artigos de lei; RD-02): a definição existe num lugar só.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from rfb_pipeline.caminhos import CONCEITOS, DOC_BLOCKS_CONCEITOS, relativo

FONTE = DOC_BLOCKS_CONCEITOS
SAIDA = CONCEITOS
INICIO_INDICE = (
    f"<!-- INÍCIO do índice gerado por scripts/gerar_conceitos.py (make conceitos) a partir de "
    f"{relativo(FONTE)}: não edite à mão -->"
)
FIM_INDICE = "<!-- FIM do índice gerado -->"

_RE_BLOCO = re.compile(r"\{%-?\s*docs\s+(\w+)\s*-?%\}(.*?)\{%-?\s*enddocs\s*-?%\}", re.S)
_RE_TITULO = re.compile(r"\A\s*\{#\s*(.+?)\s*#\}", re.S)
_RE_LUGAR = re.compile(
    r"^<!-- definição: (\w+) [^\n]*\n(.*?)^<!-- fim da definição: (\w+) -->$", re.S | re.M
)
_RE_SUBSECAO = re.compile(r"^#{2,3} ", re.M)

# Valores que o complemento não pode repetir (RD-02). Antes dos números, saem do texto os artigos,
# os valores em R$ e os números de norma (IN 2.119, LC 123/2006), que não são valores.
_RE_ARTIGO = re.compile(
    r"\barts?\.\s*\d+(?:-[A-Z])?º?(?:,\s*(?:§\s*\d+º?(?:-[A-Z])?|[IVX]+\b|parágrafo único))*"
)
_RE_REAIS = re.compile(r"R\$\s?(\d[\d.]*(?:,\d+)?)(?:\s(mil|milhões|milhão)\b)?")
_RE_NORMA = re.compile(
    r"\b(?:IN|LC|Lei|CGSN|PLP|Resolução)(?:\s(?:RFB|CGSN))?(?:\snº)?\s[\d.]+(?:/\d+)?"
)
_RE_NUMERO = re.compile(r"(?<![\w./,-])(\d{1,3}(?:\.\d{3})+|\d{3,})(?![\d/])")
_MULTIPLICADOR = {"mil": 1_000, "milhão": 1_000_000, "milhões": 1_000_000}


class ConceitosErro(Exception):
    """Doc block fora do padrão ou `docs/conceitos.md` sem o lugar de alguma definição."""


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


def inicio_lugar(nome: str) -> str:
    """Marcador de início, com a âncora `#def-<nome>` na mesma linha."""
    return (
        f"<!-- definição: {nome} (gerada do doc block por `make conceitos`; não edite à mão) -->"
        f'<a id="{ancora(nome)}"></a>'
    )


def fim_lugar(nome: str) -> str:
    return f"<!-- fim da definição: {nome} -->"


def renderizar_definicao(d: Definicao) -> str:
    """A definição em citação, sem os marcadores."""
    return (
        "\n".join(f"> {linha}" if linha.strip() else ">" for linha in d.texto.splitlines()) + "\n"
    )


def _chave_alfabetica(titulo: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", titulo).encode("ascii", "ignore").decode()
    return sem_acento.lower()


def renderizar_indice(definicoes: list[Definicao]) -> str:
    """Os títulos em ordem alfabética, cada um com link para a sua definição."""
    termos = [
        f"[{d.titulo}](#{ancora(d.nome)})"
        for d in sorted(definicoes, key=lambda d: _chave_alfabetica(d.titulo))
    ]
    linhas = [""]
    for (
        termo
    ) in termos:  # quebra só entre termos: um link partido em duas linhas escapa aos verificadores
        if linhas[-1] and len(linhas[-1]) + len(termo) + 3 > 118:
            linhas[-1] += " ·"
            linhas.append("")
        linhas[-1] += f" · {termo}" if linhas[-1] else termo
    return "\n".join([INICIO_INDICE, "", *linhas, "", FIM_INDICE])


def lugares(texto: str) -> list[re.Match[str]]:
    """Os lugares das definições em `texto`, na ordem; recusa marcadores desencontrados."""
    achados = list(_RE_LUGAR.finditer(texto))
    for m in achados:
        if m.group(1) != m.group(3):
            raise ConceitosErro(
                f"definição {m.group(1)}: fecha com `fim da definição: {m.group(3)}`"
            )
    abertos = len(re.findall(r"^<!-- definição: ", texto, flags=re.M))
    if abertos != len(achados):
        raise ConceitosErro("marcador `<!-- definição: ... -->` sem o `<!-- fim da definição -->`")
    return achados


def atualizar(texto: str, definicoes: list[Definicao]) -> str:
    """`texto` com cada lugar preenchido pela definição do doc block e o índice regenerado."""
    por_nome = {d.nome: d for d in definicoes}
    achados = lugares(texto)
    nomes = [m.group(1) for m in achados]
    problemas = [
        f"doc block {n} sem lugar em {relativo(SAIDA)}" for n in por_nome if n not in nomes
    ]
    problemas += [f"lugar de definição sem doc block: {n}" for n in nomes if n not in por_nome]
    problemas += [
        f"definição {n} com mais de um lugar"
        for n in sorted({n for n in nomes if nomes.count(n) > 1})
    ]
    if problemas:
        raise ConceitosErro("; ".join(problemas))
    partes, fim = [], 0
    for m in achados:
        nome = m.group(1)
        partes += [texto[fim : m.start()], inicio_lugar(nome), "\n"]
        partes += [renderizar_definicao(por_nome[nome]), fim_lugar(nome)]
        fim = m.end()
    novo = "".join([*partes, texto[fim:]])
    inicio = novo.find(INICIO_INDICE)
    fim_indice = novo.find(FIM_INDICE, max(inicio, 0))
    if inicio < 0 or fim_indice < inicio:
        raise ConceitosErro(f"{relativo(SAIDA)}: faltam os marcadores do índice gerado")
    return novo[:inicio] + renderizar_indice(definicoes) + novo[fim_indice + len(FIM_INDICE) :]


def _numero(texto: str) -> Decimal:
    return Decimal(texto.replace(".", "").replace(",", "."))


def valores(texto: str) -> set[str]:
    """Artigos de lei, valores em R$ e números de 3 ou mais dígitos (anos e normas não contam).

    R$ e número ficam no mesmo espaço: "R$ 81 mil", "R$ 81.000,00" e "81.000" dão "81000".
    """
    achados = {re.sub(r"\s+", " ", a).replace("arts.", "art.") for a in _RE_ARTIGO.findall(texto)}
    texto = _RE_ARTIGO.sub(" ", texto)
    for numero, escala in _RE_REAIS.findall(texto):
        achados.add(str(int(_numero(numero) * _MULTIPLICADOR.get(escala, 1))))
    texto = _RE_NORMA.sub(" ", _RE_REAIS.sub(" ", texto))
    for numero in _RE_NUMERO.findall(texto):
        digitos = numero.replace(".", "")
        if not (len(numero) == 4 and 1900 <= int(digitos) <= 2099):
            achados.add(digitos)
    return achados


def repeticoes(texto: str, definicoes: list[Definicao]) -> list[str]:
    """Valores de um doc block repetidos no complemento escrito à mão da mesma subseção (RD-02)."""
    por_nome = {d.nome: d for d in definicoes}
    cortes = [m.start() for m in _RE_SUBSECAO.finditer(texto)] + [len(texto)]
    problemas = []
    for inicio, fim in zip(cortes, cortes[1:], strict=False):
        subsecao = texto[inicio:fim]
        achados = [m for m in _RE_LUGAR.finditer(subsecao) if m.group(1) in por_nome]
        if not achados:
            continue
        complemento = _RE_LUGAR.sub(" ", subsecao.split("\n", 1)[1])
        no_complemento = valores(complemento)
        for m in achados:
            repetidos = sorted(valores(por_nome[m.group(1)].texto) & no_complemento)
            if repetidos:
                titulo = subsecao.split("\n", 1)[0].lstrip("# ")
                problemas.append(
                    f"{titulo}: o complemento repete {', '.join(repetidos)} do doc block "
                    f"{m.group(1)} (a definição já os mostra: corte-os do complemento)"
                )
    return problemas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verificar", action="store_true", help="só confere se está em dia")
    parser.add_argument("--fonte", type=Path, default=FONTE)
    parser.add_argument("--saida", type=Path, default=SAIDA)
    args = parser.parse_args(argv)
    try:
        definicoes = carregar(args.fonte)
        atual = args.saida.read_text(encoding="utf-8")
        novo = atualizar(atual, definicoes)
    except ConceitosErro as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1
    problemas = repeticoes(novo, definicoes)
    for problema in problemas:
        print(f"erro: {problema}", file=sys.stderr)
    if args.verificar:
        if novo != atual:
            print(
                f"{args.saida.name} desatualizado em relação aos doc blocks: rode `make conceitos` "
                "(e `make golden`) e versione o resultado",
                file=sys.stderr,
            )
            return 1
        if not problemas:
            print(f"{args.saida.name} em dia: {len(definicoes)} definições")
        return 1 if problemas else 0
    args.saida.write_text(novo, encoding="utf-8")
    print(f"{args.saida.name}: {len(definicoes)} definições atualizadas")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
