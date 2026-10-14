# ruff: noqa: E501  (textos longos do dicionário)
"""Gera `docs/DICIONARIO_DADOS.md` (ADR-0019) a partir do `manifest.json` e do `catalog.json` do dbt.

Uso: `make dicionario` (roda `dbt docs generate` sobre o `warehouse.duckdb` de `RAIZ_DADOS` e este
script) ou, com os dois arquivos já gerados em `transform/target/`,
`uv run python scripts/gerar_dicionario_dados.py`. Com `--verificar` não escreve nada: gera em memória
e falha (código 1) se `docs/DICIONARIO_DADOS.md` estiver desatualizado.

O dicionário descreve toda tabela disponível na base: fontes raw (RFB, Base dos Dados e IBGE), seeds,
staging, intermediate, gold (dimensões, fatos, pontes e marts) e observabilidade. Os tipos vêm do
contrato (`data_type`) e, na falta dele, do catálogo (tipos reais no DuckDB); o resto (grão em
`meta.grao`, campo do leiaute em `meta.campo_leiaute`, coluna no BigQuery em `meta.coluna_bigquery`,
campo publicado pelo IBGE em `meta.campo_ibge`,
testes, camada semântica) vem do manifesto. As seções de texto fixas ficam neste script.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
MANIFESTO = RAIZ / "transform" / "target" / "manifest.json"
CATALOGO = RAIZ / "transform" / "target" / "catalog.json"
SAIDA = RAIZ / "docs" / "DICIONARIO_DADOS.md"

PACOTE = "rfb"
ADR_0008 = "[ADR-0008](adr/0008-minimizacao-dados-pessoais.md)"
CAMADA_SEMANTICA = "[CAMADA_SEMANTICA.md](CAMADA_SEMANTICA.md)"

# (id, título, descrição curta) na ordem do índice.
CAMADAS = [
    ("fontes-rfb", "Fontes — RFB (raw)", "Parquet raw dos dados abertos de CNPJ (todas as colunas de dado são `varchar`)."),
    ("fontes-bd", "Fontes — Base dos Dados (raw)", "Parquet raw das tabelas públicas da Base dos Dados (`basedosdados`)."),
    ("fontes-ibge", "Fontes — IBGE (raw)", "Parquet raw das fontes baixadas direto do IBGE: API SIDRA e planilhas da REGIC 2018 (`ibge`)."),
    ("fontes-obs", "Fontes — observabilidade", "Tabela mantida pelos hooks `on-run-start`/`on-run-end` (não é modelo)."),
    ("seeds", "Seeds", "Domínios estáticos em CSV."),
    ("staging", "Staging", "Views com tipagem, limpeza e minimização de dados pessoais."),
    ("intermediate", "Intermediate", "Tabelas de junção e conformação entre o staging e o gold."),
    ("gold-dim", "Gold — dimensões", "Dimensões do modelo estrela (ADR-0013), com membros `-1`/`-2`."),
    ("gold-fct", "Gold — fatos", "Fatos do modelo estrela."),
    ("gold-bridge", "Gold — pontes", "Relações muitos-para-muitos opcionais no BI."),
    ("gold-original", "Gold — marts originais", "`bh_empresas` e `agg_empresas`, com paridade ao MVP Spark (ADR-0005)."),
    ("gold-analytics", "Gold — marts analíticos", "Marts de análise (concorrência, dinâmica, sobrevivência, fornecedores)."),
    ("obs", "Observabilidade", "Modelos de acompanhamento dos testes e do teste de paridade."),
]  # fmt: skip

# Descrição fixa das colunas técnicas que a ingestão acrescenta ao raw já está nos YAMLs das fontes.
PADRAO_LINHAGEM = re.compile(r"Linhagem:\s*(.+?)(?:\.(?:\s|$)|$)", re.S)
PADRAO_REF = re.compile(r"ref\('([^']+)'\)")
PADRAO_SOURCE = re.compile(r"source\('([^']+)',\s*'([^']+)'\)")
PADRAO_RAW = re.compile(r"/(raw/[^'\"]+)['\"]")
PADRAO_SENTINELA = re.compile(r"`(-[12])`")
PADRAO_PII = re.compile(r"ADR-0008|\bCPF\b|mascar", re.I)


def _texto(valor: str | None) -> str:
    """Descrição em uma linha, segura para célula de tabela Markdown."""
    return " ".join((valor or "").split()).replace("|", "\\|")


def _codigo(valor: object) -> str:
    return f"`{valor}`"


def _meta(no: dict) -> dict:
    config = no.get("config") or {}
    return {**(no.get("meta") or {}), **(config.get("meta") or {})}


def _meta_coluna(decl: dict) -> dict:
    return {**(decl.get("meta") or {}), **((decl.get("config") or {}).get("meta") or {})}


def _alvo_do_teste(no: dict) -> tuple[str, str] | None:
    """(`ref`|`source`, nome) do recurso testado, lido do `model` do teste genérico."""
    modelo = ((no.get("test_metadata") or {}).get("kwargs") or {}).get("model", "")
    achou = PADRAO_SOURCE.search(modelo)
    if achou:
        return "source", f"{achou.group(1)}.{achou.group(2)}"
    achou = PADRAO_REF.search(modelo)
    return ("ref", achou.group(1)) if achou else None


class Tabela:
    """Uma tabela do dicionário (fonte, seed ou modelo) com tudo que o manifesto sabe dela."""

    def __init__(self, camada: str, chave: str, nome: str, no: dict, tipo: str, uid: str) -> None:
        self.uid = uid  # `unique_id` do manifesto
        self.camada = camada  # id de CAMADAS
        self.chave = chave  # `ref:<modelo>` ou `source:<fonte>.<tabela>`
        self.nome = nome  # como aparece no título (modelo ou `fonte.tabela`)
        self.no = no
        self.tipo = tipo  # `source` | `seed` | `model`
        self.ancora = nome.replace(".", "-")
        self.meta = _meta(no)
        self.colunas: list[tuple[str, dict, str | None]] = []  # (nome, declarada, tipo do catálogo)
        self.testes: list[dict] = []
        self.semantica: dict | None = None
        self.metricas: list[dict] = []
        self.catalogo: dict = {}  # colunas reais do catálogo (nome -> {type, index})
        self.le_de: list[Tabela] = []  # tabelas de que esta é lida (`depends_on` do manifesto)
        self.usada_por: list[Tabela] = []  # inverso de `le_de`


def _tabelas(manifesto: dict, catalogo: dict | None) -> list[Tabela]:
    cat_nos = (catalogo or {}).get("nodes", {})
    cat_fontes = (catalogo or {}).get("sources", {})
    tabelas: list[Tabela] = []

    for uid, fonte in manifesto["sources"].items():
        if fonte["package_name"] != PACOTE:
            continue
        camada = {"rfb": "fontes-rfb", "basedosdados": "fontes-bd", "ibge": "fontes-ibge"}.get(
            fonte["source_name"], "fontes-obs"
        )
        nome = f"{fonte['source_name']}.{fonte['name']}"
        t = Tabela(camada, f"source:{nome}", nome, fonte, "source", uid)
        t.catalogo = cat_fontes.get(uid, {}).get("columns", {})
        tabelas.append(t)

    for uid, no in manifesto["nodes"].items():
        if no["package_name"] != PACOTE or no["resource_type"] not in ("model", "seed"):
            continue
        caminho = no["original_file_path"]
        if no["resource_type"] == "seed":
            camada = "seeds"
        elif "/staging/" in caminho:
            camada = "staging"
        elif "/intermediate/" in caminho:
            camada = "intermediate"
        elif "/marts/original/" in caminho:
            camada = "gold-original"
        elif "/marts/analytics/" in caminho:
            camada = "gold-analytics"
        elif "/marts/core/" in caminho:
            camada = {"dim": "gold-dim", "fct": "gold-fct"}.get(no["name"][:3], "gold-bridge")
        else:
            camada = "obs"
        t = Tabela(camada, f"ref:{no['name']}", no["name"], no, no["resource_type"], uid)
        t.catalogo = cat_nos.get(uid, {}).get("columns", {})
        tabelas.append(t)

    por_chave = {t.chave: t for t in tabelas}
    for no in manifesto["nodes"].values():
        if (
            no["resource_type"] != "test"
            or no["package_name"] != PACOTE
            or not no.get("test_metadata")
        ):
            continue
        alvo = _alvo_do_teste(no)
        if alvo is None:
            continue
        t = por_chave.get(f"{'ref' if alvo[0] == 'ref' else 'source'}:{alvo[1]}")
        if t is not None:
            t.testes.append(no)

    for t in tabelas:
        # A ordem de `manifest["nodes"]` muda com o *partial parse*; a saída não pode depender dela.
        t.testes.sort(key=lambda n: n["unique_id"])
    por_uid = {t.uid: t for t in tabelas}
    for t in tabelas:
        if t.tipo == "source":
            continue
        for uid in t.no.get("depends_on", {}).get("nodes", []):
            origem = por_uid.get(uid)
            if origem is not None and origem is not t:
                t.le_de.append(origem)
                origem.usada_por.append(t)
    for t in tabelas:
        t.le_de.sort(key=lambda o: o.nome)
        t.usada_por.sort(key=lambda o: o.nome)

    metricas = list(manifesto.get("metrics", {}).values())
    for uid, sem in manifesto.get("semantic_models", {}).items():
        if sem["package_name"] != PACOTE:
            continue
        t = por_chave.get(f"ref:{sem['name']}")
        if t is None:
            continue
        t.semantica = sem
        t.metricas = sorted(
            (m for m in metricas if uid in m["depends_on"]["nodes"]), key=lambda m: m["name"]
        )

    for t in tabelas:
        declaradas = {k.lower(): (k, v) for k, v in t.no.get("columns", {}).items()}
        reais = {
            k.lower(): v.get("type")
            for k, v in sorted(t.catalogo.items(), key=lambda i: i[1]["index"])
        }
        ordem = list(reais) + [k for k in declaradas if k not in reais]
        for chave in ordem:
            nome, decl = declaradas.get(chave, (chave, {}))
            tipo = reais.get(chave)
            t.colunas.append((nome, decl, tipo.lower() if tipo else None))
    return sorted(tabelas, key=lambda t: t.nome)


_LIMIAR_PADRAO = "!=0"


def _limiar(config: dict, chave: str) -> str:
    return str(config.get(chave, _LIMIAR_PADRAO)).replace(" ", "")


def _severidade(teste: dict) -> str:
    """`warn` quando o teste pode avisar: severidade `warn` ou `warn_if`/`error_if` fora do padrão
    (mesma regra de `pode_avisar` em tests/integration/test_store_failures.py)."""
    config = teste.get("config") or {}
    fora_do_padrao = any(_limiar(config, c) != _LIMIAR_PADRAO for c in ("warn_if", "error_if"))
    if str(config.get("severity", "error")).lower() == "warn" or fora_do_padrao:
        return "warn"
    return "error"


def _marca(teste: dict) -> str:
    """` (`warn`)` quando o teste não barra o build: o valor pode ser violado no dado.
    Com `error_if` de limiar, detalha: `warn` até o limiar, `error` acima."""
    if _severidade(teste) == "error":
        return ""
    config = teste.get("config") or {}
    erro = _limiar(config, "error_if")
    if str(config.get("severity", "error")).lower() == "error" and erro != _LIMIAR_PADRAO:
        m = re.fullmatch(r">(\d+)", erro)
        if m:
            return f" (`warn` até {m[1]} linhas; `error` acima)"
    return " (`warn`)"


def _chave_unica(t: Tabela) -> tuple[dict[str, str], list[tuple[list[str], str]]]:
    """(coluna única → severidade, combinações únicas → severidade) dos testes de unicidade."""
    simples: dict[str, str] = {}
    combinadas: list[tuple[list[str], str]] = []
    for teste in t.testes:
        meta = teste["test_metadata"]
        kwargs = meta.get("kwargs") or {}
        if meta["name"] == "unique":
            coluna = teste["column_name"]
            # Dois testes na mesma coluna: vale o mais rígido.
            if simples.get(coluna) != "error":
                simples[coluna] = _severidade(teste)
        elif meta["name"] == "unique_combination_of_columns":
            combinadas.append((list(kwargs["combination_of_columns"]), _severidade(teste)))
    return simples, combinadas


def _colunas_do_grao(t: Tabela) -> set[str]:
    """Colunas citadas entre crases em `meta.grao`."""
    return set(re.findall(r"`([^`]+)`", str(t.meta.get("grao") or "")))


def _chave_primaria(t: Tabela) -> tuple[str, str]:
    """(chave primária, outras chaves únicas) em texto Markdown.

    A chave primária é uma coluna (ou combinação) com teste de unicidade e que está no grão declarado;
    sem uma, a tabela fica "não testada" e os `unique` existentes vão para "Outras chaves únicas".
    """
    simples, combinadas = _chave_unica(t)
    grao = _colunas_do_grao(t)
    primaria: list[str] | None = None
    entidade = None
    if t.semantica:
        entidade = next(
            (e["expr"] for e in t.semantica["entities"] if e["type"] == "primary"), None
        )
    if entidade and entidade in simples:
        primaria = [entidade]
    else:
        candidatas = [c for c in simples if c in grao] if grao else list(simples)
        if candidatas:
            primaria = [next((c for c in candidatas if c.startswith("sk_")), candidatas[0])]
        elif combinadas:
            primaria = combinadas[0][0]
    todas = [([c], sev) for c, sev in simples.items()] + combinadas

    # `warn` não garante a unicidade: quem lê precisa saber.
    def _texto_chave(colunas: list[str], severidade: str, sufixo: str) -> str:
        texto = " + ".join(_codigo(c) for c in colunas)
        return texto if severidade == "error" else f"{texto} {sufixo}"

    outras = [_texto_chave(cols, sev, f"(`{sev}`)") for cols, sev in todas if cols != primaria]
    if primaria is None:
        return "não testada", "; ".join(outras) or "—"
    severidade = next(sev for cols, sev in todas if cols == primaria)
    return _texto_chave(primaria, severidade, f"(teste `{severidade}`)"), "; ".join(outras) or "—"


def _alvo_fk(t: Tabela, por_nome: dict[str, Tabela]) -> list[tuple[str, str, str, str]]:
    """(coluna, tabela alvo, coluna alvo, origem) das FKs.

    Origem: `testada` (teste `relationships`), `testada (warn)`, `semântica` (entidade `foreign` da
    camada semântica) ou `declarada` (`meta.fk_declarada` na coluna, sem teste).
    """
    saida: dict[tuple[str, str], tuple[str, str]] = {}
    for teste in t.testes:
        meta = teste["test_metadata"]
        if meta["name"] != "relationships":
            continue
        kwargs = meta["kwargs"]
        achou_ref = PADRAO_REF.search(kwargs["to"])
        achou_src = PADRAO_SOURCE.search(kwargs["to"])
        alvo = achou_ref.group(1) if achou_ref else f"{achou_src.group(1)}.{achou_src.group(2)}"
        origem = "testada" if _severidade(teste) == "error" else f"testada ({_severidade(teste)})"
        saida[(teste["column_name"], alvo)] = (kwargs["field"], origem)
    if t.semantica:
        primarias = {
            e["name"]: (s.nome, e["expr"])
            for s in por_nome.values()
            if s.semantica
            for e in s.semantica["entities"]
            if e["type"] == "primary"
        }
        for e in t.semantica["entities"]:
            if e["type"] == "foreign" and e["name"] in primarias:
                alvo, campo = primarias[e["name"]]
                saida.setdefault((e["expr"], alvo), (campo, "semântica"))
    for nome, decl, _ in t.colunas:
        declarada = _meta_coluna(decl).get("fk_declarada")
        if declarada:
            alvo, campo = declarada.split(".", 1)
            saida.setdefault((nome, alvo), (campo, "declarada"))
    return sorted((c, a, f, o) for (c, a), (f, o) in saida.items())


def _link(nome: str, por_nome: dict[str, Tabela]) -> str:
    alvo = por_nome.get(nome)
    return f"[`{nome}`](#{alvo.ancora})" if alvo else f"`{nome}`"


def _localizacao(t: Tabela) -> tuple[str, str]:
    """(materialização, localização) — o gold é relativo a `RAIZ_DADOS`."""
    if t.tipo == "source":
        raw = PADRAO_RAW.search(str(t.meta.get("external_location", "")))
        if raw:
            return (
                "Parquet raw (leitura direta, `external_location`)",
                f"`{raw.group(1)}` (relativo a `RAIZ_DADOS`)",
            )
        return (
            "tabela no `warehouse.duckdb`",
            "`warehouse.duckdb` (esquema `main`, em `RAIZ_DADOS`)",
        )
    if t.tipo == "seed":
        arquivo = t.no["original_file_path"]
        return "seed (tabela no `warehouse.duckdb`)", f"CSV `transform/{arquivo}`"
    materializacao = t.no["config"].get("materialized")
    if materializacao == "external":
        opcoes = t.no["config"].get("options") or {}
        particao = opcoes.get("partition_by")
        if particao:
            return (
                "Parquet particionado (`external`)",
                f"`gold/{t.nome}/{particao}=AAAA-MM/` (relativo a `RAIZ_DADOS`)",
            )
        return "Parquet (`external`)", f"`gold/{t.nome}.parquet` (relativo a `RAIZ_DADOS`)"
    return {
        "view": ("view dbt", "`warehouse.duckdb` (view, esquema `main`)"),
        "table": ("tabela dbt", "`warehouse.duckdb` (tabela, esquema `main`)"),
        "ephemeral": ("efêmero (CTE)", "sem relação física: só existe dentro do teste que o usa"),
    }.get(materializacao, (str(materializacao), "—"))


def _dominio(t: Tabela, coluna: str, decl: dict, por_nome: dict[str, Tabela]) -> str:
    partes: list[str] = []
    da_seed = _dominio_seed(t, coluna, decl, por_nome)
    if da_seed:
        partes.append(da_seed)
    for teste in t.testes:
        if teste.get("column_name") != coluna:
            continue
        meta = teste["test_metadata"]
        kwargs = meta.get("kwargs") or {}
        onde = (teste.get("config") or {}).get("where")
        filtro = f" (onde `{_texto(onde)}`)" if onde else ""
        if meta["name"] == "accepted_values":
            partes.append(
                "valores: " + ", ".join(f"`{v}`" for v in kwargs["values"]) + filtro + _marca(teste)
            )
        elif meta["name"] == "accepted_range":
            minimo, maximo = kwargs.get("min_value"), kwargs.get("max_value")
            inclusivo = kwargs.get("inclusive", True)
            esq, dir_ = ("≤", "≤") if inclusivo else ("<", "<")
            if minimo is not None and maximo is not None:
                partes.append(f"`{minimo}` {esq} valor {dir_} `{maximo}`" + filtro + _marca(teste))
            elif minimo is not None:
                partes.append(
                    f"valor {'≥' if inclusivo else '>'} `{minimo}`" + filtro + _marca(teste)
                )
            elif maximo is not None:
                partes.append(
                    f"valor {'≤' if inclusivo else '<'} `{maximo}`" + filtro + _marca(teste)
                )
        elif meta["name"] == "relationships":
            achou_ref = PADRAO_REF.search(kwargs["to"])
            achou_src = PADRAO_SOURCE.search(kwargs["to"])
            alvo = achou_ref.group(1) if achou_ref else f"{achou_src.group(1)}.{achou_src.group(2)}"
            partes.append(
                f"FK → {_link(alvo, por_nome)}.`{kwargs['field']}`" + filtro + _marca(teste)
            )
        elif meta["name"] == "tamanho_exato":
            partes.append(f"tamanho exato: {kwargs['tamanho']}" + filtro + _marca(teste))
        elif meta["name"] == "data_nao_futura":
            partes.append(f"data não futura (`{_severidade(teste)}`)" + filtro)
        elif meta["name"] == "cnpj_dv_valido":
            partes.append(f"CNPJ com DV válido (`{_severidade(teste)}`)" + filtro)
    return "; ".join(partes) or "—"


def _dominio_seed(t: Tabela, coluna: str, decl: dict, por_nome: dict[str, Tabela]) -> str:
    """Valores lidos da seed declarada em `meta.dominio_seed` (`seed.coluna`), mais o membro desconhecido."""
    declarado = _meta_coluna(decl).get("dominio_seed")
    if not declarado:
        return ""
    nome_seed, coluna_seed = declarado.split(".", 1)
    seed = por_nome.get(nome_seed)
    if seed is None:
        return ""
    valores = [linha[coluna_seed] for linha in _linhas_seed(seed)]
    extra = _meta_coluna(decl).get("dominio_membro_desconhecido")
    if extra:
        valores.append(extra)
    return (
        f"valores da seed {_link(nome_seed, por_nome)}.`{coluna_seed}`"
        + ": "
        + ", ".join(_codigo(v) for v in valores)
    )


def _linhas_seed(seed: Tabela) -> list[dict[str, str]]:
    """Linhas do CSV da seed (vazio se o arquivo não estiver no checkout)."""
    arquivo = RAIZ / "transform" / seed.no["original_file_path"]
    if not arquivo.is_file():
        return []
    with arquivo.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _anulavel(t: Tabela, coluna: str) -> str:
    for teste in t.testes:
        if teste.get("column_name") == coluna and teste["test_metadata"]["name"] == "not_null":
            onde = (teste.get("config") or {}).get("where")
            condicao = f", onde `{_texto(onde)}`" if onde else ""
            if _severidade(teste) == "error":
                return f"não (`not_null`{condicao})"
            return (
                f"em geral não (`not_null` `{_severidade(teste)}`{condicao}: pode haver exceções)"
            )
    return "não testado"


def _origem(t: Tabela, coluna: str, decl: dict) -> str:
    meta = _meta_coluna(decl)
    partes: list[str] = []
    if meta.get("campo_leiaute"):
        partes.append(f"leiaute RFB: **{meta['campo_leiaute']}**")
    if meta.get("coluna_bigquery"):
        tabela = t.meta.get("tabela_bigquery")
        caminho = (
            f"basedosdados.{tabela}.{meta['coluna_bigquery']}"
            if tabela
            else meta["coluna_bigquery"]
        )
        partes.append(f"BigQuery: `{caminho}`")
    if meta.get("campo_ibge"):
        partes.append(f"IBGE: **{meta['campo_ibge']}**")
    if t.tipo == "source" and coluna.startswith("_"):
        partes.append("coluna técnica da ingestão")
    elif t.camada == "fontes-rfb" and not meta.get("campo_leiaute"):
        partes.append("não consta do leiaute oficial")
    achou = PADRAO_LINHAGEM.search(decl.get("description", "") or "")
    if achou:
        partes.append("linhagem: " + _texto(achou.group(1)))
    elif meta.get("linhagem"):
        partes.append("linhagem: " + _texto(meta["linhagem"]))
    for teste in t.testes:
        if (
            teste.get("column_name") == coluna
            and teste["test_metadata"]["name"] == "taxa_conversao_tipada"
        ):
            kwargs = teste["test_metadata"]["kwargs"]
            partes.append(f"raw: `{kwargs['entidade']}.{kwargs['coluna_raw']}`")
    return "; ".join(partes) or "—"


def _observacoes(t: Tabela, coluna: str, decl: dict, fks: dict[str, tuple[str, str]]) -> str:
    descricao = decl.get("description", "") or ""
    partes: list[str] = []
    if PADRAO_PII.search(descricao):
        partes.append(f"dado pessoal / minimização ({ADR_0008})")
    for teste in t.testes:
        if teste.get("column_name") != coluna:
            continue
        nome = teste["test_metadata"]["name"]
        if nome == "sem_cpf_no_nome":
            partes.append(f"CPF mascarado no texto ({ADR_0008}; teste `sem_cpf_no_nome`)")
        elif nome == "taxa_conversao_tipada":
            sentinelas = teste["test_metadata"]["kwargs"].get("sentinelas") or []
            if sentinelas:
                partes.append("sentinelas viram NULL: " + ", ".join(f"`{s}`" for s in sentinelas))
    sentinelas = sorted(set(PADRAO_SENTINELA.findall(descricao)), reverse=True)
    if _meta_coluna(decl).get("membro_desconhecido") is False:
        partes.append("não recebe a chave `-1` (ver a descrição)")
    elif sentinelas:
        partes.append("chave sentinela: " + ", ".join(f"`{s}`" for s in sentinelas))
    elif coluna in fks and fks[coluna][0] == "dim_data":
        partes.append("data nula → chave `-1`; data anterior a 1900 → chave `-2`")
    elif coluna in fks and fks[coluna][0].startswith("dim_"):
        partes.append("sem par na dimensão → chave `-1`")
    entidade = decl.get("entity")
    if entidade:
        partes.append(f"entidade semântica `{entidade['name']}` ({entidade['type']})")
    if decl.get("dimension"):
        partes.append(f"dimensão semântica ({decl['dimension']})")
    return "; ".join(partes) or "—"


def _lista_tabelas(tabelas: list[Tabela], por_nome: dict[str, Tabela]) -> str:
    return ", ".join(_link(o.nome, por_nome) for o in tabelas)


def _fonte_de(t: Tabela) -> str:
    """De onde vem a tabela quando ela não é lida de outra do projeto."""
    if t.tipo == "seed":
        return "CSV versionado no repositório"
    return {
        "fontes-rfb": "arquivos dos dados abertos de CNPJ da RFB (ingestão)",
        "fontes-bd": "Base dos Dados (ingestão)",
        "fontes-ibge": "IBGE: API SIDRA e geoftp (ingestão)",
        "fontes-obs": "hooks `on-run-start`/`on-run-end` do dbt",
    }.get(t.camada, "—")


def _linhas_tabela(t: Tabela, por_nome: dict[str, Tabela]) -> list[str]:
    materializacao, localizacao = _localizacao(t)
    pk, outras = _chave_primaria(t)
    fks = _alvo_fk(t, por_nome)
    fk_por_coluna = {c: (a, f) for c, a, f, _ in fks}
    contrato = bool((t.no.get("config") or {}).get("contract", {}).get("enforced"))
    escopo = t.meta.get("escopo", "?")
    incremento = t.meta.get("incremento", "—")
    grao = t.meta.get("grao")
    rotulo_grao = "Grão (declarado, não testado)" if grao and pk == "não testada" else "Grão"
    linhas = [
        f'<a id="{t.ancora}"></a>',
        f"#### `{t.nome}`",
        "",
        _texto(t.no.get("description")) or "(sem descrição)",
        "",
        "| Atributo | Valor |",
        "|---|---|",
        f"| {rotulo_grao} | {'Uma linha por ' + _texto(grao) + '.' if grao else '—'} |",
        f"| Chave primária (testada) | {pk} |",
        f"| Outras chaves únicas | {outras} |",
        "| Chaves estrangeiras | "
        + (
            "<br>".join(f"{_codigo(c)} → {_link(a, por_nome)}.`{f}` ({o})" for c, a, f, o in fks)
            or "—"
        )
        + " |",
        f"| Lê de | {_lista_tabelas(t.le_de, por_nome) if t.le_de else _fonte_de(t)} |",
        f"| Usada por | {_lista_tabelas(t.usada_por, por_nome) or '—'} |",
        f"| Materialização | {materializacao} |",
        f"| Localização | {localizacao} |",
        f"| Escopo | `{escopo}` ([ADR-0006](adr/0006-marcacao-escopo.md)) |",
        f"| Incremento | {_codigo(incremento) if incremento != '—' else '—'} |",
        f"| Contrato aplicado | {'sim' if contrato else 'não'} |",
    ]
    if t.semantica:
        entidades = ", ".join(
            f"`{e['name']}` ({e['type']}, `{e['expr']}`)" for e in t.semantica["entities"]
        )
        dimensoes = ", ".join(f"`{d['name']}`" for d in t.semantica["dimensions"]) or "—"
        metricas = ", ".join(f"`{m['name']}`" for m in t.metricas) or "—"
        linhas.append(
            f"| Camada semântica | entidades: {entidades}; dimensões: {dimensoes}; métricas: {metricas}"
            f" (ver {CAMADA_SEMANTICA}) |"
        )
    linhas += [f"| Colunas | {len(t.colunas)} |", ""]
    if not t.colunas:
        return linhas + ["Sem colunas (relação efêmera).", ""]
    linhas += [
        "| Coluna | Tipo | Descrição | Pode ser nulo? | Domínio / valores aceitos | Origem | Observações |",
        "|---|---|---|---|---|---|---|",
    ]
    for nome, decl, tipo_catalogo in t.colunas:
        tipo = decl.get("data_type") or tipo_catalogo or "—"
        linhas.append(
            f"| `{nome}` | `{tipo}` | {_texto(decl.get('description')) or '(sem descrição)'} "
            f"| {_anulavel(t, nome)} | {_dominio(t, nome, decl, por_nome)} | {_origem(t, nome, decl)} "
            f"| {_observacoes(t, nome, decl, fk_por_coluna)} |"
        )
    linhas.append("")
    if t.tipo == "seed":
        valores = _linhas_seed(t)
        if valores:
            cabecalho = list(valores[0])
            linhas += [
                f"Linhas da seed ({len(valores)}):",
                "",
                "| " + " | ".join(f"`{c}`" for c in cabecalho) + " |",
                "|" + "---|" * len(cabecalho),
            ]
            linhas += ["| " + " | ".join(_texto(v[c]) for c in cabecalho) + " |" for v in valores]
            linhas.append("")
    return linhas


def _diagrama_estrela(tabelas: list[Tabela], por_nome: dict[str, Tabela]) -> list[str]:
    """`erDiagram` Mermaid das dimensões, fatos e pontes, das FKs (testadas, semânticas ou declaradas)."""
    nos = {"gold-dim", "gold-fct", "gold-bridge"}
    arestas = []
    for t in tabelas:
        if t.camada not in {"gold-fct", "gold-bridge"}:
            continue
        for coluna, alvo, _, _ in _alvo_fk(t, por_nome):
            destino = por_nome.get(alvo)
            if destino is not None and destino.camada in nos:
                arestas.append(f'    {t.nome} }}o--|| {alvo} : "{coluna}"')
    return ["```mermaid", "erDiagram", *arestas, "```"]


def gerar(manifesto: dict, catalogo: dict | None = None) -> str:
    tabelas = _tabelas(manifesto, catalogo)
    por_nome = {t.nome: t for t in tabelas}
    por_camada: dict[str, list[Tabela]] = defaultdict(list)
    for t in tabelas:
        por_camada[t.camada].append(t)

    linhas = [
        "# Dicionário de dados",
        "",
        "> Gerado por `scripts/gerar_dicionario_dados.py` a partir do manifesto e do catálogo do dbt; não edite à",
        "> mão ([ADR-0019](adr/0019-dicionario-de-dados.md)). Para regenerar: `make dicionario` (depois do",
        "> `make ci` ou de um `dbt build`).",
        "",
        "Detalhe de todas as tabelas disponíveis na base, com os campos de cada uma: o que são, em que",
        "grão, quais as chaves, onde ficam e o que cada coluna guarda. Conceitos de negócio (CNPJ, porte,",
        "situação cadastral, CNAE...) estão em [CAMADA_SEMANTICA.md](CAMADA_SEMANTICA.md) (Parte A); as",
        "dimensões e métricas do MetricFlow, na Parte B; os testes, em [QUALIDADE_DADOS.md](QUALIDADE_DADOS.md).",
        "",
        "## Como ler",
        "",
        "- **Tipo**: o `data_type` do contrato (gold e algumas fontes) ou, na falta dele, o tipo real da coluna",
        "  no DuckDB (catálogo do dbt). As fontes raw guardam todo dado como `varchar`; a tipagem acontece no",
        "  staging.",
        "- **Pode ser nulo?**: lido do teste `not_null`. Sem o teste, o dicionário escreve *não testado* — não",
        "  afirma que a coluna aceita nulos. Com o teste em `severity: warn`, escreve *em geral não*: o teste",
        "  avisa, não barra o build, e o dado real pode ter exceções.",
        "- **Domínio / valores aceitos**: dos testes `accepted_values`, `accepted_range`, `relationships`,",
        "  `tamanho_exato`, `data_nao_futura` e `cnpj_dv_valido`, e das linhas das seeds de domínio. A marca",
        "  `(warn)` indica regra que o dado pode violar (o teste só avisa).",
        "- **Chaves únicas e grão**: a chave primária é a coluna (ou combinação) com teste de unicidade que",
        "  está no grão. Sem esse teste, a linha *Chave primária* diz *não testada* e o grão aparece como",
        "  *declarado, não testado*: é o que a tabela pretende, não o que um teste prova.",
        "- **Lê de / Usada por**: as tabelas de que cada tabela é lida e as que a leem (dependências do",
        "  manifesto do dbt; testes não contam). Ligam a cadeia raw → staging → intermediate → gold.",
        "- **Origem**: nas fontes RFB, o nome do campo no leiaute oficial",
        "  ([`cnpj-metadados.pdf`](https://www.gov.br/receitafederal/dados/cnpj-metadados.pdf), `meta.campo_leiaute`);",
        "  nas fontes da Base dos Dados, a coluna no BigQuery (`meta.coluna_bigquery`); nas fontes do IBGE, o",
        "  campo como publicado (cabeçalho SIDRA ou da planilha, `meta.campo_ibge`); nas demais camadas, a",
        "  linhagem declarada na descrição (*Linhagem:*) ou em `meta.linhagem`, ou a coluna raw do teste",
        "  `taxa_conversao_tipada`.",
        "  Coluna sem origem (—) é cópia direta ou cálculo descrito na própria descrição.",
        "- **Chaves estrangeiras**: *testada* (teste `relationships`), *semântica* (entidade da camada",
        "  semântica, sem teste) ou *declarada* (`meta.fk_declarada`, sem teste).",
        "- **Chaves**: `-1` (NÃO INFORMADO) e `-2` (data inválida, só em `dim_data`) são membros das dimensões;",
        "  um estabelecimento sem par numa dimensão fica com a chave `-1`, nunca é descartado (exceto nos marts",
        "  `original`, que reproduzem os inner joins do MVP).",
        "- **Escopo** (`meta.escopo`): `original` (existia no MVP Spark), `adicao` ou `adaptado`;",
        "  **incremento** (`meta.incremento`): módulo opcional ([ADR-0015](adr/0015-enriquecimento-base-dos-dados.md)).",
        "- **Dados pessoais**: o projeto só guarda o mínimo ([ADR-0008](adr/0008-minimizacao-dados-pessoais.md)):",
        "  contatos (e-mail, telefones, fax) são descartados no staging e o CPF é mascarado no nome.",
        "- O gold fica em `RAIZ_DADOS/gold` (local ou `s3://`); `AAAA-MM` é o mês de referência do extrato.",
        "",
        "## Índice",
        "",
        "| Camada | Tabelas | Colunas |",
        "|---|---|---|",
    ]
    total_t = total_c = 0
    for ident, titulo, _ in CAMADAS:
        itens = por_camada.get(ident, [])
        total_t += len(itens)
        total_c += sum(len(t.colunas) for t in itens)
        linhas.append(
            f"| [{titulo}](#{ident}) | {len(itens)} | {sum(len(t.colunas) for t in itens)} |"
        )
    linhas += [f"| **Total** | **{total_t}** | **{total_c}** |", ""]
    for ident, titulo, descricao in CAMADAS:
        itens = por_camada.get(ident, [])
        if not itens:
            continue
        linhas += [f'<a id="{ident}"></a>', f"### {titulo}", "", descricao, ""]
        linhas += ["| Tabela | Uma linha por | Escopo | Colunas |", "|---|---|---|---|"]
        for t in itens:
            grao = _texto(t.meta.get("grao")) or "—"
            linhas.append(
                f"| [`{t.nome}`](#{t.ancora}) | {grao} | {t.meta.get('escopo', '?')} | {len(t.colunas)} |"
            )
        linhas.append("")
    linhas += [
        '<a id="modelo-estrela"></a>',
        "### Modelo estrela",
        "",
        "Chaves estrangeiras entre fatos, pontes e dimensões do gold (cada linha: muitos para um; o rótulo é",
        "a coluna da tabela de origem). Inclui as FKs testadas, as da camada semântica e as declaradas em",
        "`meta.fk_declarada`; a coluna *Chaves estrangeiras* de cada tabela diz de qual tipo é cada uma.",
        "",
        *_diagrama_estrela(tabelas, por_nome),
        "",
    ]
    for ident, titulo, _ in CAMADAS:
        itens = por_camada.get(ident, [])
        if not itens:
            continue
        linhas += [f"## {titulo}", ""]
        for t in itens:
            linhas += _linhas_tabela(t, por_nome)
    return "\n".join(linhas).rstrip("\n") + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifesto", type=Path, default=MANIFESTO)
    parser.add_argument("--catalogo", type=Path, default=CATALOGO)
    parser.add_argument("--saida", type=Path, default=SAIDA)
    parser.add_argument(
        "--verificar",
        action="store_true",
        help="não escreve: falha se o arquivo versionado diferir do gerado em memória",
    )
    args = parser.parse_args()
    manifesto = json.loads(args.manifesto.read_text(encoding="utf-8"))
    catalogo = (
        json.loads(args.catalogo.read_text(encoding="utf-8")) if args.catalogo.is_file() else None
    )
    texto = gerar(manifesto, catalogo)
    if args.verificar:
        if args.saida.read_text(encoding="utf-8") != texto:
            print(
                f"{args.saida} desatualizado: rode `make dicionario` e versione o resultado",
                file=sys.stderr,
            )
            return 1
        print(f"{args.saida} em dia")
        return 0
    args.saida.write_text(texto, encoding="utf-8")
    print(f"escrito {args.saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
