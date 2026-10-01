# ruff: noqa: E501  (textos longos do catálogo)
"""Gera `docs/QUALIDADE_DADOS.md` (DQ-02) a partir do `transform/target/manifest.json`.

Uso: `uv run python scripts/gerar_qualidade_dados.py` (depois de `dbt parse`/`dbt build`).
O catálogo lista todos os testes do projeto por etapa, com severidade, escopo e notebook de origem;
as seções de texto (ingestão, severidade, histórico) são fixas neste script.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
MANIFESTO = RAIZ / "transform" / "target" / "manifest.json"
SAIDA = RAIZ / "docs" / "QUALIDADE_DADOS.md"

ETAPAS = [
    ("Fontes", "Antes", "Entrada do dbt: Parquet raw (checks dos notebooks 2.x do original)."),
    ("Seeds", "Antes", "Domínios estáticos usados por staging e dimensões."),
    ("Staging", "Depois", "Tipagem, CNPJ, datas e ausência de colunas de contato."),
    ("Intermediate", "Depois", "Joins sem descarte e explosão de CNAEs secundários."),
    ("Original", "Depois", "`bh_empresas`/`agg_empresas`: reconciliação, domínios, paridade."),
    ("Core", "Depois", "Modelo estrela: chaves, relacionamentos, reconciliação da fato."),
    ("Análises", "Depois", "Marts analíticos: invariantes numéricas."),
    ("Observabilidade", "Depois", "Resumo do histórico de testes."),
]

# Testes singulares sem diretório próprio -> etapa.
ETAPA_SINGULAR = {
    "cnaes_sem_par_bd": "Fontes",
    "cobertura_municipio_rfb_bd": "Fontes",
    "excecoes_municipio_obsoletas": "Fontes",
    "relacionamentos_fontes_por_mes": "Fontes",
    "estabelecimentos_cnpj_unico_por_mes": "Fontes",
    "particao_selecionada_tem_linhas": "Fontes",
    "sem_colunas_de_contato": "Staging",
    "bh_empresas_descartes_inner_join": "Original",
    "bh_empresas_nome_alterado_por_trim": "Original",
    "agg_empresas_reconciliacao": "Original",
    "paridade_bh_empresas": "Original",
    "dim_data_cobre_data_referencia": "Core",
    "fct_estabelecimentos_reconciliacao": "Core",
    "cnpj_dv_valido_casos": "Staging",
    "data_nao_futura_casos": "Staging",
    "sobrevivencia_invariantes": "Análises",
    "distancias_fornecedores_validas": "Análises",
}

# Notebook de origem dos checks `original` (por alvo ou por teste singular).
ORIGEM_ALVO = {
    "cnaes": "2.1.1", "municipios": "2.1.1", "naturezas": "2.1.1", "motivos": "2.1.1",
    "empresas": "2.2", "estabelecimentos": "2.3", "municipio": "2.1.2", "cnae_2": "2.1.2",
    "bh_empresas": "3", "agg_empresas": "3",
}  # fmt: skip
ORIGEM_SINGULAR = {
    "cnaes_sem_par_bd": "2.1.2",
    "cobertura_municipio_rfb_bd": "2.1.2",
    "excecoes_municipio_obsoletas": "2.1.2",
    "relacionamentos_fontes_por_mes": "2.2 / 2.3",
    "estabelecimentos_cnpj_unico_por_mes": "2.3",
    "agg_empresas_reconciliacao": "3",
}


def _etapa(no: dict) -> str:
    caminho = no["original_file_path"]
    if caminho.startswith("tests/"):
        return ETAPA_SINGULAR.get(no["name"], "Core")
    if caminho.endswith("_sources.yml"):
        return "Fontes"
    for chave, etapa in (
        ("seeds/", "Seeds"),
        ("staging/", "Staging"),
        ("intermediate", "Intermediate"),
        ("marts/original", "Original"),
        ("marts/analytics", "Análises"),
        ("observability", "Observabilidade"),
    ):
        if chave in caminho:
            return etapa
    pais = [p.split(".")[-1] for p in no["depends_on"]["nodes"] if not p.startswith("macro")]
    return "Intermediate" if any(p.startswith("int_") for p in pais) else "Core"


def _alvo(no: dict) -> str:
    # `attached_node` (dbt >= 1.5) é o nó dono do teste; sem ele, cai no heurístico pelo nome (R3-12).
    dono = no.get("attached_node")
    if dono:
        base = dono.split(".")[-1]
        return f"{base}.{no['column_name']}" if no.get("column_name") else base
    pais = [p for p in no["depends_on"]["nodes"] if not p.startswith("macro")]
    nomes = [p.split(".")[-1] for p in pais]
    # o pai "dono" do teste é o que aparece no nome; mantém o primeiro como referência
    candidatos = [n for n in nomes if n in no["name"]]
    base = (candidatos or nomes or ["—"])[0]
    return f"{base}.{no['column_name']}" if no.get("column_name") else base


def _check(no: dict) -> str:
    meta = no.get("test_metadata")
    if meta:
        nome = meta["name"]
        args = {
            k: v for k, v in (meta.get("kwargs") or {}).items() if k not in ("model", "column_name")
        }
        return f"`{nome}`" + (f" {json.dumps(args, ensure_ascii=False)}" if args else "")
    codigo = no.get("raw_code", "")
    codigo = re.sub(r"\{\{\s*config\(.*?\)\s*\}\}", "", codigo, flags=re.S)
    comentario: list[str] = []
    for linha in codigo.splitlines():
        if linha.strip().startswith("--"):
            comentario.append(linha.strip("- ").strip())
        elif comentario:
            break
    texto = " ".join(comentario)
    if texto:
        primeira = re.split(r"(?<=[a-z\)`])\.\s", texto, maxsplit=1)[0]
        return primeira.rstrip(".") + "."
    return f"`{no['name']}` (teste singular)"


def _origem(no: dict) -> str:
    if (no.get("meta") or {}).get("escopo") != "original":
        return "—"
    if no["name"] in ORIGEM_SINGULAR:
        return ORIGEM_SINGULAR[no["name"]]
    alvo = _alvo(no).split(".")[0]
    return ORIGEM_ALVO.get(alvo, "—")


def gerar(manifesto: dict) -> str:
    por_etapa: dict[str, list[tuple]] = defaultdict(list)
    for no in manifesto["nodes"].values():
        if no["resource_type"] != "test" or no["package_name"] != "rfb":
            continue
        severidade = str(no["config"].get("severity", "error")).lower()
        por_etapa[_etapa(no)].append(
            (
                _alvo(no),
                _check(no).replace("|", "\\|").replace("\n", " "),
                severidade,
                (no.get("meta") or {}).get("escopo", "?"),
                _origem(no),
            )
        )
    unitarios = sorted(manifesto.get("unit_tests", {}).values(), key=lambda u: u["name"])

    linhas = [
        "# Qualidade de dados — catálogo de checks",
        "",
        "> Gerado por `scripts/gerar_qualidade_dados.py` a partir do manifesto dbt; não edite à mão.",
        "> Estratégia: [ARCHITECTURE.md §6](../ARCHITECTURE.md); severidades: [ADR-0009](adr/0009-estrategia-testes.md);",
        "> escopo: [ADR-0006](adr/0006-marcacao-escopo.md). Resultados de cada execução ficam em",
        "> `dq_historico_testes` (resumo em `dq_resumo_execucao`) e as linhas com falha dos testes `warn`",
        "> em `main_dbt_test__audit.*` (`store_failures`).",
        "",
        "## Como ler",
        "",
        "- **Antes** = valida a entrada de uma etapa; **Depois** = valida a saída.",
        "- **Severidade**: `error` interrompe o `dbt build`; `warn` registra a anomalia e não interrompe.",
        "  Exceção documentada: `cnpj_dv_valido` é `warn`, mas vira erro se mais de 0,1% dos CNPJs forem",
        "  inválidos **e** houver mais de 100 inválidos (`error_if` do dbt não aceita limites relativos).",
        "  `data_nao_futura` cobre toda data do staging, exceto `dat_exclusao_simples` e `dat_exclusao_mei`",
        "  (exclusão com efeito futuro é legítima; R3-11).",
        "- **Escopo**: `original` (check do MVP; notebook de origem na última coluna) ou `adicao`.",
        "",
        "## Checks da ingestão (Python, antes do dbt)",
        "",
        "| Etapa | Antes | Depois |",
        "|---|---|---|",
        "| Download | mês existe (senão lista os disponíveis); tamanho remoto conhecido | tamanho confere com `getcontentlength`; zip íntegro e sem path traversal; sha256 no manifesto |",
        "| Conversão | encoding latin-1, delimitador `;` e escape fixos | taxa de rejeito ≤ `RFB_MAX_TAXA_REJEITO` (rejeitos em `raw/_rejeitos/`); contagem > 0; `_manifestos/<mes>.json` |",
        "| Gravação | — | Parquet escrito em temp + rename atômico; mesma soma sha256 não reconverte |",
        "",
        "## Checks dbt por etapa",
        "",
        "| Etapa | Momento | O que valida |",
        "|---|---|---|",
    ]
    for etapa, momento, descricao in ETAPAS:
        linhas.append(f"| {etapa} | {momento} | {descricao} ({len(por_etapa[etapa])} testes) |")
    linhas.append("")
    for etapa, momento, _ in ETAPAS:
        itens = sorted(por_etapa[etapa])
        if not itens:
            continue
        linhas += [
            f"### {etapa} ({momento})",
            "",
            "| Alvo | Check | Severidade | Escopo | Origem (notebook) |",
            "|---|---|---|---|---|",
        ]
        linhas += [f"| `{a}` | {c} | {s} | {e} | {o} |" for a, c, s, e, o in itens]
        linhas.append("")
    linhas += [
        "## Testes unitários dbt (regras de negócio)",
        "",
        "| Modelo | Teste | Escopo |",
        "|---|---|---|",
    ]
    for u in unitarios:
        escopo = (u.get("meta") or u.get("config", {}).get("meta") or {}).get("escopo", "?")
        linhas.append(f"| `{u['model']}` | `{u['name']}` | {escopo} |")
    linhas += [
        "",
        "## Histórico de execuções (DQ-02)",
        "",
        "- `on-run-start` cria `main.dq_historico_testes` no `warehouse.duckdb`; `on-run-end` acrescenta uma",
        "  linha por teste executado (dados e unitários): `invocation_id`, `nome_teste`, `status`, `falhas`,",
        "  `severidade`, `escopo`, `executado_em`.",
        "- `dq_resumo_execucao` (view) agrega por execução: aprovados, avisos, falhos, pulados.",
        "- O histórico acumula enquanto o `warehouse.duckdb` existir. O `make ci` recria o warehouse a cada",
        "  execução (histórico só da execução corrente); no ambiente real o arquivo é mantido.",
        "",
    ]
    return "\n".join(linhas)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifesto", type=Path, default=MANIFESTO)
    parser.add_argument("--saida", type=Path, default=SAIDA)
    args = parser.parse_args()
    manifesto = json.loads(args.manifesto.read_text(encoding="utf-8"))
    args.saida.write_text(gerar(manifesto), encoding="utf-8")
    print(f"escrito {args.saida}")


if __name__ == "__main__":
    main()
