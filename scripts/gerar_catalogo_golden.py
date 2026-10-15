# ruff: noqa: E501  (textos longos do índice)
"""Gera o catálogo das golden queries (ADR-0023): `docs/referencia/golden_queries/catalogo.json` e o índice do guia.

Uso: `make golden` (compila as analyses de `transform/analyses/golden/` sobre o warehouse do `make ci` e roda este
script) ou `uv run python scripts/gerar_catalogo_golden.py`. Com `--verificar` não escreve nada: gera em memória e
falha (código 1) se o catálogo, o bloco gerado de `docs/uso/consulta-agente.md` ou o de tamanhos de
`docs/uso/construcao-agente.md` estiverem desatualizados.

Fontes:
- o cabeçalho YAML de cada golden query SQL, num comentário Jinja `{# --- ... --- #}` no início do arquivo;
- o SQL **compilado** pelo dbt (`ref()` e `source()` resolvidos), normalizado para ser portável: o banco local
  (`"warehouse"."main"."x"`) vira `main.x` e o caminho absoluto de `RAIZ_DADOS` (nos `read_parquet` das fontes
  raw) vira o marcador `${RAIZ_DADOS}`;
- `docs/referencia/golden_queries/semantica.yml`, as golden queries da camada semântica (comandos `mf query`), com o SQL que
  o MetricFlow gera para cada uma (`mf query --explain` sobre uma cópia do warehouse, normalizado como o compilado);
- `docs/referencia/golden_queries/matriz.yml`, a matriz conceito × camada com o motivo de cada célula sem query;
- os doc blocks do dbt (`transform/models/docs/conceitos.md`, lidos por `gerar_conceitos.py`): a definição curta de
  cada conceito, embutida em `conceitos[].definicoes` para o agente, que só recebe o guia e o catálogo.

As funções de validação (cabeçalho, cobertura da matriz, colunas proibidas) também são usadas pelos testes.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterator
from decimal import Decimal
from pathlib import Path

import yaml
from gerar_conceitos import Definicao
from gerar_conceitos import carregar as carregar_definicoes

from rfb_pipeline import __version__
from rfb_pipeline.caminhos import (
    DOC_BLOCKS_CONCEITOS,
    GOLDEN_CATALOGO,
    GOLDEN_MATRIZ,
    GOLDEN_SEMANTICA,
    GUIA_CONSTRUCAO_AGENTE,
    GUIA_CONSULTA,
    RAIZ_REPO,
    link_de,
    relativo,
)

RAIZ = RAIZ_REPO
DIR_TRANSFORM = RAIZ / "transform"
SUBPASTA = "golden"
DIR_GOLDEN = DIR_TRANSFORM / "analyses" / SUBPASTA
MATRIZ = GOLDEN_MATRIZ
SEMANTICA = GOLDEN_SEMANTICA
CATALOGO = GOLDEN_CATALOGO
GUIA = GUIA_CONSULTA
CONSTRUCAO = GUIA_CONSTRUCAO_AGENTE
PADRAO_ARQUIVO = "gq_*.sql"

CAMADAS = ("raw", "staging", "intermediate", "core", "analytics", "original", "semantica")
CAMPOS_COMUNS = (
    "id", "conceito", "camada", "perguntas", "intencao", "armadilhas", "variacoes",
    "resposta_esperada_fixtures",
)  # fmt: skip
CAMPOS_SQL = (*CAMPOS_COMUNS, "tabelas", "colunas_chave")
PRIVACIDADES = ("agregado", "identifica_estabelecimento")
MARCADOR_RAIZ = "${RAIZ_DADOS}"
INICIO_BLOCO = "<!-- INÍCIO do bloco gerado por scripts/gerar_catalogo_golden.py (make golden): não edite à mão -->"
FIM_BLOCO = "<!-- FIM do bloco gerado -->"
INICIO_ESQUEMA = "<!-- INÍCIO do bloco gerado do esquema por scripts/gerar_catalogo_golden.py (make golden): não edite à mão -->"
FIM_ESQUEMA = "<!-- FIM do bloco gerado do esquema -->"
INICIO_TAMANHOS = "<!-- INÍCIO do bloco gerado dos tamanhos por scripts/gerar_catalogo_golden.py (make golden): não edite à mão -->"
FIM_TAMANHOS = "<!-- FIM do bloco gerado dos tamanhos -->"

_RE_CABECALHO = re.compile(r"\A\{#\s*---\n(.*?)\n---\s*#\}", re.S)
_RE_NOME = re.compile(r"^gq_([a-z]+)__([a-z_]+?)__(\d{2})$")
_RE_REF = re.compile(r"ref\(\s*'([^']+)'\s*\)")
_RE_SOURCE = re.compile(r"source\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)")
_RE_RELACAO_LOCAL = re.compile(r'"[^"]+"\."(main)"\."([A-Za-z0-9_]+)"')
_RE_RELACAO_PORTAVEL = re.compile(r"\bmain\.([a-z_][a-z0-9_]*)\b")
_RE_ID_CITADO = re.compile(r"\bgq_[a-z]+__[a-z_]+?__\d{2}\b")

# ADR-0008: nenhuma golden query devolve nome, CPF, contato ou endereço (o endereço fica só no staging). O CNPJ
# (completo ou básico) só sai com `privacidade: identifica_estabelecimento`, quando a pergunta pede o
# estabelecimento identificado.
_COLUNAS_PROIBIDAS = re.compile(
    r"(^|_)(nome|razao_social|nome_fantasia|cpf|email|correio|telefone|tel|ddd|ddd_fax|fax|"
    r"logradouro|tipo_logradouro|numero|complemento|bairro|cep|socio|socios)\d*(_|$)"
)
# Colunas de nome de lugar ou de categoria, que não são de pessoa: permitidas apesar do prefixo `nome` (e o número do
# dia da semana, que não é o número do endereço).
_NOMES_PERMITIDOS = re.compile(
    r"^nome_(municipio|uf|regiao|mesorregiao|microrregiao|regiao_intermediaria|regiao_imediata|"
    r"regiao_metropolitana|municipio_polo_compras|municipio_vizinho|municipio_origem|municipio_destino|"
    r"mes|classe_cnae)$|^dia_semana_numero$"
)
# CNPJ completo ou básico, pelo nome: `cnpj*` e `*_raiz` (a raiz é o CNPJ básico, ex. `maior_raiz`), RGQ-04.
_COLUNAS_CNPJ = re.compile(r"(^|_)(cnpj|raiz)(_|$)")
# Relações em que `nome` é nome de lugar (o município da Base dos Dados), não de pessoa: a linhagem as aceita.
_RELACOES_DE_LUGAR = re.compile(r"munic|(^|_)uf(_|$)|regi")


class CatalogoErro(Exception):
    """Golden query, matriz ou catálogo fora do padrão."""


# ---------------------------------------------------------------------------------------------------------------
# Leitura e validação


def ler_cabecalho(texto: str, origem: str = "") -> dict:
    """O cabeçalho YAML do comentário Jinja `{# --- ... --- #}` que abre o arquivo."""
    achado = _RE_CABECALHO.match(texto)
    if achado is None:
        raise CatalogoErro(
            f"{origem}: falta o cabeçalho `{{# --- ... --- #}}` no início do arquivo"
        )
    dados = yaml.safe_load(achado.group(1))
    if not isinstance(dados, dict):
        raise CatalogoErro(f"{origem}: o cabeçalho não é um mapa YAML")
    return dados


def relacoes_do_sql_portavel(sql: str) -> list[str]:
    """Relações `main.<x>` lidas pelo SQL portável (o do catálogo), sem o `main.`: as `tabelas` da semântica."""
    return sorted(set(_RE_RELACAO_PORTAVEL.findall(sql)))


def tabelas_do_sql(sql: str) -> set[str]:
    """Relações citadas por `ref('x')` (x) e `source('a', 'b')` (a.b) no SQL fonte."""
    return set(_RE_REF.findall(sql)) | {f"{a}.{b}" for a, b in _RE_SOURCE.findall(sql)}


def _lista_de_textos(valor: object) -> bool:
    return (
        isinstance(valor, list)
        and bool(valor)
        and all(isinstance(x, str) and x.strip() for x in valor)
    )


def _validar_resposta(resposta: object) -> list[str]:
    if not isinstance(resposta, dict) or set(resposta) != {"colunas", "linhas"}:
        return ["`resposta_esperada_fixtures` deve ter exatamente `colunas` e `linhas`"]
    colunas, linhas = resposta["colunas"], resposta["linhas"]
    if colunas == [] and linhas == []:  # resultado vazio (o `mf` não grava CSV sem linhas)
        return []
    if not _lista_de_textos(colunas):
        return ["`resposta_esperada_fixtures.colunas` deve ser uma lista de nomes"]
    if not isinstance(linhas, list) or any(
        not isinstance(x, list) or len(x) != len(colunas) for x in linhas
    ):
        return [
            "`resposta_esperada_fixtures.linhas` deve ser uma lista de linhas do tamanho de `colunas`"
        ]
    return []


def validar_comum(cab: dict, conceitos: set[str]) -> list[str]:
    """Regras do cabeçalho comuns às golden queries SQL e às da camada semântica."""
    problemas: list[str] = []
    if cab.get("camada") not in CAMADAS:
        problemas.append(f"camada inválida {cab.get('camada')!r} (válidas: {', '.join(CAMADAS)})")
    if cab.get("conceito") not in conceitos:
        problemas.append(f"conceito {cab.get('conceito')!r} fora da matriz ({relativo(MATRIZ)})")
    perguntas = cab.get("perguntas")
    if not _lista_de_textos(perguntas) or not 2 <= len(perguntas) <= 4:
        problemas.append("`perguntas` deve ter de 2 a 4 formulações")
    for campo in ("armadilhas", "variacoes"):
        if not _lista_de_textos(cab.get(campo)):
            problemas.append(f"`{campo}` deve ser uma lista não vazia de textos")
    if not isinstance(cab.get("intencao"), str) or not cab["intencao"].strip():
        problemas.append("`intencao` deve ser uma frase")
    if cab.get("privacidade", "agregado") not in PRIVACIDADES:
        problemas.append(f"`privacidade` inválida (válidas: {', '.join(PRIVACIDADES)})")
    if "resposta_esperada_fixtures" in cab:
        problemas += _validar_resposta(cab["resposta_esperada_fixtures"])
    return problemas


def validar_cabecalho(cab: dict, nome: str, sql: str, conceitos: set[str]) -> list[str]:
    """Problemas do cabeçalho de uma golden query SQL (`nome` = nome do arquivo sem `.sql`)."""
    faltando = [c for c in CAMPOS_SQL if c not in cab]
    problemas = [f"faltam os campos {', '.join(faltando)}"] if faltando else []
    problemas += validar_comum(cab, conceitos)
    partes = _RE_NOME.match(nome)
    if partes is None:
        problemas.append("nome fora do padrão `gq_<camada>__<conceito>__<nn>`")
    else:
        if cab.get("id") != nome:
            problemas.append(f"`id` {cab.get('id')!r} difere do nome do arquivo")
        if partes.group(1) != cab.get("camada") or partes.group(2) != cab.get("conceito"):
            problemas.append("camada ou conceito do nome do arquivo diferem do cabeçalho")
    if cab.get("camada") == "semantica":
        problemas.append(f"a camada `semantica` fica em {relativo(SEMANTICA)}, não em SQL")
    for campo in ("tabelas", "colunas_chave"):
        if not _lista_de_textos(cab.get(campo)):
            problemas.append(f"`{campo}` deve ser uma lista não vazia de nomes")
    corpo = _RE_CABECALHO.sub("", sql)
    if _lista_de_textos(cab.get("tabelas")) and set(cab["tabelas"]) != tabelas_do_sql(corpo):
        problemas.append(
            f"`tabelas` {sorted(cab['tabelas'])} difere das relações do SQL {sorted(tabelas_do_sql(corpo))}"
        )
    if not re.search(r"golden_query", corpo) or not re.search(
        r"escopo['\"]?\s*:\s*['\"]adicao", corpo
    ):
        problemas.append("a config deve ter a tag `golden_query` e `meta.escopo: adicao`")
    if not re.search(r"\border\s+by\b", corpo, re.I):
        problemas.append("o SQL precisa de `order by`: a resposta esperada é comparada na ordem")
    problemas += municipio_sem_uf(corpo)
    problemas += case_argmax_com_else(corpo)
    problemas += media_de_razoes(corpo)
    return [f"{nome}: {p}" for p in problemas]


_RE_FILTRO_MUNICIPIO = re.compile(r"\b(nome_municipio|municipio)\s*(=|in\b|like\b)\s*\(?\s*'", re.I)
_RE_FILTRO_UF = re.compile(r"\b(sigla_uf|uf)\s*(=|in\b)\s*\(?\s*'", re.I)


def municipio_sem_uf(sql: str) -> list[str]:
    """SQL que filtra o município pelo nome sem filtrar a UF (RGQ-08): há homônimos (Água Branca em AL, PB e PI)."""
    if _RE_FILTRO_MUNICIPIO.search(sql) and not _RE_FILTRO_UF.search(sql):
        return [
            "filtra o município pelo nome sem filtrar a UF (homônimos: Água Branca em AL, PB e PI)"
        ]
    return []


_RE_COMENTARIO_OU_TEXTO = re.compile(r"\{#.*?#\}|--[^\n]*|'(?:[^']|'')*'", re.S)
_RE_CASE_OU_END = re.compile(r"\b(case|end)\b", re.I)
_RE_MAIOR_OU_MENOR = re.compile(r"\b(greatest|least)\s*\(", re.I)
_RE_ELSE_TEXTO = re.compile(r"\belse\s+'", re.I)
# `avg` sobre coluna que já é média, taxa ou percentual: a reagregação sem peso (Greptile PR #8). A mediana fica de
# fora: a mediana dos municípios é uma estatística da distribuição deles, não uma estimativa do total.
_RE_MEDIA_DE_RAZAO = re.compile(
    r"\b(avg|mean)\s*\(\s*(distinct\s+)?([\w]+\.)?"
    r"(\w*(media|medio|mediana|pct|taxa|razao|percentual|por_10k|per_capita|indice)\w*)\s*\)",
    re.I,
)


def case_argmax_com_else(sql: str) -> list[str]:
    """`CASE` de maior/menor valor (`greatest`/`least`) com `else '<categoria>'` (Greptile PR #8).

    O `else` transforma a ausência de dado (todos os valores NULL, nenhum ramo casa) numa categoria: um município
    sem VA vira "administração pública". Cada ramo deve testar a sua categoria, sem `else`, e a falta sair NULL.
    """
    limpo = _RE_COMENTARIO_OU_TEXTO.sub(lambda m: "'x'" if m.group(0).startswith("'") else " ", sql)
    inicios: list[int] = []
    problemas = []
    for achado in _RE_CASE_OU_END.finditer(limpo):
        if achado.group(1).lower() == "case":
            inicios.append(achado.start())
        elif inicios:
            bloco = limpo[inicios.pop() : achado.end()]
            if _RE_MAIOR_OU_MENOR.search(bloco) and _RE_ELSE_TEXTO.search(bloco):
                problemas.append(
                    "CASE de greatest/least com `else '<categoria>'`: sem dado, a falta vira categoria; "
                    "teste cada ramo e deixe sair NULL"
                )
    return problemas


def media_de_razoes(sql: str) -> list[str]:
    """`avg` sobre coluna que já é média, taxa ou percentual: reagregar exige ponderar (Greptile PR #8)."""
    limpo = _RE_COMENTARIO_OU_TEXTO.sub(lambda m: "'x'" if m.group(0).startswith("'") else " ", sql)
    return [
        f"`{achado.group(0)}` reagrega {achado.group(4)} sem peso: pondere (soma do numerador ÷ soma do denominador)"
        for achado in _RE_MEDIA_DE_RAZAO.finditer(limpo)
    ]


def validar_semantica(entrada: dict, conceitos: set[str]) -> list[str]:
    """Problemas de uma golden query da camada semântica (`semantica.yml`)."""
    nome = entrada.get("id", "?")
    faltando = [c for c in CAMPOS_COMUNS if c not in entrada]
    problemas = [f"faltam os campos {', '.join(faltando)}"] if faltando else []
    problemas += validar_comum(entrada, conceitos)
    if entrada.get("camada") != "semantica":
        problemas.append("camada deve ser `semantica`")
    partes = _RE_NOME.match(str(nome))
    if (
        partes is None
        or partes.group(1) != "semantica"
        or partes.group(2) != entrada.get("conceito")
    ):
        problemas.append("`id` fora do padrão `gq_semantica__<conceito>__<nn>`")
    if bool(entrada.get("saved_query")) == bool(entrada.get("metricas")):
        problemas.append("use `saved_query` ou `metricas`, um dos dois")
    if entrada.get("metricas") is not None and not _lista_de_textos(entrada.get("metricas")):
        problemas.append("`metricas` deve ser uma lista de nomes")
    if entrada.get("group_by") is not None and not _lista_de_textos(entrada.get("group_by")):
        problemas.append("`group_by` deve ser uma lista de dimensões")
    if entrada.get("saved_query") and (entrada.get("group_by") or entrada.get("where")):
        problemas.append("`saved_query` não leva `group_by` nem `where`")
    return [f"{nome}: {p}" for p in problemas]


def argumentos_mf(entrada: dict) -> list[str]:
    """Argumentos de `mf query` de uma golden query semântica (sem `--csv`)."""
    if entrada.get("saved_query"):
        return ["--saved-query", entrada["saved_query"]]
    args = ["--metrics", ",".join(entrada["metricas"])]
    if entrada.get("group_by"):
        args += ["--group-by", ",".join(entrada["group_by"])]
    if entrada.get("where"):
        args += ["--where", entrada["where"]]
    return args


def comando_mf(entrada: dict) -> str:
    """Linha de comando legível (rodar em `transform/`): aspas duplas quando bastam, como na documentação."""

    def _citar(arg: str) -> str:
        if re.fullmatch(r"[\w.,:/=-]+", arg):
            return arg
        return f'"{arg}"' if not re.search(r'["$`\\]', arg) else shlex.quote(arg)

    return "uv run mf query " + " ".join(_citar(a) for a in argumentos_mf(entrada))


def problemas_de_cobertura(matriz: dict, ids: list[str]) -> list[str]:
    """Toda célula conceito × camada tem golden query ou motivo, nunca os dois; motivos citam ids que existem."""
    conceitos = [c["id"] for c in matriz["conceitos"]]
    camadas = [c["id"] for c in matriz["camadas"]]
    problemas: list[str] = []
    if tuple(camadas) != CAMADAS:
        problemas.append(f"matriz: camadas {camadas} != {list(CAMADAS)}")
    repetidos = sorted({i for i in ids if ids.count(i) > 1})
    if repetidos:
        problemas.append(f"ids repetidos: {', '.join(repetidos)}")
    cobertas = set()
    for i in ids:
        partes = _RE_NOME.match(i)
        if partes:
            cobertas.add((partes.group(2), partes.group(1)))
    motivos = matriz.get("sem_query") or {}
    for conceito, por_camada in motivos.items():
        if conceito not in conceitos:
            problemas.append(f"sem_query: conceito {conceito!r} fora da lista de conceitos")
            continue
        for camada, motivo in (por_camada or {}).items():
            if camada not in camadas:
                problemas.append(f"sem_query: {conceito} × camada {camada!r} inválida")
            elif not isinstance(motivo, str) or not motivo.strip():
                problemas.append(f"sem_query: {conceito} × {camada} sem texto de motivo")
            if (conceito, camada) in cobertas:
                problemas.append(f"{conceito} × {camada}: tem golden query e motivo ao mesmo tempo")
            for citado in _RE_ID_CITADO.findall(str(motivo)):
                if citado not in ids:
                    problemas.append(
                        f"sem_query: {conceito} × {camada} cita {citado}, que não existe"
                    )
    for conceito in conceitos:
        for camada in camadas:
            if (conceito, camada) not in cobertas and camada not in (motivos.get(conceito) or {}):
                problemas.append(f"{conceito} × {camada}: sem golden query e sem motivo")
    return problemas


def colunas_proibidas(colunas: list[str], privacidade: str = "agregado") -> list[str]:
    """Colunas de saída que expõem pessoa, contato ou endereço (ADR-0008), ou CNPJ sem `identifica_estabelecimento`."""
    proibidas = []
    for coluna in colunas:
        nome = coluna.lower().rsplit("__", 1)[-1]  # dimensão do MetricFlow: `<entidade>__<coluna>`
        if _COLUNAS_PROIBIDAS.search(nome) and not _NOMES_PERMITIDOS.match(nome):
            proibidas.append(coluna)
        elif _COLUNAS_CNPJ.search(nome) and privacidade != "identifica_estabelecimento":
            proibidas.append(coluna)
    return proibidas


# CPF mascarado como a RFB e o staging o deixam no nome do empresário individual (`***.***.***-**`, ou com os
# dígitos do meio): um valor com isso é nome de pessoa (ADR-0008).
RE_CPF_MASCARADO = re.compile(r"\*{3}\.?[\d*]{3}\.?[\d*]{3}-?\*{2}")


def _dv_valido(digitos: str, pesos: list[list[int]]) -> bool:
    """Dígitos verificadores módulo 11 de CPF ou CNPJ (os dois últimos de `digitos`)."""
    corpo = [int(d) for d in digitos]
    for i, peso in enumerate(pesos):
        n = len(digitos) - 2 + i
        resto = sum(a * b for a, b in zip(corpo[:n], peso, strict=True)) % 11
        if corpo[n] != (0 if resto < 2 else 11 - resto):
            return False
    return len(set(digitos)) > 1


def numero_identificador(valor: int) -> bool:
    """Se um inteiro é CPF (11 dígitos) ou CNPJ (14 dígitos, ou 13/10 sem o zero à esquerda) com DV válido."""
    texto = str(abs(valor))
    cnpj, cpf = texto.zfill(14), texto.zfill(11)
    pesos_cnpj = [[5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]]
    pesos_cpf = [list(range(10, 1, -1)), list(range(11, 1, -1))]
    return (12 <= len(texto) <= 14 and _dv_valido(cnpj, pesos_cnpj)) or (
        9 <= len(texto) <= 11 and _dv_valido(cpf, pesos_cpf)
    )


def _coluna_contada(coluna: object) -> bool:
    """Se a referência à coluna está dentro de `count(...)`, de um teste `is [not] null` ou de um `filter (where ...)`:
    o valor dela não sai, só a contagem ou o recorte."""
    from sqlglot import exp

    no = coluna.parent
    while no is not None:
        if isinstance(no, exp.Count | exp.Is | exp.Where):
            return True
        no = no.parent
    return False


def colunas_derivadas_proibidas(sql: str, privacidade: str = "agregado") -> list[str]:
    """Colunas de saída do SQL que vêm de uma coluna proibida (ADR-0008), mesmo com alias, função ou CTE (RGQ-04).

    Segue a linhagem de cada coluna da saída (sqlglot, dialeto DuckDB) até as relações de origem. A saída é
    proibida se algum caminho chega a uma coluna proibida pelo nome (`colunas_proibidas`: `nome`, `cpf`, contato,
    endereço e, sem `identifica_estabelecimento`, `cnpj*`/`*_raiz`) sem passar por `count(...)`, `is [not] null` ou
    `filter (where ...)`.
    Assim `min(nome) as titular` e `max(left(cnpj_completo, 8)::bigint) as maior_raiz` são recusados, e
    `count(distinct cnpj_completo)` e o `CASE WHEN cnpj_completo IS NULL` do MetricFlow passam. SQL que o sqlglot
    não analisa também é recusado.
    """
    import sqlglot
    from sqlglot import exp
    from sqlglot.lineage import lineage

    try:
        arvore = sqlglot.parse_one(sql, read="duckdb")
        saidas = [p.alias_or_name for p in arvore.selects]
    except Exception as exc:  # noqa: BLE001 — falha fechada: SQL não analisado é recusado
        return [f"(SQL que a guarda de linhagem não analisa: {exc})"]
    proibidas: list[str] = []
    for saida in saidas:
        try:
            raiz = lineage(saida, arvore, dialect="duckdb")
        except Exception as exc:  # noqa: BLE001 — falha fechada
            proibidas.append(f"{saida} (linhagem não analisada: {exc})")
            continue
        pendentes = [(raiz, False)]
        while pendentes:
            no, contado = pendentes.pop()
            if not no.downstream:
                relacao = no.source.name if isinstance(no.source, exp.Table) else ""
                coluna = no.name.rsplit(".", 1)[-1]
                de_lugar = coluna == "nome" and _RELACOES_DE_LUGAR.search(relacao)
                if not contado and not de_lugar and colunas_proibidas([coluna], privacidade):
                    proibidas.append(f"{saida} (de {relacao}.{coluna})")
                continue
            for filho in no.downstream:
                nome = (
                    filho.name.rsplit(".", 1)[-1]
                    if not filho.downstream
                    else filho.expression.alias_or_name
                )
                refs = [c for c in no.expression.find_all(exp.Column) if c.name == nome]
                pendentes.append(
                    (filho, contado or (bool(refs) and all(_coluna_contada(c) for c in refs)))
                )
    return sorted(set(proibidas))


# ---------------------------------------------------------------------------------------------------------------
# Resultado e SQL compilado


def normalizar_valor(valor: object) -> object:
    """Valor de resultado em forma estável para YAML/JSON: decimal e float com 6 casas, data em ISO."""
    if isinstance(valor, bool) or valor is None or isinstance(valor, int | str):
        return valor
    if isinstance(valor, Decimal | float):
        return round(float(valor), 6)
    if isinstance(valor, dt.date | dt.datetime):
        return valor.isoformat()
    return str(valor)


def normalizar_resultado(colunas: list[str], linhas: list[tuple]) -> dict:
    return {
        "colunas": list(colunas),
        "linhas": [[normalizar_valor(v) for v in linha] for linha in linhas],
    }


_RE_INTEIRO = re.compile(r"^-?\d+$")
_RE_DECIMAL = re.compile(r"^-?\d+\.\d+(e-?\d+)?$")
_RE_MEIA_NOITE = re.compile(r"^(\d{4}-\d{2}-\d{2})[ T]00:00:00$")


def normalizar_texto_mf(valor: str) -> object:
    """Célula do CSV do `mf query` em forma estável: vazio = null, data sem hora, número como número."""
    if valor == "":
        return None
    if valor in ("True", "False"):
        return valor == "True"
    if _RE_INTEIRO.match(valor):
        return int(valor)
    if _RE_DECIMAL.match(valor):
        return round(float(valor), 6)
    data = _RE_MEIA_NOITE.match(valor)
    return data.group(1) if data else valor


def resultado_mf(colunas: list[str], linhas: list[list[str]]) -> dict:
    """Resultado do `mf query` normalizado, com as linhas ordenadas (o MetricFlow não garante a ordem)."""
    normalizadas = [[normalizar_texto_mf(v) for v in linha] for linha in linhas]
    normalizadas.sort(key=lambda linha: [("" if v is None else str(v)) for v in linha])
    return {"colunas": list(colunas), "linhas": normalizadas}


def resultado_sql_semantico(colunas: list[str], linhas: list[tuple]) -> dict:
    """Resultado do SQL gerado pelo MetricFlow na mesma forma do CSV do `mf query`.

    Cada valor passa pelo texto que o `mf` gravaria (`2026-08-01 00:00:00` vira `2026-08-01`, `'47415'` vira número)
    e as linhas são ordenadas; consulta sem linhas = `{"colunas": [], "linhas": []}`, como o `mf`, que não grava CSV.
    """
    if not linhas:
        return {"colunas": [], "linhas": []}
    textos = [["" if v is None else str(v) for v in linha] for linha in linhas]
    return resultado_mf(colunas, textos)


@contextlib.contextmanager
def mf_sobre_copia(raiz_dados: Path) -> Iterator[Callable[[list[str]], str]]:
    """Função que roda `mf <args>` (em `transform/`) sobre uma **cópia** do `warehouse.duckdb` e devolve o stdout.

    O `mf` abre o warehouse pelo perfil do dbt, em modo de **escrita** (RGQ-01): a cópia (`CAMINHO_DUCKDB`) garante
    que o original de `raiz_dados` nunca é aberto para escrita nem bloqueado.
    """
    with tempfile.TemporaryDirectory(prefix="rfb-golden-mf-") as temporario:
        # Mesmo nome do arquivo: o catálogo do DuckDB continua "warehouse" e a normalização vale igual.
        copia = Path(temporario) / "warehouse.duckdb"
        shutil.copyfile(Path(raiz_dados) / "warehouse.duckdb", copia)
        env = os.environ | {
            "RAIZ_DADOS": str(raiz_dados), "DBT_PROFILES_DIR": str(DIR_TRANSFORM), "CAMINHO_DUCKDB": str(copia),
        }  # fmt: skip

        def rodar(args: list[str]) -> str:
            feito = subprocess.run(
                ["uv", "run", "mf", *args], cwd=DIR_TRANSFORM, env=env, capture_output=True, text=True, check=False
            )  # fmt: skip
            if feito.returncode != 0:
                raise CatalogoErro(
                    f"`mf {' '.join(args)}` falhou:\n{feito.stdout[-1500:]}{feito.stderr[-1500:]}"
                )
            return feito.stdout

        yield rodar


def sql_semantico(semantica: list[dict], raiz_dados: Path) -> dict[str, str]:
    """`{id: SQL}` que o MetricFlow gera (`mf query --explain`) para cada golden query semântica, normalizado.

    Roda sobre uma cópia do warehouse (`mf_sobre_copia`). O SQL gerado só lê `main.<relação>`.
    """
    resultado: dict[str, str] = {}
    with mf_sobre_copia(raiz_dados) as mf:
        for entrada in semantica:
            sql = mf(["query", "--quiet", "--explain", *argumentos_mf(entrada)]).strip()
            if not re.match(r"(?i)(select|with)\b", sql):
                raise CatalogoErro(
                    f"{entrada['id']}: `mf query --explain` não devolveu SQL:\n{sql[-1500:]}"
                )
            resultado[entrada["id"]] = normalizar_sql(sql, raiz_dados)
    return resultado


def normalizar_sql(sql: str, raiz_dados: str | Path | None) -> str:
    """SQL compilado portável: `main.<relação>` e `${RAIZ_DADOS}` no lugar do caminho da máquina."""
    texto = sql
    if raiz_dados:
        texto = texto.replace(str(Path(raiz_dados).resolve()), MARCADOR_RAIZ)
        texto = texto.replace(str(raiz_dados), MARCADOR_RAIZ)
    texto = _RE_RELACAO_LOCAL.sub(r"\1.\2", texto)
    linhas = [linha.rstrip() for linha in texto.strip().splitlines()]
    return "\n".join(linhas) + "\n"


def caminho_absoluto_no_sql(sql: str) -> bool:
    """Se sobrou caminho absoluto da máquina (`/Users/...`, `/home/...`, `C:\\...`) no SQL."""
    return bool(re.search(r"'(/(Users|home|tmp|private|var)/|[A-Za-z]:\\)", sql))


# ---------------------------------------------------------------------------------------------------------------
# Esquema consultável (RGQ-02): métricas e dimensões do `semantic_manifest.json`, relações do `catalog.json` do dbt

# A natureza de cada métrica vem do modelo semântico da sua medida: muda a forma de agregar no tempo.
NATUREZA_MODELO = {
    "fct_resumo_mensal": "fotografia mensal: um mês é o cadastro inteiro; nunca some meses",
    "fct_estabelecimentos": "evento do extrato corrente, pela data de início ou da situação; soma entre anos",
    "mart_sobrevivencia_coorte": "coorte: ano de abertura; elegíveis e sobreviventes somam entre recortes",
    "mart_emprego_setor_municipio": "CEMPRE: 31/12 do `ano_cempre`, por classe CNAE; sigilo vira NULL",
}
# Camada de cada relação, pelo caminho do modelo; as de observabilidade (`dq_*`) e os testes ficam fora.
CAMADA_DO_CAMINHO = (
    ("models/staging/", "staging"),
    ("models/intermediate/", "intermediate"),
    ("models/marts/core/", "core"),
    ("models/marts/analytics/", "analytics"),
    ("models/marts/original/", "original"),
    ("seeds/", "seed"),
)
CAMADAS_GOLD = ("core", "analytics", "original")


def _texto_curto(texto: str | None) -> str:
    return " ".join((texto or "").split())


def _entidade_primaria(modelo: dict) -> str | None:
    if modelo.get("primary_entity"):
        return modelo["primary_entity"]
    return next((e["name"] for e in modelo["entities"] if e["type"] == "primary"), None)


def _entidades_alcancaveis(modelo: dict, primarias: set[str]) -> set[str]:
    """A entidade primária do modelo e as estrangeiras que têm modelo próprio (um salto de join, como o `mf`)."""
    proprias = {_entidade_primaria(modelo)} - {None}
    return proprias | {e["name"] for e in modelo["entities"] if e["name"] in primarias}


def gerar_esquema(manifesto: dict, catalogo_dbt: dict, semantico: dict) -> dict:
    """`metricas`, `dimensoes` (por entidade, com o nome qualificado do MetricFlow) e `relacoes` (colunas e tipos)."""
    modelos = {m["name"]: m for m in semantico["semantic_models"]}
    primarias = {_entidade_primaria(m) for m in modelos.values()} - {None}

    dimensoes = []
    for nome_modelo in sorted(modelos):
        modelo = modelos[nome_modelo]
        entidade = _entidade_primaria(modelo)
        if entidade is None:
            continue
        for dim in modelo["dimensions"]:
            grao = (dim.get("type_params") or {}).get("time_granularity")
            dimensoes.append(
                {
                    "nome": f"{entidade}__{dim['name']}",
                    "entidade": entidade,
                    "tipo": "tempo" if dim["type"] == "time" else "categórica",
                    "grao": grao,
                    "relacao": modelo["node_relation"]["alias"],
                    "coluna": dim.get("expr") or dim["name"],
                    "descricao": _texto_curto(dim.get("description")),
                }
            )
    dimensoes.sort(key=lambda d: (d["entidade"], d["nome"]))

    por_nome = {m["name"]: m for m in semantico["metrics"]}

    def _base(nome: str) -> set[str]:
        """Modelos semânticos das medidas de uma métrica (recursivo em ratio e derived)."""
        metrica = por_nome[nome]
        params = metrica["type_params"]
        agregacao = params.get("metric_aggregation_params") or {}
        if agregacao.get("semantic_model"):
            return {agregacao["semantic_model"]}
        entradas = [
            params.get("numerator"),
            params.get("denominator"),
            *(params.get("metrics") or []),
        ]
        return set().union(*(_base(e["name"]) for e in entradas if e))

    metricas = []
    for nome in sorted(por_nome):
        metrica = por_nome[nome]
        params = metrica["type_params"]
        agregacao = params.get("metric_aggregation_params") or {}
        bases = sorted(_base(nome))
        desconhecidos = [b for b in bases if b not in NATUREZA_MODELO]
        if desconhecidos:
            raise CatalogoErro(
                f"métrica {nome}: modelo semântico sem natureza em NATUREZA_MODELO: {', '.join(desconhecidos)}"
            )
        if metrica["type"] == "simple":
            medida = f"{agregacao['agg']}({params['expr']}) em {agregacao['semantic_model']}"
        elif metrica["type"] == "ratio":
            medida = f"{params['numerator']['name']} / {params['denominator']['name']}"
        else:
            entradas = ", ".join(sorted({e["name"] for e in params.get("metrics") or []}))
            medida = f"{params.get('expr')} (de {entradas})"
        filtros = [
            f["where_sql_template"]
            for f in ((metrica.get("filter") or {}).get("where_filters") or [])
        ]
        entidades = set.intersection(
            *(_entidades_alcancaveis(modelos[b], primarias) for b in bases)
        )
        metricas.append(
            {
                "nome": nome,
                "rotulo": metrica.get("label"),
                "tipo": metrica["type"],
                "natureza": "; ".join(NATUREZA_MODELO[b] for b in bases),
                "medida": medida,
                "filtro": filtros,
                "entidades": sorted(entidades),
                "descricao": _texto_curto(metrica.get("description")),
            }
        )

    relacoes = []
    for uid, no_catalogo in catalogo_dbt["nodes"].items():
        no = manifesto["nodes"].get(uid) or {}
        caminho = no.get("original_file_path", "")
        camada = next((c for prefixo, c in CAMADA_DO_CAMINHO if caminho.startswith(prefixo)), None)
        if (
            camada is None
            or no.get("package_name") != "rfb"
            or uid.split(".")[0] not in ("model", "seed")
        ):
            continue
        declaradas = no.get("columns") or {}
        colunas = []
        for coluna in sorted(no_catalogo["columns"].values(), key=lambda c: c["index"]):
            nome_coluna = coluna["name"]
            colunas.append(
                {
                    "nome": nome_coluna,
                    "tipo": coluna["type"],
                    "descricao": _texto_curto(
                        (declaradas.get(nome_coluna) or {}).get("description")
                    ),
                    "proibida_na_saida": bool(colunas_proibidas([nome_coluna])),
                }
            )
        meta = no.get("meta") or (no.get("config") or {}).get("meta") or {}
        relacoes.append(
            {
                "nome": f"main.{no['alias'] or no['name']}",
                "camada": camada,
                "grao": _texto_curto(meta.get("grao")) or None,
                "descricao": _texto_curto(no.get("description")),
                "colunas": colunas,
            }
        )
    ordem = {c: i for i, (_, c) in enumerate(CAMADA_DO_CAMINHO)}
    relacoes.sort(key=lambda r: (ordem[r["camada"]], r["nome"]))
    return {"metricas": metricas, "dimensoes": dimensoes, "relacoes": relacoes}


def carregar_esquema(alvo_dbt: Path) -> dict:
    """O esquema a partir do `manifest.json`, do `catalog.json` e do `semantic_manifest.json` de `alvo_dbt`."""
    arquivos = {n: alvo_dbt / f"{n}.json" for n in ("manifest", "catalog", "semantic_manifest")}
    faltam = [str(c) for c in arquivos.values() if not c.is_file()]
    if faltam:
        raise CatalogoErro(f"faltam {', '.join(faltam)}: rode `make golden` (dbt docs generate)")
    lidos = {n: json.loads(c.read_text(encoding="utf-8")) for n, c in arquivos.items()}
    return gerar_esquema(lidos["manifest"], lidos["catalog"], lidos["semantic_manifest"])


# ---------------------------------------------------------------------------------------------------------------
# Catálogo


def carregar_matriz(caminho: Path = MATRIZ) -> dict:
    return yaml.safe_load(caminho.read_text(encoding="utf-8"))


def carregar_semantica(caminho: Path = SEMANTICA) -> list[dict]:
    dados = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    return list(dados.get("golden_queries") or [])


def carregar_golden(diretorio: Path = DIR_GOLDEN) -> dict[str, tuple[dict, str]]:
    """`{id: (cabeçalho, SQL fonte)}` das golden queries SQL, em ordem de nome."""
    resultado = {}
    for arquivo in sorted(diretorio.glob(PADRAO_ARQUIVO)):
        texto = arquivo.read_text(encoding="utf-8")
        resultado[arquivo.stem] = (ler_cabecalho(texto, arquivo.name), texto)
    return resultado


def problemas_gerais(
    matriz: dict, golden: dict[str, tuple[dict, str]], semantica: list[dict]
) -> list[str]:
    """Cabeçalhos, entradas semânticas e cobertura da matriz."""
    conceitos = {c["id"] for c in matriz["conceitos"]}
    problemas: list[str] = []
    for nome, (cab, texto) in golden.items():
        problemas += validar_cabecalho(cab, nome, texto, conceitos)
        resposta = cab.get("resposta_esperada_fixtures") or {}
        proibidas = colunas_proibidas(
            resposta.get("colunas") or [], cab.get("privacidade", "agregado")
        )
        if proibidas:
            problemas.append(
                f"{nome}: colunas proibidas na saída (ADR-0008): {', '.join(proibidas)}"
            )
    for entrada in semantica:
        problemas += validar_semantica(entrada, conceitos)
        resposta = entrada.get("resposta_esperada_fixtures") or {}
        proibidas = colunas_proibidas(
            resposta.get("colunas") or [], entrada.get("privacidade", "agregado")
        )
        if proibidas:
            problemas.append(
                f"{entrada.get('id')}: colunas proibidas na saída (ADR-0008): {', '.join(proibidas)}"
            )
    for cab, texto in golden.values():
        problemas += problemas_empresa(cab, _RE_CABECALHO.sub("", texto))
    for entrada in semantica:
        consulta = " ".join([*(entrada.get("metricas") or []), *(entrada.get("group_by") or [])])
        problemas += problemas_empresa(entrada, f"{consulta} {entrada.get('where') or ''}")
    ids = [*golden, *(str(e.get("id")) for e in semantica)]
    cabecalhos = [*(c for c, _ in golden.values()), *semantica]
    return (
        problemas + problemas_de_cobertura(matriz, ids) + ids_citados_inexistentes(cabecalhos, ids)
    )


_CAMPOS_DE_TEXTO = ("perguntas", "intencao", "armadilhas", "variacoes")
_RE_PERGUNTA_EMPRESA = re.compile(r"\bempresas?\b", re.I)
# SQL ou consulta semântica que conta empresas (CNPJ básico), não estabelecimentos.
_RE_CONTA_EMPRESA = re.compile(
    r"eh_matriz|cnpj_raiz|cnpj_basico|left\(\s*[\w.]*cnpj_completo\s*,\s*8\s*\)|qtd_matrizes", re.I
)
ARMADILHA_EMPRESA = "Empresa × estabelecimento:"


def problemas_empresa(cab: dict, consulta: str) -> list[str]:
    """Pergunta com "empresa" exige consulta que conte empresas ou a armadilha explícita (RGQ-03).

    O glossário do guia: empresa = CNPJ básico (matriz); estabelecimento = CNPJ completo. Uma golden query que
    responde "quantas empresas" contando estabelecimentos precisa dizer isso numa armadilha que começa com
    `Empresa × estabelecimento:`.
    """
    if not any(_RE_PERGUNTA_EMPRESA.search(p) for p in cab.get("perguntas") or []):
        return []
    if _RE_CONTA_EMPRESA.search(consulta):
        return []
    if any(str(a).startswith(ARMADILHA_EMPRESA) for a in cab.get("armadilhas") or []):
        return []
    return [
        f"{cab.get('id')}: pergunta por empresa, mas não conta empresas (`eh_matriz`, CNPJ básico, `qtd_matrizes`) "
        f"nem tem a armadilha `{ARMADILHA_EMPRESA} ...`"
    ]


def ids_citados_inexistentes(cabecalhos: list[dict], ids: list[str]) -> list[str]:
    """Golden queries citadas no texto de um cabeçalho (armadilhas, variações...) que não existem (RGQ-07)."""
    existentes = set(ids)
    problemas = []
    for cab in cabecalhos:
        texto = " ".join(str(cab.get(campo) or "") for campo in _CAMPOS_DE_TEXTO)
        for citado in sorted(set(_RE_ID_CITADO.findall(texto)) - existentes):
            problemas.append(f"{cab.get('id')}: cita {citado}, que não existe")
    return problemas


_RE_BLOCO_SQL = re.compile(r"^[ \t]*```sql[ \t]*\n(.*?)^[ \t]*```", re.S | re.M)
_RE_MARCA_EXEMPLO = re.compile(r"\A\s*-- exemplo: ([a-z0-9_]+)\s*\n")


def exemplos_sql_do_guia(texto: str) -> dict[str, str]:
    """`{id: SQL}` dos blocos ```sql do guia; todo bloco abre com `-- exemplo: <id>` (RGQ-07), id único."""
    exemplos: dict[str, str] = {}
    for bloco in _RE_BLOCO_SQL.findall(texto):
        marca = _RE_MARCA_EXEMPLO.match(bloco)
        if marca is None:
            raise CatalogoErro(
                f"{GUIA.name}: bloco ```sql sem `-- exemplo: <id>` na primeira linha:\n{bloco[:200]}"
            )
        if marca.group(1) in exemplos:
            raise CatalogoErro(f"{GUIA.name}: id de exemplo repetido: {marca.group(1)}")
        exemplos[marca.group(1)] = "\n".join(linha.strip() for linha in bloco.splitlines())
    return exemplos


def problemas_do_guia(texto: str, ids: list[str]) -> list[str]:
    """Golden queries citadas no guia (fora do bloco gerado também) que não existem (RGQ-07)."""
    return [
        f"{GUIA.name}: cita {citado}, que não existe"
        for citado in sorted(set(_RE_ID_CITADO.findall(texto)) - set(ids))
    ]


def _entrada_comum(cab: dict) -> dict:
    return {
        "id": cab["id"],
        "conceito": cab["conceito"],
        "camada": cab["camada"],
        "perguntas": cab["perguntas"],
        "intencao": cab["intencao"],
        "privacidade": cab.get("privacidade", "agregado"),
        "armadilhas": cab["armadilhas"],
        "variacoes": cab["variacoes"],
    }


def gerar_catalogo(
    matriz: dict, golden: dict[str, tuple[dict, str]], compilados: dict[str, str], semantica: list[dict],
    raiz_dados: str | Path | None, semanticos: dict[str, str], esquema: dict | None = None,
    definicoes: list[Definicao] | None = None,
) -> dict:  # fmt: skip
    """O catálogo legível por máquina (dicionário pronto para `json.dumps`).

    `semanticos` é o SQL gerado pelo MetricFlow para cada golden query semântica (`sql_semantico`); `esquema`, as
    métricas, dimensões e relações consultáveis (`gerar_esquema`); `definicoes`, os doc blocks dos conceitos.
    """
    problemas = problemas_gerais(matriz, golden, semantica) + problemas_de_definicoes(
        matriz, definicoes or []
    )
    faltam = sorted(set(golden) - set(compilados))
    if faltam:
        problemas.append(f"sem SQL compilado: {', '.join(faltam)}")
    faltam = sorted({str(e.get("id")) for e in semantica} - set(semanticos))
    if faltam:
        problemas.append(f"sem SQL do MetricFlow: {', '.join(faltam)}")
    privacidade = {n: c.get("privacidade", "agregado") for n, (c, _) in golden.items()} | {
        str(e.get("id")): e.get("privacidade", "agregado") for e in semantica
    }
    for nome, sql in sorted({**compilados, **semanticos}.items()):
        derivadas = colunas_derivadas_proibidas(sql, privacidade.get(nome, "agregado"))
        if derivadas:
            problemas.append(
                f"{nome}: saída derivada de coluna proibida (ADR-0008): {', '.join(derivadas)}"
            )
    if problemas:
        raise CatalogoErro("golden queries com problema:\n- " + "\n- ".join(problemas))
    consultas = []
    for nome, (cab, _) in golden.items():
        sql = normalizar_sql(compilados[nome], raiz_dados)
        if caminho_absoluto_no_sql(sql):
            raise CatalogoErro(f"{nome}: o SQL compilado ainda tem caminho absoluto da máquina")
        consultas.append(
            {
                **_entrada_comum(cab),
                "tabelas": cab["tabelas"],
                "colunas_chave": cab["colunas_chave"],
                "arquivo": f"transform/analyses/{SUBPASTA}/{nome}.sql",
                "sql": sql,
                "resposta_esperada_fixtures": cab["resposta_esperada_fixtures"],
            }
        )
    for entrada in semantica:
        extra = (
            {"saved_query": entrada["saved_query"]}
            if entrada.get("saved_query")
            else {
                "metricas": entrada["metricas"],
                "group_by": entrada.get("group_by") or [],
                "where": entrada.get("where"),
            }
        )
        consultas.append(
            {
                **_entrada_comum(entrada),
                **extra,
                "tabelas": relacoes_do_sql_portavel(semanticos[entrada["id"]]),
                "arquivo": relativo(SEMANTICA),
                "sql": semanticos[entrada["id"]],
                "comando": comando_mf(entrada),
                "resposta_esperada_fixtures": entrada["resposta_esperada_fixtures"],
            }
        )
    ordem = {c: i for i, c in enumerate(CAMADAS)}
    consultas.sort(key=lambda c: (ordem[c["camada"]], c["conceito"], c["id"]))
    motivos = matriz.get("sem_query") or {}
    return {
        "formato": 1,
        "versao_projeto": __version__,
        "descricao": (
            "Golden queries por conceito e camada (ADR-0023). Gerado por scripts/gerar_catalogo_golden.py; não "
            "edite à mão. Toda golden query tem `sql`: nas camadas SQL, o compilado pelo dbt; na semântica, o que o "
            "MetricFlow gera (`mf query --explain`), que roda sem o repositório e só lê. Relações em `main.<nome>` "
            "(o schema do warehouse local e do MotherDuck) e `${RAIZ_DADOS}` no lugar da raiz dos dados nas fontes "
            f"raw. Guia de uso: {relativo(GUIA)}. Cada conceito traz em `definicoes` a definição curta (doc blocks "
            "do dbt, a mesma das descrições dos modelos)."
        ),
        "marcador_raiz_dados": MARCADOR_RAIZ,
        "camadas": matriz["camadas"],
        "conceitos": [
            {
                **c,
                "definicoes": [
                    {"id": d.nome, "titulo": d.titulo, "texto": d.texto}
                    for nome in c.get("definicoes") or []
                    for d in definicoes or []
                    if d.nome == nome
                ],
                "sem_query": dict(motivos.get(c["id"]) or {}),
            }
            for c in matriz["conceitos"]
        ],
        "golden_queries": consultas,
        **(esquema or {}),
    }


def problemas_de_definicoes(matriz: dict, definicoes: list[Definicao]) -> list[str]:
    """Todo nome em `conceitos[].definicoes` é um doc block, e todo doc block está em algum conceito."""
    nomes = {d.nome for d in definicoes}
    citados = {n for c in matriz["conceitos"] for n in c.get("definicoes") or []}
    problemas = [
        f"conceito {c['id']}: definição {n!r} não é doc block de {relativo(DOC_BLOCKS_CONCEITOS)}"
        for c in matriz["conceitos"]
        for n in c.get("definicoes") or []
        if n not in nomes
    ]
    if definicoes:
        problemas += [
            f"doc block {n!r} sem conceito na matriz (`definicoes`)"
            for n in sorted(nomes - citados)
        ]
    return problemas


def _link(consulta: dict) -> str:
    if consulta["camada"] == "semantica":
        return f"[`{consulta['id']}`]({link_de(GUIA, SEMANTICA)})"
    return f"[`{consulta['id']}`]({link_de(GUIA, RAIZ / consulta['arquivo'])})"


def renderizar_indice(catalogo: dict) -> str:
    """O bloco gerado do guia: a matriz conceito × camada, os motivos das células vazias e o índice."""
    camadas = [c["id"] for c in catalogo["camadas"]]
    por_celula: dict[tuple[str, str], list[dict]] = {}
    for consulta in catalogo["golden_queries"]:
        por_celula.setdefault((consulta["conceito"], consulta["camada"]), []).append(consulta)
    por_camada = {
        c: sum(1 for q in catalogo["golden_queries"] if q["camada"] == c) for c in camadas
    }
    linhas = [
        INICIO_BLOCO,
        "",
        f"**{len(catalogo['golden_queries'])}** golden queries em **{len(catalogo['conceitos'])}** conceitos: "
        + ", ".join(f"{c} {por_camada[c]}" for c in camadas)
        + ". Cada célula tem as golden queries (número = sufixo `__nn`) ou um traço, com o motivo na lista abaixo "
        "da tabela.",
        "",
        "| Conceito | " + " | ".join(camadas) + " |",
        "|---|" + "---|" * len(camadas),
    ]
    for conceito in catalogo["conceitos"]:
        celulas = []
        for camada in camadas:
            consultas = por_celula.get((conceito["id"], camada), [])
            if consultas:
                celulas.append(
                    " ".join(f"[{q['id'][-2:]}]({_link(q).split('](', 1)[1]}" for q in consultas)
                )
            else:
                celulas.append("—")
        linhas.append(f"| `{conceito['id']}` {conceito['nome']} | " + " | ".join(celulas) + " |")
    linhas += ["", "#### Células sem golden query", ""]
    for conceito in catalogo["conceitos"]:
        for camada, motivo in conceito["sem_query"].items():
            linhas.append(f"- `{conceito['id']}` × `{camada}`: {motivo}")
    linhas += [
        "",
        "#### Índice",
        "",
        "| Golden query | Camada | Conceito | Pergunta típica | Intenção |",
        "|---|---|---|---|---|",
    ]
    for consulta in catalogo["golden_queries"]:
        linhas.append(
            f"| {_link(consulta)} | {consulta['camada']} | `{consulta['conceito']}` | "
            f"{consulta['perguntas'][0]} | {consulta['intencao']} |".replace("\n", " ")
        )
    linhas += ["", FIM_BLOCO]
    return "\n".join(linhas)


def _codigo(texto: str) -> str:
    return f"`{_celula(texto)}`" if texto else "—"


def _celula(texto: str) -> str:
    """Texto seguro numa célula de tabela Markdown (o `|` escapado)."""
    return texto.replace("|", "\\|")


def renderizar_esquema(catalogo: dict) -> str:
    """O bloco gerado do esquema no guia: métricas, dimensões por entidade e colunas das relações do gold."""
    linhas = [
        INICIO_ESQUEMA,
        "",
        f"#### Métricas ({len(catalogo['metricas'])})",
        "",
        "Toda métrica aceita `metric_time` (`metric_time__day`, `__week`, `__month`, `__quarter`, `__year`) e as "
        "dimensões das entidades listadas. A medida diz o que somar no gold quando o `sql` da semântica não basta.",
        "",
        "| Métrica | Tipo | Natureza | Medida | Filtro | Entidades | Descrição |",
        "|---|---|---|---|---|---|---|",
    ]
    for m in catalogo["metricas"]:
        filtro = "<br/>".join(_codigo(f) for f in m["filtro"]) or "—"
        linhas.append(
            f"| `{m['nome']}` | {m['tipo']} | {m['natureza']} | {_codigo(m['medida'])} | {filtro} | "
            f"{', '.join(m['entidades'])} | {_celula(m['descricao'])} |"
        )
    linhas += [
        "",
        f"#### Dimensões por entidade ({len(catalogo['dimensoes'])})",
        "",
        "Nome qualificado `<entidade>__<dimensão>`, como no `--group-by` e no `Dimension(...)` do `mf` e como coluna "
        "no `sql` gerado. Dimensão de tempo leva o grão (`resumo_mensal__mes__month`).",
        "",
        "| Entidade | Relação | Dimensões |",
        "|---|---|---|",
    ]
    por_entidade: dict[tuple[str, str], list[dict]] = {}
    for d in catalogo["dimensoes"]:
        por_entidade.setdefault((d["entidade"], d["relacao"]), []).append(d)
    for (entidade, relacao), dims in por_entidade.items():
        nomes = ", ".join(
            f"`{d['nome']}`" + (f" (tempo, {d['grao']})" if d["tipo"] == "tempo" else "")
            for d in dims
        )
        linhas.append(f"| `{entidade}` | `main.{relacao}` | {nomes} |")
    gold = [r for r in catalogo["relacoes"] if r["camada"] in CAMADAS_GOLD]
    linhas += [
        "",
        f"#### Colunas das relações do gold ({len(gold)})",
        "",
        "Nome e tipo no DuckDB, como `describe main.<relação>` mostra. **Negrito** = coluna proibida na saída "
        "(seção 7). As relações de staging, intermediate e seeds, com a descrição de cada coluna, estão em "
        "`relacoes` no catálogo.",
        "",
        "| Relação | Camada | Grão | Colunas |",
        "|---|---|---|---|",
    ]
    for r in gold:
        colunas = ", ".join(
            (f"**`{c['nome']}`**" if c["proibida_na_saida"] else f"`{c['nome']}`")
            + f" {c['tipo'].lower()}"
            for c in r["colunas"]
        )
        linhas.append(
            f"| `{r['nome']}` | {r['camada']} | {_celula(r['grao'] or '—')} | {colunas} |"
        )
    linhas += ["", FIM_ESQUEMA]
    return "\n".join(linhas)


def substituir_bloco(
    texto: str, bloco: str, inicio_marca: str = INICIO_BLOCO, fim_marca: str = FIM_BLOCO
) -> str:
    """Troca o bloco entre os marcadores do guia pelo `bloco` gerado."""
    inicio = texto.find(inicio_marca)
    fim = texto.find(fim_marca, max(inicio, 0))
    if inicio < 0 or fim < inicio:
        raise CatalogoErro(f"faltam os marcadores {inicio_marca[:60]}…")
    return texto[:inicio] + bloco + texto[fim + len(fim_marca) :]


def renderizar_guia(texto: str, catalogo: dict) -> str:
    """O guia com os dois blocos gerados atualizados: o esquema e o índice."""
    texto = substituir_bloco(texto, renderizar_esquema(catalogo), INICIO_ESQUEMA, FIM_ESQUEMA)
    return substituir_bloco(texto, renderizar_indice(catalogo))


def _milhar(numero: int) -> str:
    return f"{numero:,}".replace(",", ".")


def renderizar_tamanhos(catalogo: dict, texto_catalogo: str, texto_guia: str) -> str:
    """Bloco de tamanhos de `construcao-agente.md`: bytes em UTF-8 e tokens estimados (bytes ÷ 4).

    O catálogo inteiro é o arquivo versionado (`texto_catalogo`); cada bloco, o `json.dumps` compacto (separadores
    padrão, sem escapar acento); o guia, o texto gerado com as linhas.
    """

    def linha(rotulo: str, texto: str) -> str:
        tamanho = len(texto.encode("utf-8"))
        return f"| {rotulo} | {_milhar(tamanho)} | ~{_milhar(round(tamanho / 400) * 100)} |"

    blocos = [
        linha(
            f"`{chave}` ({len(catalogo[chave])})", json.dumps(catalogo[chave], ensure_ascii=False)
        )
        for chave in ("golden_queries", "relacoes", "dimensoes", "metricas", "conceitos")
    ]
    referencia = texto_guia[texto_guia.index("## 11. ") :]
    return "\n".join(
        [
            INICIO_TAMANHOS,
            "",
            f"Medido na versão {catalogo['versao_projeto']} (`versao_projeto` do catálogo).",
            "",
            "| Bloco | Bytes | Tokens (est.) |",
            "|---|---|---|",
            linha("`catalogo.json` inteiro (o arquivo)", texto_catalogo),
            *blocos,
            linha(f"Guia `consulta-agente.md` ({texto_guia.count(chr(10))} linhas)", texto_guia),
            linha(f"Guia, seções 11 e 12 ({referencia.count(chr(10))} linhas)", referencia),
            "",
            FIM_TAMANHOS,
        ]
    )


def renderizar_construcao(texto: str, catalogo: dict, texto_catalogo: str, texto_guia: str) -> str:
    """`construcao-agente.md` com o bloco de tamanhos atualizado."""
    bloco = renderizar_tamanhos(catalogo, texto_catalogo, texto_guia)
    return substituir_bloco(texto, bloco, INICIO_TAMANHOS, FIM_TAMANHOS)


def serializar(catalogo: dict) -> str:
    return json.dumps(catalogo, ensure_ascii=False, indent=2) + "\n"


def compilar(raiz_dados: Path) -> dict[str, str]:
    """`{id: SQL compilado}` das golden queries (`dbt compile` com o target `ci`)."""
    sys.path.insert(0, str(RAIZ / "src"))
    from rfb_pipeline.relatorio import compilar_analises

    return compilar_analises(
        DIR_TRANSFORM, raiz_dados, "ci", subpasta=SUBPASTA, padrao=PADRAO_ARQUIVO
    )


def main(argv: list[str] | None = None) -> int:
    analisador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analisador.add_argument(
        "--verificar", action="store_true", help="só confere se o catálogo e o guia estão em dia"
    )
    analisador.add_argument(
        "--raiz-dados", type=Path, default=Path(os.environ.get("RAIZ_DADOS", RAIZ / ".tmp" / "ci" / "dados")),
        help="RAIZ_DADOS da compilação (padrão: a do `make ci`)",
    )  # fmt: skip
    analisador.add_argument("--catalogo", type=Path, default=CATALOGO)
    analisador.add_argument("--guia", type=Path, default=GUIA)
    analisador.add_argument("--construcao", type=Path, default=CONSTRUCAO)
    analisador.add_argument(
        "--alvo-dbt", type=Path, default=DIR_TRANSFORM / "target",
        help="diretório com manifest.json, catalog.json e semantic_manifest.json (`dbt docs generate`)",
    )  # fmt: skip
    args = analisador.parse_args(argv)
    try:
        compilados = compilar(args.raiz_dados)
        semantica = carregar_semantica()
        catalogo = gerar_catalogo(
            carregar_matriz(), carregar_golden(), compilados, semantica, args.raiz_dados,
            sql_semantico(semantica, args.raiz_dados), carregar_esquema(args.alvo_dbt),
            carregar_definicoes(),
        )  # fmt: skip
        texto_catalogo = serializar(catalogo)
        texto_guia = renderizar_guia(args.guia.read_text(encoding="utf-8"), catalogo)
        texto_construcao = renderizar_construcao(
            args.construcao.read_text(encoding="utf-8"), catalogo, texto_catalogo, texto_guia
        )
        problemas = problemas_do_guia(texto_guia, [q["id"] for q in catalogo["golden_queries"]])
        exemplos_sql_do_guia(texto_guia)  # todo bloco SQL marcado
        if problemas:
            raise CatalogoErro("\n- ".join(["guia com problema:", *problemas]))
    except Exception as exc:  # noqa: BLE001 — mensagem curta na linha de comando
        print(f"erro: {exc}", file=sys.stderr)
        return 1
    if args.verificar:
        atual = args.catalogo.read_text(encoding="utf-8") if args.catalogo.is_file() else ""
        desatualizados = [
            str(caminho.relative_to(RAIZ)) if caminho.is_relative_to(RAIZ) else str(caminho)
            for caminho, novo, velho in (
                (args.catalogo, texto_catalogo, atual),
                (args.guia, texto_guia, args.guia.read_text(encoding="utf-8")),
                (args.construcao, texto_construcao, args.construcao.read_text(encoding="utf-8")),
            )
            if novo != velho
        ]
        if desatualizados:
            print(
                f"desatualizado: {', '.join(desatualizados)}; rode `make golden` e versione o resultado",
                file=sys.stderr,
            )
            return 1
        print(f"catálogo em dia: {len(catalogo['golden_queries'])} golden queries")
        return 0
    args.catalogo.parent.mkdir(parents=True, exist_ok=True)
    args.catalogo.write_text(texto_catalogo, encoding="utf-8")
    args.guia.write_text(texto_guia, encoding="utf-8")
    args.construcao.write_text(texto_construcao, encoding="utf-8")
    print(
        f"{args.catalogo.relative_to(RAIZ)}: {len(catalogo['golden_queries'])} golden queries; índice do guia atualizado"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
