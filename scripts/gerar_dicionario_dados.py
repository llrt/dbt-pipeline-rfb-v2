# ruff: noqa: E501  (textos longos do dicionário)
"""Gera `docs/DICIONARIO_DADOS.md` (ADR-0019) a partir do `manifest.json` e do `catalog.json` do dbt.

Uso: `make dicionario` (roda `dbt docs generate` sobre o `warehouse.duckdb` de `RAIZ_DADOS` e este
script) ou, com os dois arquivos já gerados em `transform/target/`,
`uv run python scripts/gerar_dicionario_dados.py`. Com `--verificar` não escreve nada: gera em memória
e falha (código 1) se `docs/DICIONARIO_DADOS.md` estiver desatualizado.

O dicionário descreve toda tabela disponível na base: fontes raw (RFB e Base dos Dados), seeds,
staging, intermediate, gold (dimensões, fatos, pontes e marts) e observabilidade. Os tipos vêm do
contrato (`data_type`) e, na falta dele, do catálogo (tipos reais no DuckDB); o resto (grão em
`meta.grao`, campo do leiaute em `meta.campo_leiaute`, coluna no BigQuery em `meta.coluna_bigquery`,
testes, camada semântica) vem do manifesto. As seções de texto fixas ficam neste script.
"""

from __future__ import annotations

import argparse
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

    def __init__(self, camada: str, chave: str, nome: str, no: dict, tipo: str) -> None:
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


def _tabelas(manifesto: dict, catalogo: dict | None) -> list[Tabela]:
    cat_nos = (catalogo or {}).get("nodes", {})
    cat_fontes = (catalogo or {}).get("sources", {})
    tabelas: list[Tabela] = []

    for uid, fonte in manifesto["sources"].items():
        if fonte["package_name"] != PACOTE:
            continue
        camada = {"rfb": "fontes-rfb", "basedosdados": "fontes-bd"}.get(
            fonte["source_name"], "fontes-obs"
        )
        nome = f"{fonte['source_name']}.{fonte['name']}"
        t = Tabela(camada, f"source:{nome}", nome, fonte, "source")
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
        t = Tabela(camada, f"ref:{no['name']}", no["name"], no, no["resource_type"])
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


def _chave_unica(t: Tabela) -> tuple[list[str], list[list[str]]]:
    """(colunas únicas simples, combinações únicas) dos testes `unique`/`unique_combination_of_columns`."""
    simples: list[str] = []
    combinadas: list[list[str]] = []
    for teste in t.testes:
        meta = teste["test_metadata"]
        kwargs = meta.get("kwargs") or {}
        if meta["name"] == "unique":
            simples.append(teste["column_name"])
        elif meta["name"] == "unique_combination_of_columns":
            combinadas.append(list(kwargs["combination_of_columns"]))
    return simples, combinadas


def _severidade(teste: dict) -> str:
    return str((teste.get("config") or {}).get("severity", "error")).lower()


def _chave_primaria(t: Tabela) -> tuple[str, str]:
    """(chave primária, outras chaves únicas) em texto Markdown."""
    simples, combinadas = _chave_unica(t)
    primaria: list[str] | None = None
    entidade = None
    if t.semantica:
        entidade = next(
            (e["expr"] for e in t.semantica["entities"] if e["type"] == "primary"), None
        )
    if entidade and entidade in simples:
        primaria = [entidade]
    elif simples:
        primaria = [next((c for c in simples if c.startswith("sk_")), simples[0])]
    elif combinadas:
        primaria = combinadas[0]
    if primaria is None:
        return "não testada", "—"
    outras = [[c] for c in simples if [c] != primaria] + [c for c in combinadas if c != primaria]
    texto = " + ".join(_codigo(c) for c in primaria)
    # `warn` não garante a unicidade: quem lê precisa saber.
    rebaixados = {
        c
        for teste in t.testes
        if teste["test_metadata"]["name"] == "unique" and _severidade(teste) != "error"
        for c in [teste["column_name"]]
    }
    if len(primaria) == 1 and primaria[0] in rebaixados:
        texto += " (teste `warn`)"
    return texto, "; ".join(" + ".join(_codigo(c) for c in o) for o in outras) or "—"


def _alvo_fk(t: Tabela, por_nome: dict[str, Tabela]) -> list[tuple[str, str, str]]:
    """(coluna, tabela alvo, coluna alvo) dos testes `relationships` e das entidades `foreign`."""
    saida: dict[tuple[str, str], str] = {}
    for teste in t.testes:
        meta = teste["test_metadata"]
        if meta["name"] != "relationships":
            continue
        kwargs = meta["kwargs"]
        achou_ref = PADRAO_REF.search(kwargs["to"])
        achou_src = PADRAO_SOURCE.search(kwargs["to"])
        alvo = achou_ref.group(1) if achou_ref else f"{achou_src.group(1)}.{achou_src.group(2)}"
        saida[(teste["column_name"], alvo)] = kwargs["field"]
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
                saida.setdefault((e["expr"], alvo), campo)
    return sorted((c, a, f) for (c, a), f in saida.items())


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


