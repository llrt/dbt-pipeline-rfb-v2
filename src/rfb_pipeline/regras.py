"""Relatório das regras de negócio (ADR-0020): executa as `analyses/regras_negocio/rn_*`.

Fluxo: `dbt compile` das analyses da pasta -> consulta cada SQL compilado no `warehouse.duckdb`
(somente leitura) -> valida as linhas (só contagens, ADR-0008) -> cruza com o catálogo
`caminhos.CATALOGO_REGRAS` -> renderiza `caminhos.RELATORIO_REGRAS_NEGOCIO`. Inconsistências nos
dados são o conteúdo do relatório, não erro: `rfb regras` só falha se a execução falhar (compilação,
consulta, linha fora do padrão ou analysis sem seção no catálogo, e vice-versa).

O texto abaixo do marcador da seção "Interpretação de AAAA-MM" é escrito à mão (leitura do dado
real) e é preservado quando o relatório é regenerado no mesmo arquivo. Se o mês mudou, ele passa
para a seção "Interpretação anterior (AAAA-MM)" e o comando avisa que precisa ser revisto (RRN-07).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from rfb_pipeline.caminhos import (
    CATALOGO_REGRAS,
    DIR_ADR,
    RELATORIO_REGRAS_NEGOCIO,
    link_de,
    relativo,
)
from rfb_pipeline.configuracao import Configuracao, ler_credenciais_s3
from rfb_pipeline.relatorio import (
    DIR_TRANSFORM,
    SUBPASTA_REGRAS,
    RelatorioErro,
    Tabela,
    compilar_analises,
    executar_analises,
    sql_conexao_s3,
)

SUBPASTA_ANALISES = SUBPASTA_REGRAS
PADRAO_ANALISES = "rn_*.sql"
COLUNAS_OBRIGATORIAS = ("regra", "avaliados", "violacoes")
# Guarda de privacidade em duas camadas (ADR-0008, RRN-01): (1) as quebras só podem ter nomes desta
# lista fechada de dimensões agregadas; (2) nenhum valor de quebra pode parecer um identificador
# (`traz_identificador`).
QUEBRAS_PERMITIDAS = frozenset(
    {
        "situacao",
        "situacao_matriz",
        "uf",
        "porte",
        "natureza_juridica",
        "grupo_natureza",
        "ano",
        "campo",
        "faixa",
        "regime",
        "tabela",
        "estabelecimentos",
        "matrizes",
    }
)
TIPOS_REGRA = ("legal", "leiaute/cadastro", "estrutural", "coerência do projeto")
_PREFIXO_MARCADOR = "<!-- Interpretação manual de "
_SUFIXO_MARCADOR = ": o texto abaixo desta linha é preservado por `rfb regras` no mesmo mês. -->"
TITULO_ANTERIOR = "## Interpretação anterior ("
LIMITE_QUEBRAS = 20
# Quebra que separa casos aceitos pela regra, mas dignos de nota (ex.: o D+1 da RN-13): é mostrada
# mesmo quando a regra não tem violação.
QUEBRA_INFORMATIVA = "faixa"
_RE_ID = re.compile(r"^RN-\d{2}$")
_RE_ANALISE = re.compile(r"^rn_(\d{2})_[a-z0-9_]+$")
_RE_MARCADOR = re.compile(
    "^" + re.escape(_PREFIXO_MARCADOR) + r"(\d{4}-\d{2})" + re.escape(_SUFIXO_MARCADOR) + "$",
    re.MULTILINE,
)
# Separadores de máscara (`.`, `-`, `/`, espaço) entre dígitos ou entre caracteres do CNPJ.
_RE_SEPARADOR_DIGITOS = re.compile(r"(?<=[0-9])[.\-/\s]+(?=[0-9])")
_RE_SEPARADOR_ALFANUMERICO = re.compile(r"(?<=[0-9A-Z])[.\-/]+(?=[0-9A-Z])")
# 8 ou mais dígitos: CNPJ básico (8), CPF (11), CNPJ numérico (14), com ou sem máscara.
_RE_DIGITOS = re.compile(r"[0-9]{8,}")
# CNPJ alfanumérico: 12 posições [0-9A-Z] e os 2 DV numéricos (IN RFB 2.119, art. 2º, par. único).
_RE_CNPJ_ALFANUMERICO = re.compile(r"(?<![0-9A-Z])[0-9A-Z]{12}[0-9]{2}(?![0-9A-Z])")
_RE_SECAO = re.compile(r"^### (RN-\d{2}) — (.+)$")
_RE_TIPO = re.compile(r"^- \*\*Tipo:\*\* (.+?)\.?$")
_RE_ARQUIVO = re.compile(r"transform/analyses/regras_negocio/(rn_\d{2}_[a-z0-9_]+)\.sql")

SQL_CONTEXTO = (
    "select max(_mes_referencia) as mes_referencia, max(_data_referencia) as data_referencia "
    "from main.int_estabelecimentos__enriquecidos"
)


class RegrasErro(RelatorioErro):
    """Falha de execução das regras de negócio (não uma inconsistência nos dados)."""


@dataclass(frozen=True)
class Regra:
    """Uma seção do catálogo: ID, enunciado curto, tipo e a analysis que a verifica."""

    id: str
    titulo: str
    tipo: str
    analise: str


@dataclass(frozen=True)
class Linha:
    """Uma linha padronizada de analysis: a quebra (coluna -> valor) e as contagens."""

    quebra: tuple[tuple[str, str], ...]
    avaliados: int
    violacoes: int


def ler_catalogo(caminho: Path = CATALOGO_REGRAS) -> dict[str, Regra]:
    """Lê as seções `### RN-xx — título` do catálogo, com o tipo e o arquivo da analysis."""
    regras: dict[str, Regra] = {}
    atual: dict | None = None

    def _fechar() -> None:
        if atual is None:
            return
        faltando = [c for c in ("tipo", "analise") if c not in atual]
        if faltando:
            raise RegrasErro(f"catálogo: {atual['id']} sem {', '.join(faltando)}")
        if atual["tipo"] not in TIPOS_REGRA:
            raise RegrasErro(f"catálogo: {atual['id']} com tipo inválido {atual['tipo']!r}")
        regras[atual["id"]] = Regra(**atual)

    for linha in caminho.read_text(encoding="utf-8").splitlines():
        secao = _RE_SECAO.match(linha)
        if secao:
            _fechar()
            if secao.group(1) in regras:
                raise RegrasErro(f"catálogo: {secao.group(1)} repetida")
            atual = {"id": secao.group(1), "titulo": secao.group(2).strip()}
            continue
        if atual is None:
            continue
        tipo = _RE_TIPO.match(linha)
        if tipo and "tipo" not in atual:
            atual["tipo"] = tipo.group(1).strip()
        arquivo = _RE_ARQUIVO.search(linha)
        if arquivo and linha.startswith("- **Analysis:**"):
            atual["analise"] = arquivo.group(1)
    _fechar()
    if not regras:
        raise RegrasErro(f"nenhuma regra `### RN-xx — …` no catálogo {caminho}")
    return regras


def traz_identificador(valor: str) -> bool:
    """Se o valor de uma quebra parece CPF, CNPJ (numérico ou alfanumérico) ou CNPJ básico.

    Tira a máscara antes de procurar (`14.141.414/0001-55`, `529.982.247-25`, `12.ABC.345/01DE-35`)
    e recusa qualquer sequência de 8 ou mais dígitos, o que também barra datas `AAAA-MM-DD`: as
    quebras usam rótulos, não datas.
    """
    texto = valor.upper()
    if _RE_DIGITOS.search(_RE_SEPARADOR_DIGITOS.sub("", texto)):
        return True
    return bool(_RE_CNPJ_ALFANUMERICO.search(_RE_SEPARADOR_ALFANUMERICO.sub("", texto)))


def _inteiro(valor: object, coluna: str, analise: str) -> int:
    if isinstance(valor, bool) or not isinstance(valor, int) or valor < 0:
        raise RegrasErro(f"{analise}: `{coluna}` deve ser inteiro >= 0, veio {valor!r}")
    return valor


def padronizar_linhas(analise: str, tabela: Tabela) -> tuple[str, list[Linha]]:
    """Valida a saída de uma analysis e devolve `(id da regra, linhas)`.

    Exige `regra`, `avaliados` e `violacoes`; as demais colunas são quebras agregadas da lista
    `QUEBRAS_PERMITIDAS`. Recusa valor que pareça identificador (`traz_identificador`) e
    `violacoes > avaliados`. A regra de todas as linhas é a mesma e bate com o nome do arquivo.
    Nenhuma linha quer dizer universo vazio (0 avaliados).
    """
    colunas, linhas = tabela
    faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in colunas]
    if faltando:
        raise RegrasErro(f"{analise}: faltam as colunas {', '.join(faltando)}")
    quebras = [c for c in colunas if c not in COLUNAS_OBRIGATORIAS]
    proibidas = sorted(set(quebras) - QUEBRAS_PERMITIDAS)
    if proibidas:
        raise RegrasErro(
            f"{analise}: colunas fora das quebras agregadas permitidas: {', '.join(proibidas)}"
        )
    nome = _RE_ANALISE.match(analise)
    if nome is None:
        raise RegrasErro(f"{analise}: nome fora do padrão `rn_<nn>_<descricao>`")
    esperado = f"RN-{nome.group(1)}"
    resultado: list[Linha] = []  # sem linhas = universo vazio (ex.: nenhuma matriz baixada)
    for valores in linhas:
        registro = dict(zip(colunas, valores, strict=True))
        if registro["regra"] != esperado:
            raise RegrasErro(f"{analise}: regra {registro['regra']!r} != {esperado}")
        quebra = tuple((c, "—" if registro[c] is None else str(registro[c])) for c in quebras)
        for coluna, valor in quebra:
            if traz_identificador(valor):
                raise RegrasErro(
                    f"{analise}: a quebra `{coluna}` traz um possível identificador (CPF, CNPJ ou "
                    "CNPJ básico, com ou sem máscara, ou CNPJ alfanumérico; ADR-0008)"
                )
        avaliados = _inteiro(registro["avaliados"], "avaliados", analise)
        violacoes = _inteiro(registro["violacoes"], "violacoes", analise)
        if violacoes > avaliados:
            raise RegrasErro(f"{analise}: violacoes ({violacoes}) > avaliados ({avaliados})")
        resultado.append(Linha(quebra, avaliados, violacoes))
    return esperado, resultado


def _milhar(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _pct(violacoes: int, avaliados: int) -> str:
    if avaliados == 0:
        return "—"
    if violacoes == 0:
        return "0 %"
    pct = violacoes * 100 / avaliados
    if pct < 0.01:
        return "< 0,01 %"
    return f"{pct:.2f} %".replace(".", ",")


def _secao_regra(rid: str, regra: Regra, quebras: list[Linha]) -> list[str]:
    """Título, totais e a tabela das quebras (mais violações primeiro) de uma regra."""
    avaliados = sum(x.avaliados for x in quebras)
    violacoes = sum(x.violacoes for x in quebras)
    linhas = [
        f"### {rid} — {regra.titulo}",
        "",
        f"**{_milhar(violacoes)}** {'violação' if violacoes == 1 else 'violações'} em "
        f"**{_milhar(avaliados)}** {'avaliado' if avaliados == 1 else 'avaliados'} "
        f"({_pct(violacoes, avaliados)}). Como ler: [catálogo, {rid}]"
        f"(regras-negocio.md#{rid.lower()}).",
        "",
    ]
    if not quebras or not quebras[0].quebra:
        return linhas
    colunas = [c for c, _ in quebras[0].quebra]
    ordenadas = sorted(quebras, key=lambda x: (-x.violacoes, x.quebra))
    linhas += [
        "| " + " | ".join(colunas) + " | Avaliados | Violações | % |",
        "|" + "---|" * len(colunas) + "---:|---:|---:|",
    ]
    for item in ordenadas[:LIMITE_QUEBRAS]:
        valores = " | ".join(v for _, v in item.quebra)
        linhas.append(
            f"| {valores} | {_milhar(item.avaliados)} | {_milhar(item.violacoes)} "
            f"| {_pct(item.violacoes, item.avaliados)} |"
        )
    if len(ordenadas) > LIMITE_QUEBRAS:
        linhas += ["", f"_Mostrando {LIMITE_QUEBRAS} de {len(ordenadas)} linhas._"]
    return [*linhas, ""]


def renderizar(
    catalogo: dict[str, Regra],
    linhas_por_regra: dict[str, list[Linha]],
    mes_referencia: object,
    data_referencia: object,
    interpretacao: str | None = None,
) -> str:
    """Monta o Markdown: resumo de todas as regras, quebras das violadas, faixas informativas das
    não violadas (quebra `faixa`) e a interpretação."""
    totais = {
        rid: (sum(x.avaliados for x in ls), sum(x.violacoes for x in ls))
        for rid, ls in linhas_por_regra.items()
    }
    violadas = [rid for rid in sorted(catalogo) if totais[rid][1] > 0]
    catalogo_link = link_de(RELATORIO_REGRAS_NEGOCIO, CATALOGO_REGRAS)
    adr_0008 = link_de(RELATORIO_REGRAS_NEGOCIO, DIR_ADR / "0008-minimizacao-dados-pessoais.md")
    adr_0020 = link_de(RELATORIO_REGRAS_NEGOCIO, DIR_ADR / "0020-regras-de-negocio.md")
    linhas = [
        f"# Relatório das regras de negócio — {mes_referencia}",
        "",
        "> **Para quem:** quem usa o dado real e quer saber onde o cadastro foge das regras · "
        "**Quando ler:** depois de cada mês novo processado, antes de confiar num recorte.",
        "",
        f"> Mês de referência **{mes_referencia}** (extrato de {data_referencia}). Gerado por "
        "`rfb regras` a partir das analyses `transform/analyses/regras_negocio/` e do catálogo "
        f"[`{relativo(CATALOGO_REGRAS)}`]({link_de(RELATORIO_REGRAS_NEGOCIO, CATALOGO_REGRAS)}); "
        'não edite à mão acima da seção "Interpretação". Só contagens: nenhum CNPJ, nome ou CPF '
        f"([ADR-0008]({adr_0008})). Inconsistências não falham o comando nem o build "
        f"([ADR-0020]({adr_0020})).",
        "",
        "## Resumo",
        "",
        f"**{len(catalogo)}** regras avaliadas: **{len(catalogo) - len(violadas)}** sem violação "
        f"e **{len(violadas)}** com violação.",
        "",
        "| Regra | Enunciado | Tipo | Avaliados | Violações | % |",
        "|---|---|---|---:|---:|---:|",
    ]
    for rid in sorted(catalogo):
        regra = catalogo[rid]
        avaliados, violacoes = totais[rid]
        linhas.append(
            f"| [{rid}]({catalogo_link}#{rid.lower()}) | {regra.titulo} | {regra.tipo} "
            f"| {_milhar(avaliados)} | {_milhar(violacoes)} | {_pct(violacoes, avaliados)} |"
        )
    linhas += ["", "## Regras com violação", ""]
    if not violadas:
        linhas += ["_Nenhuma regra violada._", ""]
    for rid in violadas:
        linhas += _secao_regra(rid, catalogo[rid], linhas_por_regra[rid])
    informativas = [
        rid
        for rid in sorted(catalogo)
        if rid not in violadas
        and linhas_por_regra[rid]
        and QUEBRA_INFORMATIVA in dict(linhas_por_regra[rid][0].quebra)
    ]
    if informativas:
        linhas += [
            "## Faixas informativas",
            "",
            f"Regras sem violação com a quebra `{QUEBRA_INFORMATIVA}`: casos que a regra aceita e "
            "que vale acompanhar.",
            "",
        ]
        for rid in informativas:
            linhas += _secao_regra(rid, catalogo[rid], linhas_por_regra[rid])
    linhas += [f"## Interpretação de {mes_referencia}", "", marcador(str(mes_referencia))]
    texto = "\n".join(linhas) + "\n"
    if interpretacao is None:
        interpretacao = SEM_INTERPRETACAO
    return texto + interpretacao


SEM_INTERPRETACAO = "\n_Sem interpretação manual (escreva abaixo do comentário acima)._\n"
_RE_TITULO_ANTERIOR = re.compile("^" + re.escape(TITULO_ANTERIOR) + r"(\d{4}-\d{2})\)$", re.M)


def marcador(mes: str) -> str:
    """Comentário que abre o texto manual da interpretação de um mês (`AAAA-MM`)."""
    return f"{_PREFIXO_MARCADOR}{mes}{_SUFIXO_MARCADOR}"


@dataclass(frozen=True)
class Interpretacao:
    """O texto manual depois do marcador de um relatório já gravado e o mês do marcador."""

    mes: str
    texto: str


def interpretacao_existente(saida: Path) -> Interpretacao | None:
    """Mês e texto manual depois do marcador de um relatório gravado; `None` se não houver."""
    if not saida.is_file():
        return None
    texto = saida.read_text(encoding="utf-8")
    achado = _RE_MARCADOR.search(texto)
    if achado is None:
        return None
    return Interpretacao(achado.group(1), texto[achado.end() + 1 :])


def compor_interpretacao(anterior: Interpretacao | None, mes: str) -> tuple[str | None, str | None]:
    """Devolve `(texto manual do relatório de `mes`, aviso)`.

    No mesmo mês, o texto é preservado. Em outro mês, o texto antigo vai para a seção
    "Interpretação anterior (AAAA-MM)", abaixo de um texto vazio, e só uma seção anterior é mantida:
    se o texto antigo não tinha nada escrito, a seção anterior dele continua. Enquanto houver
    seção anterior, o aviso diz que a interpretação precisa ser revista.
    """
    if anterior is None:
        return None, None
    if anterior.mes == mes:
        texto = anterior.texto
    else:
        partes = re.split(r"\n(?=" + re.escape(TITULO_ANTERIOR) + ")", anterior.texto, maxsplit=1)
        escrito = partes[0].strip()
        if escrito and escrito != SEM_INTERPRETACAO.strip():
            secao = (
                f"{TITULO_ANTERIOR}{anterior.mes})\n\n"
                f"> Escrita para os números de {anterior.mes}, não para os de cima. Revise-a, "
                f"escreva a interpretação de {mes} acima e apague esta seção.\n\n{escrito}\n"
            )
        elif len(partes) > 1:
            secao = partes[1]
        else:
            return None, None
        texto = SEM_INTERPRETACAO + "\n" + secao
    achado = _RE_TITULO_ANTERIOR.search(texto)
    if achado is None:
        return texto, None
    return texto, (
        f"a interpretação manual é de {achado.group(1)} e o relatório é de {mes}: revise-a e "
        'apague a seção "Interpretação anterior"'
    )


def _preparo_local(configuracao: Configuracao) -> list[str]:
    """Memória, threads e temporários da conexão de leitura, como no profile (dado real: 73 M)."""
    comandos = []
    limite = os.environ.get("DUCKDB_MEMORY_LIMIT")
    if limite:
        comandos.append(f"SET memory_limit = '{limite.replace(chr(39), '')}'")
    threads = os.environ.get("DUCKDB_THREADS")
    if threads and threads.isdigit():
        comandos.append(f"SET threads = {int(threads)}")
    temporario = configuracao.raiz_dados / "_tmp"
    if temporario.is_dir():
        comandos.append(f"SET temp_directory = '{str(temporario).replace(chr(39), '')}'")
    return comandos


def cruzar_com_catalogo(
    catalogo: dict[str, Regra], resultados: dict[str, Tabela]
) -> dict[str, list[Linha]]:
    """Padroniza cada analysis e exige correspondência 1 para 1 com o catálogo."""
    linhas_por_regra: dict[str, list[Linha]] = {}
    for analise, tabela in resultados.items():
        rid, linhas = padronizar_linhas(analise, tabela)
        if rid not in catalogo:
            raise RegrasErro(f"{analise}: {rid} não tem seção no catálogo {CATALOGO_REGRAS.name}")
        if catalogo[rid].analise != analise:
            raise RegrasErro(
                f"catálogo: {rid} aponta para {catalogo[rid].analise}.sql, mas a analysis é "
                f"{analise}.sql"
            )
        linhas_por_regra[rid] = linhas
    sem_analise = sorted(set(catalogo) - set(linhas_por_regra))
    if sem_analise:
        raise RegrasErro(f"regras do catálogo sem analysis: {', '.join(sem_analise)}")
    return linhas_por_regra


def gerar_relatorio_regras(
    configuracao: Configuracao,
    saida: Path = RELATORIO_REGRAS_NEGOCIO,
    target: str | None = None,
    dir_transform: Path = DIR_TRANSFORM,
    catalogo_caminho: Path = CATALOGO_REGRAS,
) -> tuple[Path, int, int, str | None]:
    """Gera o relatório; devolve `(caminho, regras, regras violadas, aviso)`.

    Não falha por violação. O aviso, quando há, diz que a interpretação manual é de outro mês.
    """
    catalogo = ler_catalogo(catalogo_caminho)
    warehouse = Path(
        os.environ.get("CAMINHO_DUCKDB") or configuracao.raiz_dados / "warehouse.duckdb"
    )
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
            subpasta=SUBPASTA_ANALISES,
            padrao=PADRAO_ANALISES,
        )
    else:
        preparo = _preparo_local(configuracao)
        sqls = compilar_analises(
            dir_transform,
            configuracao.raiz_dados,
            target,
            subpasta=SUBPASTA_ANALISES,
            padrao=PADRAO_ANALISES,
        )
    resultados = executar_analises(
        warehouse, {**sqls, "_contexto": SQL_CONTEXTO}, preparo, segredos
    )
    _, ((mes, data),) = resultados.pop("_contexto")
    linhas_por_regra = cruzar_com_catalogo(catalogo, resultados)
    interpretacao, aviso = compor_interpretacao(interpretacao_existente(saida), str(mes))
    texto = renderizar(catalogo, linhas_por_regra, mes, data, interpretacao)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(texto, encoding="utf-8")
    violadas = sum(1 for ls in linhas_por_regra.values() if any(x.violacoes for x in ls))
    return saida, len(catalogo), violadas, aviso
