"""Confere `docs/CAMADA_SEMANTICA.md` contra o projeto: identificadores, links e exemplos `mf`.

Uso, depois de `dbt parse` (os exemplos precisam do gold do `make ci` em `RAIZ_DADOS`):

    uv run python scripts/verificar_doc_semantica.py [--executar-exemplos]

- Todo trecho entre crases precisa existir:
  - nome da camada semântica (métrica, entidade, dimensão, modelo semântico, saved query);
  - nó do dbt (modelo, seed, fonte, macro) ou `modelo.coluna` documentada;
  - alvo do Makefile, opção do `mf` ou arquivo do repositório;
  - em último caso, texto presente em outro arquivo versionado.
  Trechos com espaços ou símbolos são quebrados em palavras, e cada uma é conferida.
- Links relativos e âncoras (`#...`) da doc precisam existir, e também os links de outras docs
  para âncoras dela.
- Com `--executar-exemplos`, roda cada `uv run mf ...` dos blocos de código e exige saída 0.

Sai com código 1 se houver pendência.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DOC = RAIZ / "docs" / "CAMADA_SEMANTICA.md"
TARGET = RAIZ / "transform" / "target"
EXCLUIDOS_DA_BUSCA = ("docs/CAMADA_SEMANTICA.md",)
IDENTIFICADOR = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
PALAVRA = re.compile(r"[^\W\d]\w*")
GRANULARIDADES = ("day", "week", "month", "quarter", "year")


def _nomes() -> dict[str, set[str]]:
    """Nomes conhecidos, por categoria, a partir dos manifestos e do Makefile."""
    semantico = json.loads((TARGET / "semantic_manifest.json").read_text(encoding="utf-8"))
    manifesto = json.loads((TARGET / "manifest.json").read_text(encoding="utf-8"))
    entidades, dimensoes, consultaveis = set(), set(), set()
    for modelo in semantico["semantic_models"]:
        entidades |= {e["name"] for e in modelo["entities"]}
        principais = {e["name"] for e in modelo["entities"] if e["type"] == "primary"}
        principais |= {modelo["primary_entity"]} if modelo.get("primary_entity") else set()
        entidades |= principais
        dimensoes |= {d["name"] for d in modelo["dimensions"]}
        consultaveis |= {f"{p}__{d['name']}" for p in principais for d in modelo["dimensions"]}
    consultaveis |= {f"metric_time__{g}" for g in GRANULARIDADES} | {"metric_time"}
    nos = list(manifesto["nodes"].values()) + list(manifesto["sources"].values())
    colunas = {f"{no['name']}.{c}" for no in nos for c in no.get("columns", {})}
    makefile = (RAIZ / "Makefile").read_text(encoding="utf-8")
    return {
        "camada semântica": (
            {m["name"] for m in semantico["metrics"]}
            | entidades
            | dimensoes
            | consultaveis
            | {m["name"] for m in semantico["semantic_models"]}
            | {q["name"] for q in semantico["saved_queries"]}
        ),
        "nó dbt": {no["name"] for no in nos}
        | {m["name"].removeprefix("test_") for m in manifesto["macros"].values()},
        "modelo.coluna": colunas,
        "coluna dbt": {c.split(".", 1)[1] for c in colunas},
        "alvo make": set(re.findall(r"^([a-z][\w-]*):", makefile, flags=re.M)),
    }


def _no_repositorio(texto: str) -> bool:
    """`texto` aparece em algum arquivo versionado além da própria doc."""
    palavra = ["-w"] if IDENTIFICADOR.fullmatch(texto) else []
    excluidos = [f":!{c}" for c in EXCLUIDOS_DA_BUSCA]
    resultado = subprocess.run(
        ["git", "grep", "--untracked", "-q", "-F", *palavra, "-e", texto, "--", ".", *excluidos],
        cwd=RAIZ, check=False,
    )  # fmt: skip
    return resultado.returncode == 0


def _caminho(texto: str) -> bool:
    """Caminho relativo à raiz, a `transform/` ou a `docs/`, ou nome de arquivo do repositório."""
    candidato = texto.rstrip("/")
    if any((base / candidato).exists() for base in (RAIZ, RAIZ / "transform", RAIZ / "docs")):
        return True
    arquivos = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=RAIZ, capture_output=True, text=True, check=True,
    ).stdout.split()  # fmt: skip
    return "/" not in candidato and any(Path(a).name == candidato for a in arquivos)


def _opcao_mf(opcao: str) -> bool:
    """Opção de linha de comando do `mf query`."""
    ajuda = subprocess.run(
        ["uv", "run", "mf", "query", "--help"], cwd=RAIZ / "transform", capture_output=True,
        text=True, check=False,
    ).stdout  # fmt: skip
    return re.search(rf"(?<![\w-]){re.escape(opcao)}\b", ajuda) is not None


def classificar(trecho: str, nomes: dict[str, set[str]]) -> list[tuple[str, str]]:
    """[(texto conferido, categoria)]; categoria "PENDENTE" quando não existe."""
    if trecho.startswith(("uv run mf", "mf ", "dbt ")):
        return [(trecho, "comando (exemplos executados à parte)")]
    if trecho.startswith("make "):
        alvos = trecho.split()[1:]
        return [(a, "alvo make" if a in nomes["alvo make"] else "PENDENTE") for a in alvos]
    if trecho.startswith("--"):
        return [(trecho, "opção do mf" if _opcao_mf(trecho) else "PENDENTE")]
    if re.search(r"\{[\d,]+\}", trecho):  # `elegiveis_{1,3,5}a` -> elegiveis_1a, elegiveis_3a...
        prefixo, opcoes, sufixo = re.match(r"(.*)\{([\d,]+)\}(.*)", trecho).groups()
        return [i for o in opcoes.split(",") for i in classificar(prefixo + o + sufixo, nomes)]
    if " " not in trecho and re.search(r"[/.]\w+$", trecho) and _caminho(trecho):
        return [(trecho, "arquivo")]
    for categoria in ("camada semântica", "nó dbt", "modelo.coluna", "coluna dbt", "alvo make"):
        if trecho in nomes[categoria]:
            return [(trecho, categoria)]
    # palavra, código ou literal em maiúsculas (`-1`, `N/A`, `NÃO INFORMADO`): busca o texto inteiro
    if re.fullmatch(r"[\w.\-]+", trecho) or re.fullmatch(r"[A-ZÀ-Ý0-9/ \-]+", trecho):
        if _no_repositorio(trecho):
            return [(trecho, "repositório")]
        if "." in trecho.strip("."):  # chave YAML aninhada (`derived_semantics.dimensions`)
            return [i for parte in trecho.split(".") for i in classificar(parte, nomes)]
        return [(trecho, "PENDENTE")]
    return [
        item
        for token in dict.fromkeys(PALAVRA.findall(trecho))
        if len(token) > 1
        for item in classificar(token, nomes)
    ]


def _slug(titulo: str) -> str:
    """Âncora no estilo do GitHub."""
    return re.sub(r"[^\w\- ]", "", titulo.strip().lower()).replace(" ", "-")


def verificar_links(texto: str) -> list[str]:
    ancoras = {_slug(t) for t in re.findall(r"^#{1,6} (.+)$", texto, flags=re.M)}
    pendencias = []
    for alvo in re.findall(r"\]\(([^)\s]+)\)", texto):
        if alvo.startswith("http"):
            continue
        arquivo, _, ancora = alvo.partition("#")
        if arquivo and not (DOC.parent / arquivo).exists():
            pendencias.append(f"link para arquivo inexistente: {alvo}")
        elif not arquivo and ancora not in ancoras:
            pendencias.append(f"âncora inexistente: #{ancora}")
    for outro in RAIZ.joinpath("docs").rglob("*.md"):
        conteudo = outro.read_text(encoding="utf-8")
        for ancora in re.findall(r"CAMADA_SEMANTICA\.md#([^)\s]+)", conteudo):
            if ancora not in ancoras:
                pendencias.append(f"{outro.relative_to(RAIZ)}: âncora inexistente #{ancora}")
    return pendencias


def exemplos_mf(texto: str) -> list[str]:
    """Comandos `uv run mf ...` dos blocos de código, com as continuações de linha unidas."""
    comandos = []
    for bloco in re.findall(r"```bash\n(.*?)```", texto, flags=re.S):
        for linha in bloco.replace("\\\n", " ").splitlines():
            if linha.strip().startswith("uv run mf"):
                comandos.append(linha.strip())
    return comandos


def executar(comando: str) -> tuple[bool, str]:
    args = shlex.split(comando, comments=True)
    with tempfile.TemporaryDirectory() as pasta:
        if "--csv" in args:  # não suja transform/ com o CSV do exemplo
            args[args.index("--csv") + 1] = str(Path(pasta) / "saida.csv")
        env = os.environ | {"DBT_PROFILES_DIR": str(RAIZ / "transform")}
        resultado = subprocess.run(
            args, cwd=RAIZ / "transform", env=env, capture_output=True, text=True, check=False
        )
    return resultado.returncode == 0, (resultado.stdout + resultado.stderr)[-500:]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--executar-exemplos", action="store_true")
    opcoes = parser.parse_args()
    texto = DOC.read_text(encoding="utf-8")
    nomes = _nomes()
    sem_blocos = re.sub(r"```.*?```", "", texto, flags=re.S)
    trechos = list(dict.fromkeys(re.findall(r"`([^`\n]+)`", sem_blocos)))
    conferidos = [item for trecho in trechos for item in classificar(trecho, nomes)]
    pendencias = [f"identificador inexistente: `{t}`" for t, c in conferidos if c == "PENDENTE"]
    pendencias += verificar_links(texto)
    print(f"Trechos entre crases: {len(trechos)}; itens conferidos: {len(conferidos)}")
    for categoria, total in Counter(c for _, c in conferidos).most_common():
        print(f"  {categoria}: {total}")
    so_no_texto = sorted({t for t, c in conferidos if c == "repositório"})
    print("  só no texto do repositório:", ", ".join(so_no_texto))
    if opcoes.executar_exemplos:
        comandos = exemplos_mf(texto)
        print(f"Exemplos `mf`: {len(comandos)}")
        for comando in comandos:
            ok, saida = executar(comando)
            print(f"  [{'ok' if ok else 'FALHOU'}] {comando}")
            if not ok:
                pendencias.append(f"exemplo falhou: {comando}\n{saida}")
    print(f"Pendências: {len(pendencias)}")
    for pendencia in pendencias:
        print(f"  - {pendencia}")
    return 1 if pendencias else 0


if __name__ == "__main__":
    sys.exit(main())
