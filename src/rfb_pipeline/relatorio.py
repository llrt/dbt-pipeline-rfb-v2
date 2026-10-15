"""Relatório do estudo de caso (CASE-01): executa as `analyses/estudo_caso_*` e escreve o Markdown.

Fluxo: `dbt compile` das analyses (resolve `ref()` e as vars `caso_*`) -> consulta cada SQL
compilado no `warehouse.duckdb` (as views dos marts apontam para o Parquet em `gold/`) -> renderiza
o relatório (`caminhos.RELATORIO_ESTUDO_CASO`). Com `RAIZ_DADOS=s3://` (R3-06/P19) as analyses são
compiladas com a URI S3 e target `s3`, e a conexão de leitura carrega `httpfs` e cria um secret S3
temporário (as views dos marts apontam para `s3://…/gold`). O corpo é determinístico; só a linha
`> Execução dbt` do cabeçalho da seção de qualidade carrega identificador e horário da última
execução.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

import duckdb

from rfb_pipeline.caminhos import CENARIOS_DE_USO, RAIZ_REPO, RELATORIO_ESTUDO_CASO, relativo
from rfb_pipeline.configuracao import Configuracao, CredenciaisS3, ler_credenciais_s3
from rfb_pipeline.erros import ErroIngestao

DIR_TRANSFORM = RAIZ_REPO / "transform"
PREFIXO_ANALISES = "estudo_caso_"
PREFIXO_CENARIOS = "cenario_"  # incremento: enriquecimento_ibge (cenários de uso)
SUBPASTA_REGRAS = "regras_negocio"  # analyses de `rfb regras` (ADR-0020)
SUBPASTA_GOLDEN = "golden"  # golden queries (ADR-0023): testadas e catalogadas, fora do relatório
# Analyses do relatório: as do caso e os cenários de uso (incremento enriquecimento_ibge)
PADRAO_RELATORIO = "*.sql"
LIMITE_LINHAS = 20  # tabelas longas mostram as N primeiras linhas e o total (R3-16)

# incremento: enriquecimento_ibge — relações e colunas do gold da v1.4 que as analyses do IBGE (a do
# caso e os cenários) leem. Um warehouse da v1.3 ainda não reconstruído não as tem: o relatório sai
# com as seções antigas e um aviso no lugar da seção do IBGE (Greptile PR #7), sem falhar.
ANALISE_CASO_IBGE = f"{PREFIXO_ANALISES}enriquecimento_ibge"
REQUISITOS_IBGE: dict[str, tuple[str, ...]] = {
    "dim_municipio": (
        "renda_per_capita_media_2022", "renda_per_capita_mediana_2022", "moradores_renda_2022",
        "ano_va", "va_agropecuaria", "va_industria", "va_servicos", "va_adm_publica",
        "pct_va_agropecuaria", "pct_va_industria", "pct_va_servicos", "pct_va_adm_publica",
        "regic_hierarquia_codigo", "regic_hierarquia", "regic_arranjo_populacional",
        "regic_regiao_influencia", "regic_indice_atracao", "id_municipio_polo_compras",
        "nome_municipio_polo_compras", "pct_compras_no_polo", "ano_cempre",
        "unidades_locais_cempre", "pessoal_ocupado_cempre",
    ),
    "mart_concorrencia_area_mercado": (
        "id_municipio_polo_compras", "nome_municipio_polo_compras", "pct_compras_no_polo",
        "ativos_no_polo",
    ),
    "mart_emprego_setor_municipio": (),
    "bridge_municipio_destino_compras": (),
}  # fmt: skip
AVISO_IBGE_NAO_CONSTRUIDO = (
    "dados do IBGE ainda não construídos; rode `rfb pipeline` ou `rfb atualizar --renovar-ibge`"
)


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


def compilar_analises(
    dir_transform: Path,
    raiz_dados: Path | str,
    target: str | None,
    raiz_dados_local: Path | None = None,
    subpasta: str = "",
    padrao: str = f"{PREFIXO_ANALISES}*.sql",
    variaveis: dict[str, str] | None = None,
) -> dict[str, str]:
    """Roda `dbt compile` nas analyses do estudo de caso e devolve `{nome: SQL compilado}`.

    `raiz_dados` é o `RAIZ_DADOS` do dbt: caminho local ou URI `s3://` (nesse caso
    `raiz_dados_local` vira `RAIZ_DADOS_LOCAL`, onde o profile `s3` acha o `.duckdb`). Compila num
    `--target-path` temporário: o `target/` do projeto guarda o `run_results.json` do último build,
    que outras ferramentas e testes leem (R3-16). `subpasta` e `padrao` escolhem outras analyses
    (ex.: `regras_negocio`, `rn_*.sql`, ADR-0020). Sem `subpasta`, as analyses das regras de negócio
    (RRN-09) e as golden queries (ADR-0023) ficam fora da compilação. `variaveis` vira `--vars`
    (ex.: outro `caso_municipio`).
    """
    selecao = f"path:analyses/{subpasta}" if subpasta else "path:analyses"
    with tempfile.TemporaryDirectory(prefix="rfb-relatorio-") as temporario:
        comando = [
            *_executavel_dbt(),
            "compile",
            "--select",
            selecao,
            "--target-path",
            temporario,
        ]
        if not subpasta:
            comando += [
                "--exclude",
                f"path:analyses/{SUBPASTA_REGRAS}",
                f"path:analyses/{SUBPASTA_GOLDEN}",
            ]
        if target:
            comando += ["--target", target]
        if variaveis:
            comando += ["--vars", json.dumps(variaveis, ensure_ascii=False)]
        ambiente = {
            **os.environ,
            "RAIZ_DADOS": str(raiz_dados),
            "DBT_PROFILES_DIR": os.environ.get("DBT_PROFILES_DIR", str(dir_transform)),
        }
        if raiz_dados_local is not None:
            ambiente["RAIZ_DADOS_LOCAL"] = str(raiz_dados_local)
        resultado = subprocess.run(
            comando, cwd=dir_transform, env=ambiente, capture_output=True, text=True, check=False
        )
        if resultado.returncode != 0:
            raise RelatorioErro(f"`dbt compile` das analyses falhou:\n{resultado.stdout[-2000:]}")
        compilados = Path(temporario) / "compiled" / "rfb" / "analyses" / subpasta
        sqls = {
            arquivo.stem: arquivo.read_text(encoding="utf-8")
            for arquivo in sorted(compilados.glob(padrao))
        }
        if not sqls:
            raise RelatorioErro(f"nenhuma analysis `{padrao}` compilada em {compilados}")
    return sqls


def _literal(texto: str) -> str:
    return "'" + texto.replace("'", "''") + "'"


def sql_conexao_s3(credenciais: CredenciaisS3) -> list[str]:
    """Comandos que preparam a conexão do relatório para ler o gold em S3 (R3-06).

    Espelha o profile `s3` (`transform/profiles.yml`): `httpfs` e um secret S3 **temporário** (só
    desta conexão; não é gravado no `.duckdb`, que é aberto somente leitura).
    """
    opcoes = [
        "TYPE s3",
        f"KEY_ID {_literal(credenciais.access_key_id)}",
        f"SECRET {_literal(credenciais.secret_access_key)}",
        f"ENDPOINT {_literal(credenciais.endpoint_sem_esquema)}",
        f"REGION {_literal(credenciais.regiao)}",
        f"URL_STYLE {_literal(credenciais.url_style)}",
        f"USE_SSL {'true' if credenciais.usa_ssl else 'false'}",
    ]
    return [
        "INSTALL httpfs",
        "LOAD httpfs",
        "CREATE OR REPLACE TEMPORARY SECRET rfb_relatorio_s3 (" + ", ".join(opcoes) + ")",
    ]


def executar_analises(
    warehouse: Path,
    sqls: dict[str, str],
    preparo: list[str] | None = None,
    segredos: tuple[str, ...] = (),
) -> dict[str, Tabela]:
    """Executa os SQLs compilados no warehouse (somente leitura), após os comandos de `preparo`.

    Mensagens de erro do preparo saem com os `segredos` mascarados.
    """
    if not warehouse.is_file():
        raise RelatorioErro(f"warehouse não encontrado em {warehouse}; rode `dbt build` antes")
    resultados: dict[str, Tabela] = {}
    with duckdb.connect(str(warehouse), read_only=True) as con:
        for comando in preparo or []:
            try:
                con.execute(comando)
            except duckdb.Error as exc:  # sem o comando na mensagem: ele contém o secret
                mensagem = str(exc)
                for segredo in segredos:
                    mensagem = mensagem.replace(segredo, "***")
                raise RelatorioErro(
                    f"falha ao preparar a conexão S3 do relatório: {mensagem}"
                ) from None
        for nome, sql in sqls.items():
            try:
                cursor = con.execute(sql)
            except duckdb.Error as exc:
                raise RelatorioErro(f"analysis {nome} falhou: {exc}") from exc
            resultados[nome] = ([d[0] for d in cursor.description], cursor.fetchall())
    return resultados


# incremento: enriquecimento_ibge
def faltas_ibge(warehouse: Path) -> list[str]:
    """Relações e colunas de `REQUISITOS_IBGE` ausentes do warehouse (`information_schema`).

    Vazia quando o gold da v1.4 já foi construído; `relação` ou `relação.coluna` no warehouse da
    v1.3 ainda não reconstruído.
    """
    if not warehouse.is_file():
        return []  # `executar_analises` dá o erro claro de warehouse ausente
    nomes = ", ".join(_literal(nome) for nome in REQUISITOS_IBGE)
    with duckdb.connect(str(warehouse), read_only=True) as con:
        existentes = con.execute(
            "select table_name, column_name from information_schema.columns "
            f"where table_schema = 'main' and table_name in ({nomes})"
        ).fetchall()
    colunas: dict[str, set[str]] = {}
    for tabela, coluna in existentes:
        colunas.setdefault(tabela, set()).add(coluna)
    faltas: list[str] = []
    for relacao, requeridas in REQUISITOS_IBGE.items():
        if relacao not in colunas:
            faltas.append(relacao)
            continue
        faltas += [f"{relacao}.{c}" for c in requeridas if c not in colunas[relacao]]
    return faltas


def _resumir_faltas(faltas: list[str]) -> str:
    """`a, b, c.x, c.y` -> `a, b, c (2 colunas)`."""
    relacoes = [f for f in faltas if "." not in f]
    por_relacao: dict[str, int] = {}
    for falta in faltas:
        if "." in falta:
            relacao = falta.split(".", 1)[0]
            por_relacao[relacao] = por_relacao.get(relacao, 0) + 1
    colunas = [f"{r} ({n} {_plural(n, 'coluna', 'colunas')})" for r, n in por_relacao.items()]
    return ", ".join(relacoes + colunas)


def _analise_ibge(nome: str) -> bool:
    return nome == ANALISE_CASO_IBGE or nome.startswith(PREFIXO_CENARIOS)


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
        except (
            duckdb.CatalogException
        ):  # só "tabela inexistente"; outro erro (coluna renomeada) propaga
            return None
    chaves = ["invocation_id", "executado_em", "testes", "aprovados", "avisos", "falhos", "pulados"]
    return dict(zip(chaves, ultimo, strict=True)), pendentes


def _numero(valor: object, casas: int | None = None) -> str:
    if valor is None:
        return "—"
    if isinstance(valor, float):
        return f"{valor:.{casas if casas is not None else 2}f}".replace(".", ",")
    return str(valor)


def _tabela(
    tabela: Tabela, formatos: dict[str, int] | None = None, limite: int | None = None
) -> str:
    """Tabela Markdown; com `limite`, mostra só as primeiras linhas e informa o total."""
    colunas, linhas = tabela
    formatos = formatos or {}
    if not linhas:
        return "_Nenhum resultado._"
    total = len(linhas)
    if limite is not None and total > limite:
        linhas = linhas[:limite]
        rodape = f"_Mostrando as {limite} primeiras de {total} linhas._"
    else:
        rodape = None
    cabecalho = "| " + " | ".join(colunas) + " |"
    separador = "|" + "|".join("---" for _ in colunas) + "|"
    corpo = [
        "| "
        + " | ".join(_numero(v, formatos.get(c)) for c, v in zip(colunas, linha, strict=True))
        + " |"
        for linha in linhas
    ]
    return "\n".join([cabecalho, separador, *corpo, *(["", rodape] if rodape else [])])


def _plural(n: int, singular: str, plural: str) -> str:
    return singular if n == 1 else plural


def _como_dict(tabela: Tabela) -> list[dict]:
    colunas, linhas = tabela
    return [dict(zip(colunas, linha, strict=True)) for linha in linhas]


def renderizar(
    resultados: dict[str, Tabela],
    qualidade: tuple[dict, list[tuple]] | None,
    aviso_ibge: str | None = None,
) -> str:
    """Monta o Markdown do relatório a partir das tabelas das analyses.

    Com `aviso_ibge` (warehouse sem o gold do IBGE), a seção do IBGE traz só o aviso.
    """
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
    com_idade = [r for r in idade if r["media_idade"] is not None and r["qtd_empresas"]]
    if com_idade:
        total_idade = sum(r["qtd_empresas"] for r in com_idade)
        media = sum(r["media_idade"] * r["qtd_empresas"] for r in com_idade) / total_idade
        linhas += [
            f"Idade média das ativas: **{_numero(media, 1)}** anos "
            f"(média ponderada por `qtd_empresas`, {total_idade} "
            f"{_plural(total_idade, 'empresa', 'empresas')}).",
            "",
        ]
    linhas += [
        "### 4. Fornecedores potenciais nas proximidades",
        "",
        _tabela(resultados[f"{PREFIXO_ANALISES}q4_fornecedores_resumo"]),
        "",
        "> **Nota (adaptado):** o notebook 4 original retornava 0 nas buscas por microrregião e "
        "mesorregião porque comparava nomes em MAIÚSCULAS com a grafia mista da Base dos Dados. "
        "Com a comparação corrigida (`upper()` dos dois lados), essas buscas passam a achar "
        'fornecedores onde o original concluía "nada nas imediações".',
        "",
        "Estabelecimentos ativos da UF com o CNAE de fornecedor entre os secundários:",
        "",
        _tabela(
            resultados[f"{PREFIXO_ANALISES}q4_fornecedores_secundarios_uf"], limite=LIMITE_LINHAS
        ),
        "",
        "## Análises novas (adição)",
        "",
        "### Densidade de concorrência (ativos por 10 mil habitantes)",
        "",
        _tabela(
            resultados[f"{PREFIXO_ANALISES}adicao_concorrencia"],
            {"ativos_por_10k_hab": 2},
            LIMITE_LINHAS,
        ),
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
        '> **Como ler:** "ativa" é a situação cadastral da Receita Federal, não operação efetiva. '
        "Empresas sem atividade continuam ATIVAS até serem declaradas INAPTAS ou baixadas, "
        "então as taxas de sobrevivência saem mais altas que as de fontes que medem operação "
        "(ex.: IBGE, Demografia das Empresas).",
        "",
        "### Dinâmica de mercado (aberturas e encerramentos por ano)",
        "",
        _tabela(resultados[f"{PREFIXO_ANALISES}adicao_dinamica"]),
        "",
        f"### Fornecedores ativos em até {caso['raio_fornecedores_km']} km (CNAEs "
        f"{caso['cnaes_fornecedores']})",
        "",
        _tabela(
            resultados[f"{PREFIXO_ANALISES}adicao_fornecedores_proximos"],
            {"distancia_km": 2},
            LIMITE_LINHAS,
        ),
        "",
    ]
    if not proximos:
        linhas += ["_Nenhum fornecedor ativo dentro do raio._", ""]
    linhas += _secao_area_mercado(resultados, caso, local)  # incremento: enriquecimento_bd
    linhas += _secao_ibge(resultados, caso, local, aviso_ibge)  # incremento: enriquecimento_ibge
    linhas += _secao_qualidade(qualidade)
    return "\n".join(linhas).rstrip("\n") + "\n"


# incremento: enriquecimento_bd
def _secao_area_mercado(resultados: dict[str, Tabela], caso: dict, local: str) -> list[str]:
    """Área de mercado (município, vizinhos, região metropolitana); vazia sem a analysis."""
    tabela = resultados.get(f"{PREFIXO_ANALISES}enriquecimento_area_mercado")
    if tabela is None:
        return []
    linhas = [
        "## Área de mercado (enriquecimento com a Base dos Dados)",
        "",
        f"Concorrência no CNAE {caso['cnae_alvo']} em {local}, nos municípios vizinhos e na região "
        "metropolitana (Censo 2022 e vizinhança da Base dos Dados; incremento "
        "`enriquecimento_bd`).",
        "",
    ]
    dados = _como_dict(tabela)
    if not dados:
        return [*linhas, f"_{local} não tem estabelecimentos deste CNAE na base._", ""]
    d = dados[0]
    rm = d["nome_regiao_metropolitana"]
    linhas += [
        "| Escopo | Ativos | Inativos |",
        "|---|---|---|",
        f"| {local} | {_numero(d['ativos'])} | {_numero(d['inativos'])} |",
        f"| {_numero(d['qtd_vizinhos'])} {_plural(d['qtd_vizinhos'], 'vizinho', 'vizinhos')} "
        f"| {_numero(d['ativos_vizinhos'])} | {_numero(d['inativos_vizinhos'])} |",
        f"| Região metropolitana ({rm}) | {_numero(d['ativos_regiao_metropolitana'])} "
        f"| {_numero(d['inativos_regiao_metropolitana'])} |",
        "",
        f"Indicadores de {local}: **{_numero(d['ativos_por_mil_domicilios'], 4)}** ativos por mil "
        f"domicílios e **{_numero(d['ativos_por_km2'], 6)}** por km²; na área de mercado "
        f"(município + vizinhos): **{_numero(d['ativos_area_por_mil_domicilios'], 4)}** por mil "
        f"domicílios e **{_numero(d['ativos_area_por_km2'], 6)}** por km².",
        "",
    ]
    return linhas


# incremento: enriquecimento_ibge
def _secao_ibge(
    resultados: dict[str, Tabela], caso: dict, local: str, aviso: str | None = None
) -> list[str]:
    """Renda, polo de compras e CEMPRE do caso, mais três cenários; vazia sem a analysis do caso.

    Com `aviso` (gold do IBGE ainda não construído), só o título e o aviso.
    """
    titulo = "## Enriquecimento com o IBGE (renda, rede urbana e CEMPRE)"
    if aviso is not None:
        return [titulo, "", f"> **Aviso:** {aviso}.", ""]
    tabela = resultados.get(ANALISE_CASO_IBGE)
    if tabela is None:
        return []
    linhas = [
        titulo,
        "",
        "Renda per capita do Censo 2022, hierarquia urbana e polo de compras da REGIC 2018 e o "
        f"CEMPRE da classe do CNAE {caso['cnae_alvo']} (incremento `enriquecimento_ibge`). Os anos "
        "são diferentes: renda de 2022 (nominal), REGIC de 2018, CEMPRE do `ano_cempre` e ativos "
        "da RFB do mês de referência. O CEMPRE não conta MEI; com sigilo do IBGE o pessoal ocupado "
        f"fica vazio, nunca imputado. Como usar cada base: `{relativo(CENARIOS_DE_USO)}`.",
        "",
    ]
    dados = _como_dict(tabela)
    if not dados:
        return [*linhas, f"_{local} não está na dimensão de municípios._", ""]
    formatos = {"renda_per_capita_media_2022": 2, "pct_compras_no_polo": 2}
    colunas, registros = tabela
    sem_ordem = (colunas[1:], [_sem_decimal(r[1:]) for r in registros])
    linhas += [_tabela(sem_ordem, formatos), ""]
    caso_ibge = next((r for r in dados if r["escopo"] == "município do caso"), None)
    polo = next((r for r in dados if r["escopo"] == "polo de compras"), None)
    if caso_ibge and polo:
        # RIBG-03: o polo pode ficar noutra UF (Iúna/ES -> Manhuaçu/MG)
        nome_polo = polo["municipio"]
        if polo.get("uf") and polo["uf"] != caso_ibge.get("uf"):
            nome_polo = f"{nome_polo}/{polo['uf']}"
        linhas += [
            "Para comprar móveis e eletroeletrônicos fora do município, os moradores de "
            f"{local} vão principalmente a **{nome_polo}** "
            f"({_numero(caso_ibge['pct_compras_no_polo'], 1)} % desses deslocamentos), onde há "
            f"**{_numero(polo['ativos_cnae'])}** "
            f"{_plural(polo['ativos_cnae'] or 0, 'ativo', 'ativos')} do CNAE {caso['cnae_alvo']}.",
            "",
        ]
    elif caso_ibge and caso_ibge["polo_compras"] is None:
        linhas += [f"_{local} não tem polo de compras na REGIC 2018._", ""]
    elif caso_ibge:  # polo fora da dimensão de municípios: só o nome e o %
        linhas += [
            "Para comprar móveis e eletroeletrônicos fora do município, os moradores de "
            f"{local} vão principalmente a **{caso_ibge['polo_compras']}** "
            f"({_numero(caso_ibge['pct_compras_no_polo'], 1)} % desses deslocamentos).",
            "",
        ]
    cenarios = (
        ("polo_compras_evasao", "Polo de compras dos municípios da UF", {"pct_compras_no_polo": 1}),
        (
            "tamanho_setor_cempre",
            "Tamanho do setor na UF: CEMPRE × RFB",
            {"pessoal_por_unidade": 2},
        ),
        ("renda_concorrencia", "Renda acima da mediana da UF e concorrência", {}),
    )
    for nome, titulo, formatos_cenario in cenarios:
        cenario = resultados.get(f"{PREFIXO_CENARIOS}{nome}")
        if cenario is None:
            continue
        colunas_c, registros_c = cenario
        linhas += [
            f"### {titulo}",
            "",
            _tabela(
                (colunas_c, [_sem_decimal(r) for r in registros_c]), formatos_cenario, LIMITE_LINHAS
            ),
            "",
        ]
    return linhas


def _sem_decimal(linha: tuple) -> tuple:
    """`Decimal` (renda, salários) vira `float`, para sair com vírgula como os demais números."""
    return tuple(float(v) if isinstance(v, Decimal) else v for v in linha)


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
    saida: Path = RELATORIO_ESTUDO_CASO,
    target: str | None = None,
    dir_transform: Path = DIR_TRANSFORM,
) -> Path:
    """Gera o relatório e devolve o caminho escrito."""
    warehouse = Path(
        os.environ.get("CAMINHO_DUCKDB") or configuracao.raiz_dados / "warehouse.duckdb"
    )
    preparo: list[str] = []
    segredos: tuple[str, ...] = ()
    if configuracao.raiz_dados_s3 is not None:
        credenciais = ler_credenciais_s3()
        preparo = sql_conexao_s3(credenciais)
        segredos = (credenciais.secret_access_key, credenciais.access_key_id)
        sqls = compilar_analises(
            dir_transform,
            configuracao.raiz_dados_s3,
            target or "s3",
            configuracao.raiz_dados,
            padrao=PADRAO_RELATORIO,
        )
    else:
        sqls = compilar_analises(
            dir_transform, configuracao.raiz_dados, target, padrao=PADRAO_RELATORIO
        )
    aviso_ibge = None
    faltas = faltas_ibge(warehouse)
    if faltas:  # incremento: enriquecimento_ibge — warehouse da v1.3 ainda não reconstruído
        aviso_ibge = AVISO_IBGE_NAO_CONSTRUIDO
        sqls = {nome: sql for nome, sql in sqls.items() if not _analise_ibge(nome)}
        print(
            f"aviso: relatório sem a seção do IBGE: {aviso_ibge} (faltam no warehouse: "
            f"{_resumir_faltas(faltas)})",
            file=sys.stderr,
            flush=True,
        )
    resultados = executar_analises(warehouse, sqls, preparo, segredos)
    texto = renderizar(resultados, ler_qualidade(warehouse), aviso_ibge)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(texto, encoding="utf-8")
    return saida
