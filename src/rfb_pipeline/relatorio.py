"""Relatório do estudo de caso (CASE-01): executa as `analyses/estudo_caso_*` e escreve o Markdown.

Fluxo: `dbt compile` das analyses (resolve `ref()` e as vars `caso_*`) -> consulta cada SQL
compilado no `warehouse.duckdb` (as views dos marts apontam para o Parquet em `gold/`) -> renderiza
`docs/RELATORIO_ESTUDO_CASO.md`. O corpo é determinístico; só a linha `> Execução dbt` do cabeçalho
da seção de qualidade carrega identificador e horário da última execução.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import duckdb

from rfb_pipeline.configuracao import Configuracao
from rfb_pipeline.erros import ErroIngestao

RAIZ_REPO = Path(__file__).resolve().parents[2]
DIR_TRANSFORM = RAIZ_REPO / "transform"
SAIDA_PADRAO = RAIZ_REPO / "docs" / "RELATORIO_ESTUDO_CASO.md"
PREFIXO_ANALISES = "estudo_caso_"


class RelatorioErro(ErroIngestao):
    """Falha ao compilar as analyses ou ao consultar o warehouse para o relatório."""


Tabela = tuple[list[str], list[tuple]]


def _executavel_dbt() -> list[str]:
    ao_lado = Path(sys.executable).parent / "dbt"
    if ao_lado.is_file():
        return [str(ao_lado)]
    encontrado = shutil.which("dbt")
    if encontrado:
        return [encontrado]
    raise RelatorioErro("executável `dbt` não encontrado; rode `make setup`")


def compilar_analises(dir_transform: Path, raiz_dados: Path, target: str | None) -> dict[str, str]:
    """Roda `dbt compile` nas analyses do estudo de caso e devolve `{nome: SQL compilado}`."""
    comando = [*_executavel_dbt(), "compile", "--select", "path:analyses"]
    if target:
        comando += ["--target", target]
    ambiente = {
        **os.environ,
        "RAIZ_DADOS": str(raiz_dados),
        "DBT_PROFILES_DIR": os.environ.get("DBT_PROFILES_DIR", str(dir_transform)),
    }
    resultado = subprocess.run(
        comando, cwd=dir_transform, env=ambiente, capture_output=True, text=True, check=False
    )
    if resultado.returncode != 0:
        raise RelatorioErro(f"`dbt compile` das analyses falhou:\n{resultado.stdout[-2000:]}")
    compilados = dir_transform / "target" / "compiled" / "rfb" / "analyses"
    sqls = {
        arquivo.stem: arquivo.read_text(encoding="utf-8")
        for arquivo in sorted(compilados.glob(f"{PREFIXO_ANALISES}*.sql"))
    }
    if not sqls:
        raise RelatorioErro(f"nenhuma analysis `{PREFIXO_ANALISES}*` compilada em {compilados}")
    return sqls


def executar_analises(warehouse: Path, sqls: dict[str, str]) -> dict[str, Tabela]:
    """Executa os SQLs compilados no warehouse (somente leitura)."""
    if not warehouse.is_file():
        raise RelatorioErro(f"warehouse não encontrado em {warehouse}; rode `dbt build` antes")
    resultados: dict[str, Tabela] = {}
    with duckdb.connect(str(warehouse), read_only=True) as con:
        for nome, sql in sqls.items():
            try:
                cursor = con.execute(sql)
            except duckdb.Error as exc:
                raise RelatorioErro(f"analysis {nome} falhou: {exc}") from exc
            resultados[nome] = ([d[0] for d in cursor.description], cursor.fetchall())
    return resultados


def ler_qualidade(warehouse: Path) -> tuple[dict, list[tuple]] | None:
    """Resumo da última execução dbt e seus testes que não passaram; `None` sem histórico."""
    with duckdb.connect(str(warehouse), read_only=True) as con:
        try:
            ultimo = con.execute(
                "select invocation_id, executado_em, testes, aprovados, avisos, falhos, pulados "
                "from main.dq_resumo_execucao order by executado_em desc limit 1"
            ).fetchone()
            if ultimo is None:
                return None
            pendentes = con.execute(
                "select nome_teste, status, coalesce(falhas, 0), severidade, escopo "
                "from main.dq_historico_testes where invocation_id = ? and status != 'pass' "
                "order by nome_teste",
                [ultimo[0]],
            ).fetchall()
        except duckdb.Error:
            return None
    chaves = ["invocation_id", "executado_em", "testes", "aprovados", "avisos", "falhos", "pulados"]
    return dict(zip(chaves, ultimo, strict=True)), pendentes


def _numero(valor: object, casas: int | None = None) -> str:
    if valor is None:
        return "—"
    if isinstance(valor, float):
        return f"{valor:.{casas if casas is not None else 2}f}".replace(".", ",")
    return str(valor)


def _tabela(tabela: Tabela, formatos: dict[str, int] | None = None) -> str:
    colunas, linhas = tabela
    formatos = formatos or {}
    if not linhas:
        return "_Nenhum resultado._"
    cabecalho = "| " + " | ".join(colunas) + " |"
    separador = "|" + "|".join("---" for _ in colunas) + "|"
    corpo = [
        "| "
        + " | ".join(_numero(v, formatos.get(c)) for c, v in zip(colunas, linha, strict=True))
        + " |"
        for linha in linhas
    ]
    return "\n".join([cabecalho, separador, *corpo])


def _plural(n: int, singular: str, plural: str) -> str:
    return singular if n == 1 else plural


def _como_dict(tabela: Tabela) -> list[dict]:
    colunas, linhas = tabela
    return [dict(zip(colunas, linha, strict=True)) for linha in linhas]


def renderizar(resultados: dict[str, Tabela], qualidade: tuple[dict, list[tuple]] | None) -> str:
    """Monta o Markdown do relatório a partir das tabelas das analyses."""
    caso = _como_dict(resultados[f"{PREFIXO_ANALISES}parametros"])[0]
    local = f"{str(caso['municipio']).title()}/{caso['uf']}"
    q1 = _como_dict(resultados[f"{PREFIXO_ANALISES}q1_concorrentes"])
    ativos = sum(r["qtd_empresas"] for r in q1 if r["situacao"] == "ATIVA")
    inativos = sum(r["qtd_empresas"] for r in q1 if r["situacao"] != "ATIVA")
    idade = _como_dict(resultados[f"{PREFIXO_ANALISES}q2_q3_idade_porte"])
    surv = _como_dict(resultados[f"{PREFIXO_ANALISES}adicao_sobrevivencia"])[0]
    conc = _como_dict(resultados[f"{PREFIXO_ANALISES}adicao_concorrencia"])
    proximos = _como_dict(resultados[f"{PREFIXO_ANALISES}adicao_fornecedores_proximos"])

    linhas = [
        f"# Relatório do estudo de caso — {local}, CNAE {caso['cnae_alvo']}",
        "",
        f"> Mês de referência **{caso['mes_referencia']}** (extrato de {caso['data_referencia']}). "
        "Gerado por `rfb relatorio` a partir das analyses `transform/analyses/estudo_caso_*`; "
        "não edite à mão.",
        "",
        "## Respostas das perguntas do estudo (notebook 4 do original)",
        "",
        "### 1. Quantas empresas concorrentes há no setor e na localidade?",
        "",
        f"Em {local} há **{ativos}** {_plural(ativos, 'concorrente ativo', 'concorrentes ativos')} "
        f"e **{inativos}** {_plural(inativos, 'inativo', 'inativos')} no CNAE {caso['cnae_alvo']}.",
        "",
        _tabela(resultados[f"{PREFIXO_ANALISES}q1_concorrentes"], {"media_idade": 1}),
        "",
        "### 2 e 3. Idade média e distribuição por porte das empresas ativas",
        "",
        _tabela(resultados[f"{PREFIXO_ANALISES}q2_q3_idade_porte"], {"media_idade": 1}),
        "",
    ]
    if idade:
        unica = idade[0]
        linhas += [
            f"Idade média das ativas: **{_numero(unica['media_idade'], 1)}** anos "
            f"(porte {unica['porte']}).",
            "",
        ]
    linhas += [
        "### 4. Fornecedores potenciais nas proximidades",
        "",
        _tabela(resultados[f"{PREFIXO_ANALISES}q4_fornecedores_resumo"]),
        "",
        "Estabelecimentos ativos da UF com o CNAE de fornecedor entre os secundários:",
        "",
        _tabela(resultados[f"{PREFIXO_ANALISES}q4_fornecedores_secundarios_uf"]),
        "",
        "## Análises novas (adição)",
        "",
        "### Densidade de concorrência (ativos por 10 mil habitantes)",
        "",
        _tabela(resultados[f"{PREFIXO_ANALISES}adicao_concorrencia"], {"ativos_por_10k_hab": 2}),
        "",
    ]
    no_caso = next((r for r in conc if str(r["municipio"]).upper() == caso["municipio"]), None)
    if no_caso:
        linhas += [
            f"{local} tem **{_numero(no_caso['ativos_por_10k_hab'], 2)}** ativos por 10 mil "
            f"habitantes (posição {no_caso['ranking_uf']} na UF).",
            "",
        ]
    linhas += [
        "### Sobrevivência das coortes (todas as coortes e portes do CNAE na UF)",
        "",
        "| Horizonte | Elegíveis | Sobreviventes | Taxa |",
        "|---|---|---|---|",
    ]
    for n in (1, 3, 5):
        taxa = surv[f"taxa_{n}a"]
        taxa_txt = "—" if taxa is None else f"{taxa * 100:.1f}%".replace(".", ",")
        linhas.append(
            f"| {n} {_plural(n, 'ano', 'anos')} | {_numero(surv[f'elegiveis_{n}a'])} "
            f"| {_numero(surv[f'sobreviventes_{n}a'])} | {taxa_txt} |"
        )
    linhas += [
        "",
        "### Dinâmica de mercado (aberturas e encerramentos por ano)",
        "",
        _tabela(resultados[f"{PREFIXO_ANALISES}adicao_dinamica"]),
        "",
        f"### Fornecedores ativos em até {caso['raio_fornecedores_km']} km (CNAEs "
        f"{caso['cnaes_fornecedores']})",
        "",
        _tabela(resultados[f"{PREFIXO_ANALISES}adicao_fornecedores_proximos"], {"distancia_km": 2}),
        "",
    ]
    if not proximos:
        linhas += ["_Nenhum fornecedor ativo dentro do raio._", ""]
    linhas += _secao_qualidade(qualidade)
    return "\n".join(linhas).rstrip("\n") + "\n"


def _secao_qualidade(qualidade: tuple[dict, list[tuple]] | None) -> list[str]:
    linhas = ["## Qualidade dos dados (última execução dbt)", ""]
    if qualidade is None:
        return [*linhas, "_Histórico de testes indisponível (rode `dbt build`)._", ""]
    resumo, pendentes = qualidade
    linhas += [
        f"> Execução dbt `{resumo['invocation_id']}` em {str(resumo['executado_em'])[:19]}.",
        "",
        f"**{resumo['testes']}** {_plural(resumo['testes'], 'teste', 'testes')}: "
        f"{resumo['aprovados']} aprovados, "
        f"{resumo['avisos']} avisos, {resumo['falhos']} falhos, {resumo['pulados']} pulados.",
        "",
    ]
    if pendentes:
        linhas += [
            "| Teste | Status | Linhas com falha | Severidade | Escopo |",
            "|---|---|---|---|---|",
        ]
        linhas += [f"| `{n}` | {s} | {f} | {v} | {e} |" for n, s, f, v, e in pendentes]
        linhas.append("")
    return linhas


def gerar_relatorio(
    configuracao: Configuracao,
    saida: Path = SAIDA_PADRAO,
    target: str | None = None,
    dir_transform: Path = DIR_TRANSFORM,
) -> Path:
    """Gera o relatório e devolve o caminho escrito."""
    warehouse = Path(
        os.environ.get("CAMINHO_DUCKDB") or configuracao.raiz_dados / "warehouse.duckdb"
    )
    sqls = compilar_analises(dir_transform, configuracao.raiz_dados, target)
    resultados = executar_analises(warehouse, sqls)
    texto = renderizar(resultados, ler_qualidade(warehouse))
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(texto, encoding="utf-8")
    return saida
