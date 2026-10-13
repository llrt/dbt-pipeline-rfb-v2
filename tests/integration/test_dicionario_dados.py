# ruff: noqa: E501
"""ADR-0019: `docs/DICIONARIO_DADOS.md` é o dicionário que o manifesto e o catálogo atuais gerariam.

Usa o `manifest.json` e o `catalog.json` de `dbt docs generate` sobre o warehouse do `make ci`
(fixture `manifesto_e_catalogo`). Se falhar, rode `make dicionario` e versione o resultado.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

RAIZ = Path(__file__).resolve().parents[2]
DICIONARIO = RAIZ / "docs" / "DICIONARIO_DADOS.md"
SCRIPT = RAIZ / "scripts" / "gerar_dicionario_dados.py"

sys.path.insert(0, str(RAIZ / "scripts"))

import gerar_dicionario_dados  # noqa: E402

from rfb_pipeline.esquemas import COLUNAS_TECNICAS, ENTIDADES_RFB, TABELAS_BD  # noqa: E402

pytestmark = pytest.mark.skipif(
    "RAIZ_DADOS" not in os.environ, reason="rode via make ci (exporta RAIZ_DADOS)"
)

# Campos do leiaute oficial (`cnpj-metadados.pdf`), na ordem do PDF e das colunas posicionais do raw
# (`esquemas.py`). Conferidos contra o PDF em 2026-10-13 (RDIC); `motivos` não consta do leiaute.
_CODIGO_DESCRICAO = ["CÓDIGO", "DESCRIÇÃO"]
LEIAUTE = {
    "empresas": [
        "CNPJ BÁSICO", "RAZÃO SOCIAL / NOME EMPRESARIAL", "NATUREZA JURÍDICA",
        "QUALIFICAÇÃO DO RESPONSÁVEL", "CAPITAL SOCIAL DA EMPRESA", "PORTE DA EMPRESA",
        "ENTE FEDERATIVO RESPONSÁVEL",
    ],
    "estabelecimentos": [
        "CNPJ BÁSICO", "CNPJ ORDEM", "CNPJ DV", "IDENTIFICADOR MATRIZ/FILIAL", "NOME FANTASIA",
        "SITUAÇÃO CADASTRAL", "DATA SITUAÇÃO CADASTRAL", "MOTIVO SITUAÇÃO CADASTRAL",
        "NOME DA CIDADE NO EXTERIOR", "PAIS", "DATA DE INÍCIO ATIVIDADE", "CNAE FISCAL PRINCIPAL",
        "CNAE FISCAL SECUNDÁRIA", "TIPO DE LOGRADOURO", "LOGRADOURO", "NÚMERO", "COMPLEMENTO",
        "BAIRRO", "CEP", "UF", "MUNICÍPIO", "DDD 1", "TELEFONE 1", "DDD 2", "TELEFONE 2",
        "DDD DO FAX", "FAX", "CORREIO ELETRÔNICO", "SITUAÇÃO ESPECIAL", "DATA DA SITUAÇÃO ESPECIAL",
    ],
    "simples": [
        "CNPJ BÁSICO", "OPÇÃO PELO SIMPLES", "DATA DE OPÇÃO PELO SIMPLES",
        "DATA DE EXCLUSÃO DO SIMPLES", "OPÇÃO PELO MEI", "DATA DE OPÇÃO PELO MEI",
        "DATA DE EXCLUSÃO DO MEI",
    ],
    "cnaes": _CODIGO_DESCRICAO,
    "municipios": _CODIGO_DESCRICAO,
    "naturezas": _CODIGO_DESCRICAO,
    "paises": _CODIGO_DESCRICAO,
    "qualificacoes": _CODIGO_DESCRICAO,
}  # fmt: skip

# Prefixos de nome de modelo/seed/fonte do projeto: citá-los entre crases exige que existam.
PREFIXOS = ("stg_", "int_", "dim_", "fct_", "bridge_", "mart_", "audit__", "dominio_", "dq_")


def _carregar(manifesto_e_catalogo) -> tuple[dict, dict]:
    manifesto, catalogo = (json.loads(p.read_text(encoding="utf-8")) for p in manifesto_e_catalogo)
    return manifesto, catalogo


def test_verificar_passa_com_o_dicionario_versionado(manifesto_e_catalogo) -> None:
    """O gerador em modo `--verificar` (gera em memória e compara) aceita o arquivo versionado."""
    manifesto, catalogo = manifesto_e_catalogo
    resultado = subprocess.run(
        [sys.executable, str(SCRIPT), "--verificar", "--manifesto", str(manifesto),
         "--catalogo", str(catalogo), "--saida", str(DICIONARIO)],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    assert resultado.returncode == 0, (
        "docs/DICIONARIO_DADOS.md desatualizado: rode `make dicionario`\n" + resultado.stderr
    )


def test_dicionario_versionado_bate_com_o_manifesto(manifesto_e_catalogo) -> None:
    manifesto, catalogo = _carregar(manifesto_e_catalogo)
    esperado = gerar_dicionario_dados.gerar(manifesto, catalogo)
    assert DICIONARIO.read_text(encoding="utf-8") == esperado, (
        "docs/DICIONARIO_DADOS.md desatualizado: rode `make dicionario`"
    )


def _colunas_reais_da_fonte(fonte: dict, unique_id: str, catalogo: dict) -> list[str]:
    """Colunas do Parquet raw (fontes externas) ou do catálogo (tabelas do `warehouse.duckdb`)."""
    localizacao = str(gerar_dicionario_dados._meta(fonte).get("external_location", ""))
    raw = re.search(r"/(raw/[^'\"]+)['\"]", localizacao)
    if raw:
        arquivo = Path(os.environ["RAIZ_DADOS"]) / raw.group(1)
        with duckdb.connect() as con:
            return [
                linha[0]
                for linha in con.execute(
                    f"describe select * from read_parquet('{arquivo}', hive_partitioning=false)"
                ).fetchall()
            ]
    return list(catalogo["sources"].get(unique_id, {}).get("columns", {}))


def test_toda_tabela_e_coluna_real_esta_no_dicionario(manifesto_e_catalogo) -> None:
    """Cada modelo, seed e fonte do projeto tem seção; cada coluna real (do catálogo ou do raw) tem linha."""
    manifesto, catalogo = _carregar(manifesto_e_catalogo)
    texto = DICIONARIO.read_text(encoding="utf-8")
    secoes = set(re.findall(r"^#### `([^`]+)`$", texto, flags=re.M))
    esperadas = {
        n["name"]
        for n in manifesto["nodes"].values()
        if n["package_name"] == "rfb" and n["resource_type"] in ("model", "seed")
    } | {
        f"{s['source_name']}.{s['name']}"
        for s in manifesto["sources"].values()
        if s["package_name"] == "rfb"
    }
    assert secoes == esperadas
    for unique_id, no in catalogo["nodes"].items():
        declarado = manifesto["nodes"].get(unique_id)
        if declarado is None or declarado["resource_type"] not in ("model", "seed"):
            continue
        secao = texto.split(f"#### `{declarado['name']}`\n", 1)[1].split("\n#### ", 1)[0]
        for coluna in no["columns"]:
            assert f"| `{coluna.lower()}` |" in secao.lower(), f"{declarado['name']}.{coluna}"
    conferidas = 0
    for unique_id, fonte in manifesto["sources"].items():
        if fonte["package_name"] != "rfb":
            continue
        nome = f"{fonte['source_name']}.{fonte['name']}"
        secao = texto.split(f"#### `{nome}`\n", 1)[1].split("\n#### ", 1)[0]
        reais = _colunas_reais_da_fonte(fonte, unique_id, catalogo)
        assert reais, f"fonte {nome} sem colunas reais (rode o make ci antes)"
        for coluna in reais:
            conferidas += 1
            assert f"| `{coluna.lower()}` |" in secao.lower(), f"{nome}.{coluna}"
    assert conferidas > 100


def _fonte(manifesto: dict, fonte: str, tabela: str) -> dict:
    return next(
        s for s in manifesto["sources"].values()
        if s["package_name"] == "rfb" and s["source_name"] == fonte and s["name"] == tabela
    )  # fmt: skip


def test_campo_do_leiaute_segue_a_ordem_posicional_do_raw(manifesto_e_catalogo) -> None:
    """Toda coluna de dado das fontes RFB (salvo `motivos`) declara o campo do leiaute na ordem do PDF."""
    manifesto, _ = _carregar(manifesto_e_catalogo)
    assert set(LEIAUTE) | {"motivos"} == set(ENTIDADES_RFB)
    for entidade, campos in LEIAUTE.items():
        colunas = ENTIDADES_RFB[entidade].colunas
        assert len(colunas) == len(campos), entidade
        declaradas = _fonte(manifesto, "rfb", entidade)["columns"]
        for coluna, campo in zip(colunas, campos, strict=True):
            meta = gerar_dicionario_dados._meta_coluna(declaradas[coluna])
            assert meta.get("campo_leiaute") == campo, f"rfb.{entidade}.{coluna}"
        for coluna in COLUNAS_TECNICAS:
            assert "campo_leiaute" not in gerar_dicionario_dados._meta_coluna(declaradas[coluna])
    for coluna, decl in _fonte(manifesto, "rfb", "motivos")["columns"].items():
        assert "campo_leiaute" not in gerar_dicionario_dados._meta_coluna(decl), coluna


def test_coluna_bigquery_existe_no_parquet_raw_da_base_dos_dados(manifesto_e_catalogo) -> None:
    """`tabela_bigquery` é o par `dataset.tabela` de `esquemas.py`; `coluna_bigquery` existe no raw."""
    manifesto, _ = _carregar(manifesto_e_catalogo)
    raiz = Path(os.environ["RAIZ_DADOS"])
    for nome, tabela in TABELAS_BD.items():
        fonte = _fonte(manifesto, "basedosdados", nome)
        meta_tabela = gerar_dicionario_dados._meta(fonte)
        assert meta_tabela.get("tabela_bigquery") == f"{tabela.dataset}.{tabela.tabela}", nome
        with duckdb.connect() as con:
            reais = {
                linha[0]
                for linha in con.execute(
                    f"describe select * from read_parquet('{raiz}/raw/bd/{nome}/*.parquet', hive_partitioning=false)"
                ).fetchall()
            }
        for coluna, decl in fonte["columns"].items():
            citada = gerar_dicionario_dados._meta_coluna(decl).get("coluna_bigquery")
            if citada:
                assert citada in reais, f"basedosdados.{nome}.{coluna} → {citada}"


def test_colunas_citadas_no_grao_existem_na_tabela(manifesto_e_catalogo) -> None:
    """`meta.grao` cita colunas entre crases: cada identificador tem de ser coluna da própria tabela."""
    manifesto, _ = _carregar(manifesto_e_catalogo)
    texto = DICIONARIO.read_text(encoding="utf-8")
    nos = [n for n in manifesto["nodes"].values() if n["resource_type"] in ("model", "seed")]
    nos += list(manifesto["sources"].values())
    verificadas = 0
    for no in nos:
        if no["package_name"] != "rfb":
            continue
        nome = no["name"] if "source_name" not in no else f"{no['source_name']}.{no['name']}"
        grao = str(gerar_dicionario_dados._meta(no).get("grao") or "")
        secao = texto.split(f"#### `{nome}`\n", 1)[1].split("\n#### ", 1)[0].lower()
        for citada in re.findall(r"`([a-z_][a-z0-9_]*)`", grao):
            verificadas += 1
            assert f"| `{citada}` |" in secao, f"{nome}: grão cita `{citada}`, que não é coluna"
    assert verificadas > 30


def test_links_e_ancoras_do_dicionario_resolvem() -> None:
    texto = DICIONARIO.read_text(encoding="utf-8")
    ancoras = set(re.findall(r'<a id="([^"]+)"></a>', texto))
    internos = set(re.findall(r"\]\(#([^)]+)\)", texto))
    assert not internos - ancoras, f"links sem âncora: {sorted(internos - ancoras)}"
    for alvo in set(re.findall(r"\]\(((?:adr/)?[A-Z0-9a-z_./-]+\.md)\)", texto)):
        assert (RAIZ / "docs" / alvo).is_file(), f"link quebrado: {alvo}"


def test_identificadores_de_tabela_citados_existem(manifesto_e_catalogo) -> None:
    """Todo `stg_*`/`dim_*`/... entre crases (descrições vindas dos YAMLs inclusive) existe no projeto."""
    manifesto, _ = _carregar(manifesto_e_catalogo)
    existentes = {n["name"] for n in manifesto["nodes"].values() if n["package_name"] == "rfb"}
    existentes |= {s["name"] for s in manifesto["sources"].values() if s["package_name"] == "rfb"}
    existentes |= {m["name"] for m in manifesto["macros"].values() if m["package_name"] == "rfb"}
    inexistentes = set()
    for citado in re.findall(r"`([^`\n]+)`", DICIONARIO.read_text(encoding="utf-8")):
        base = re.split(r"[.\s(]", citado)[0]
        if base.startswith(PREFIXOS) and base not in existentes and not base.endswith("*"):
            inexistentes.add(base)
    assert not inexistentes, f"identificadores inexistentes no dicionário: {sorted(inexistentes)}"


def test_fks_declaradas_e_semanticas_aparecem_na_tabela_e_no_diagrama(manifesto_e_catalogo) -> None:
    """Toda FK sem teste (`meta.fk_declarada` ou entidade `foreign`) de fato/ponte consta da seção e do `erDiagram`."""
    manifesto, _ = _carregar(manifesto_e_catalogo)
    texto = DICIONARIO.read_text(encoding="utf-8")
    diagrama = texto.split("```mermaid\nerDiagram\n", 1)[1].split("\n```", 1)[0]
    # A FK de `sk_mes_referencia` não tem `relationships` nem entidade semântica: só `meta.fk_declarada`.
    assert '    fct_resumo_mensal }o--|| dim_data : "sk_mes_referencia"' in diagrama
    secao = texto.split("#### `fct_resumo_mensal`\n", 1)[1].split("\n#### ", 1)[0]
    assert "`sk_mes_referencia` → [`dim_data`](#dim_data).`sk_data` (declarada)" in secao

    modelos = {
        n["name"]: n
        for n in manifesto["nodes"].values()
        if n["package_name"] == "rfb" and n["resource_type"] == "model"
    }
    esperadas: list[tuple[str, str, str, str]] = []  # (tabela, coluna, alvo, rótulo)
    for nome, no in modelos.items():
        if not nome.startswith(("fct_", "bridge_")):
            continue
        for coluna, decl in no["columns"].items():
            declarada = gerar_dicionario_dados._meta_coluna(decl).get("fk_declarada")
            if declarada:
                esperadas.append((nome, coluna, declarada.split(".")[0], "declarada"))
    primarias = {
        e["name"]: s["name"]
        for s in manifesto["semantic_models"].values()
        if s["package_name"] == "rfb"
        for e in s["entities"]
        if e["type"] == "primary"
    }
    for sem in manifesto["semantic_models"].values():
        if sem["package_name"] != "rfb" or not sem["name"].startswith(("fct_", "bridge_")):
            continue
        for entidade in sem["entities"]:
            if entidade["type"] == "foreign" and entidade["name"] in primarias:
                esperadas.append(
                    (sem["name"], entidade["expr"], primarias[entidade["name"]], "semântica")
                )
    assert len(esperadas) >= 5
    for tabela, coluna, alvo, _ in esperadas:
        assert f'    {tabela} }}o--|| {alvo} : "{coluna}"' in diagrama, (
            f"{tabela}.{coluna} → {alvo}"
        )


def test_faixa_de_idade_atual_e_marcada_como_aviso() -> None:
    """`accepted_range` de `bh_empresas.idade_atual` tem `error_if: ">100"`: 1..100 linhas só avisam."""
    texto = DICIONARIO.read_text(encoding="utf-8")
    secao = texto.split("#### `bh_empresas`\n", 1)[1].split("\n#### ", 1)[0]
    linha = next(x for x in secao.splitlines() if x.startswith("| `idade_atual` |"))
    assert "`0` ≤ valor ≤ `200` (`warn` até 100 linhas; `error` acima)" in linha