def _dominio(t: Tabela, coluna: str, por_nome: dict[str, Tabela]) -> str:
    partes: list[str] = []
    for teste in t.testes:
        if teste.get("column_name") != coluna:
            continue
        meta = teste["test_metadata"]
        kwargs = meta.get("kwargs") or {}
        onde = (teste.get("config") or {}).get("where")
        filtro = f" (onde `{_texto(onde)}`)" if onde else ""
        if meta["name"] == "accepted_values":
            partes.append("valores: " + ", ".join(f"`{v}`" for v in kwargs["values"]) + filtro)
        elif meta["name"] == "accepted_range":
            minimo, maximo = kwargs.get("min_value"), kwargs.get("max_value")
            inclusivo = kwargs.get("inclusive", True)
            esq, dir_ = ("≤", "≤") if inclusivo else ("<", "<")
            if minimo is not None and maximo is not None:
                partes.append(f"`{minimo}` {esq} valor {dir_} `{maximo}`" + filtro)
            elif minimo is not None:
                partes.append(f"valor {'≥' if inclusivo else '>'} `{minimo}`" + filtro)
            elif maximo is not None:
                partes.append(f"valor {'≤' if inclusivo else '<'} `{maximo}`" + filtro)
        elif meta["name"] == "relationships":
            achou_ref = PADRAO_REF.search(kwargs["to"])
            achou_src = PADRAO_SOURCE.search(kwargs["to"])
            alvo = achou_ref.group(1) if achou_ref else f"{achou_src.group(1)}.{achou_src.group(2)}"
            partes.append(f"FK → {_link(alvo, por_nome)}.`{kwargs['field']}`" + filtro)
        elif meta["name"] == "tamanho_exato":
            partes.append(f"tamanho exato: {kwargs['tamanho']}" + filtro)
        elif meta["name"] == "data_nao_futura":
            partes.append(f"data não futura (`{_severidade(teste)}`)" + filtro)
        elif meta["name"] == "cnpj_dv_valido":
            partes.append(f"CNPJ com DV válido (`{_severidade(teste)}`)" + filtro)
    return "; ".join(partes) or "—"


def _anulavel(t: Tabela, coluna: str) -> str:
    for teste in t.testes:
        if teste.get("column_name") == coluna and teste["test_metadata"]["name"] == "not_null":
            onde = (teste.get("config") or {}).get("where")
            return f"não (`not_null`, onde `{_texto(onde)}`)" if onde else "não (`not_null`)"
    return "não testado"


def _origem(t: Tabela, coluna: str, decl: dict) -> str:
    meta = {**(decl.get("meta") or {}), **((decl.get("config") or {}).get("meta") or {})}
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
    if t.tipo == "source" and coluna.startswith("_"):
        partes.append("coluna técnica da ingestão")
    achou = PADRAO_LINHAGEM.search(decl.get("description", "") or "")
    if achou:
        partes.append("linhagem: " + _texto(achou.group(1)))
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
    if sentinelas:
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


def _linhas_tabela(t: Tabela, por_nome: dict[str, Tabela]) -> list[str]:
    materializacao, localizacao = _localizacao(t)
    pk, outras = _chave_primaria(t)
    fks = _alvo_fk(t, por_nome)
    fk_por_coluna = {c: (a, f) for c, a, f in fks}
    contrato = bool((t.no.get("config") or {}).get("contract", {}).get("enforced"))
    escopo = t.meta.get("escopo", "?")
    incremento = t.meta.get("incremento", "—")
    grao = t.meta.get("grao")
    linhas = [
        f'<a id="{t.ancora}"></a>',
        f"#### `{t.nome}`",
        "",
        _texto(t.no.get("description")) or "(sem descrição)",
        "",
        "| Atributo | Valor |",
        "|---|---|",
        f"| Grão | {'Uma linha por ' + _texto(grao) + '.' if grao else '—'} |",
        f"| Chave primária (testada) | {pk} |",
        f"| Outras chaves únicas | {outras} |",
        "| Chaves estrangeiras | "
        + ("<br>".join(f"{_codigo(c)} → {_link(a, por_nome)}.`{f}`" for c, a, f in fks) or "—")
        + " |",
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
            f"| {_anulavel(t, nome)} | {_dominio(t, nome, por_nome)} | {_origem(t, nome, decl)} "
            f"| {_observacoes(t, nome, decl, fk_por_coluna)} |"
        )
    linhas.append("")
    return linhas


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
        "  afirma que a coluna aceita nulos.",
        "- **Domínio / valores aceitos**: dos testes `accepted_values`, `accepted_range`, `relationships`,",
        "  `tamanho_exato`, `data_nao_futura` e `cnpj_dv_valido`.",
        "- **Origem**: nas fontes RFB, o nome do campo no leiaute oficial",
        "  ([`cnpj-metadados.pdf`](https://www.gov.br/receitafederal/dados/cnpj-metadados.pdf), `meta.campo_leiaute`);",
        "  nas fontes da Base dos Dados, a coluna no BigQuery (`meta.coluna_bigquery`); nas demais camadas, a",
        "  linhagem declarada na descrição ou a coluna raw do teste `taxa_conversao_tipada`.",
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
