"""Funções de referência de `docs/uso/construcao-agente.md`, extraídas do documento e executadas nas fixtures (RGA).

Roda depois do `make ci` (warehouse de `RAIZ_DADOS`):
- `conectar_somente_leitura` e `exigir_leitura` (RGA-01): as 93 golden queries rodam por elas; leitura de arquivo fora
  da raiz, URL, `COPY ... TO`, `INSTALL`/`LOAD`, `ATTACH` e `SET` falham;
- `comparar_resposta` (RGA-02): aprova o `sql` de cada golden query contra `resposta_esperada_fixtures`;
- `conferir_esquema` (RGA-04): aprova o warehouse das fixtures, bloqueia as golden queries de uma relação mutada e não
  cobra staging, intermediate e seeds num banco só com o gold.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path

import duckdb
import pytest

from rfb_pipeline import caminhos

pytestmark = pytest.mark.skipif(
    "RAIZ_DADOS" not in os.environ, reason="rode via make ci (exporta RAIZ_DADOS)"
)

CATALOGO = json.loads(caminhos.GOLDEN_CATALOGO.read_text(encoding="utf-8"))
MARCADOR = CATALOGO["marcador_raiz_dados"]


def _referencia(marca: str) -> dict:
    """O espaço de nomes do bloco `python` do documento que começa com `# referência: <marca>`."""
    texto = caminhos.GUIA_CONSTRUCAO_AGENTE.read_text(encoding="utf-8")
    (bloco,) = re.findall(rf"```python\n(# referência: {marca}\n.*?)```", texto, re.S)
    espaco: dict = {}
    exec(compile(bloco, f"construcao:{marca}", "exec"), espaco)  # noqa: S102 — código versionado do documento
    return espaco


CONEXAO = _referencia("conexão somente leitura")
comparar_resposta = _referencia("comparar resposta")["comparar_resposta"]
conferir_esquema = _referencia("conferir esquema")["conferir_esquema"]


def _raiz() -> Path:
    return Path(os.environ["RAIZ_DADOS"]).resolve()


@pytest.fixture
def conexao():
    con = CONEXAO["conectar_somente_leitura"](_raiz())
    yield con
    con.close()


def test_golden_queries_rodam_pela_conexao_endurecida_e_comparar_resposta_as_aprova(conexao) -> None:
    exigir_leitura = CONEXAO["exigir_leitura"]
    reprovadas = []
    for consulta in CATALOGO["golden_queries"]:
        sql = consulta["sql"].replace(MARCADOR, str(_raiz()))
        exigir_leitura(conexao, sql)
        cursor = conexao.execute(sql)
        obtido = {"colunas": [d[0] for d in cursor.description], "linhas": cursor.fetchall()}
        if not comparar_resposta(obtido, consulta["resposta_esperada_fixtures"], consulta["camada"]):
            reprovadas.append(consulta["id"])
    assert len(CATALOGO["golden_queries"]) == 93
    assert reprovadas == []


def test_comparar_resposta_aceita_alias_e_ordem_e_recusa_valor_diferente() -> None:
    esperado = {"colunas": ["uf", "qtd"], "linhas": [["ES", 3], ["MG", 1.5]]}
    trocado = {"colunas": ["sigla", "total"], "linhas": [("MG", 1.5), ("ES", 3)]}
    assert comparar_resposta(trocado, esperado, "core")
    assert not comparar_resposta({**trocado, "linhas": [("MG", 1.5), ("ES", 4)]}, esperado, "core")
    assert not comparar_resposta({**trocado, "linhas": [("ES", 3)]}, esperado, "core")
    assert not comparar_resposta({"colunas": ["uf"], "linhas": [("ES",), ("MG",)]}, esperado, "core")


@pytest.mark.parametrize(
    "sql",
    [
        "select length(content) from read_text('{fora}')",
        "select count(*) from read_csv('{fora}', header=false)",
        "select count(*) from glob('{fora_dir}/*')",
        "select count(*) from read_text('/etc/hosts')",
        "select * from read_csv('https://example.com/a.csv')",
        "copy (select 42) to '{fora_dir}/copia.csv'",
        "install httpfs",
        "load httpfs",
        "attach '{fora_dir}/novo.duckdb' as novo",
        "set enable_external_access = true",
        "set allowed_directories = ['/']",
    ],
)
def test_conexao_endurecida_recusa_sair_da_raiz(conexao, tmp_path: Path, sql: str) -> None:
    """RGA-01: mesmo sem o filtro de texto, a própria conexão recusa; o arquivo de fora nunca é lido nem gravado."""
    segredo = tmp_path / "segredo.env"
    segredo.write_text("MOTHERDUCK_TOKEN=nao-pode-vazar\n", encoding="utf-8")
    with pytest.raises(duckdb.Error):
        conexao.execute(sql.format(fora=segredo, fora_dir=tmp_path)).fetchall()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["segredo.env"]


@pytest.mark.parametrize(
    "sql",
    [
        "copy (select 42) to '{raiz}/copia.csv'",  # dentro da raiz: a conexão aceitaria, o filtro recusa
        "install httpfs",
        "attach ':memory:' as m",
        "set threads = 1",
        "select 1; select 2",
        "create table t as select 1",
        "export database '{raiz}/exportado'",
    ],
)
def test_exigir_leitura_recusa_o_que_nao_e_consulta(conexao, sql: str) -> None:
    with pytest.raises(ValueError, match="consulta de leitura"):
        CONEXAO["exigir_leitura"](conexao, sql.format(raiz=_raiz()))
    assert not (_raiz() / "copia.csv").exists()


@pytest.mark.parametrize(
    "sql", ["select 1", "with a as (select 1 as x) select x from a", "from main.dim_porte", "values (1)"]
)
def test_exigir_leitura_aceita_consultas(conexao, sql: str) -> None:
    CONEXAO["exigir_leitura"](conexao, sql)


def test_conferir_esquema_aprova_o_warehouse_das_fixtures(conexao) -> None:
    assert conferir_esquema(conexao, CATALOGO) == ([], [])


def _copia_mutada(tmp_path: Path, comandos: list[str]) -> Path:
    """Cópia do warehouse em `tmp_path` com os `comandos` aplicados (o original nunca é aberto para escrita)."""
    shutil.copy(_raiz() / "warehouse.duckdb", tmp_path / "warehouse.duckdb")
    with duckdb.connect(str(tmp_path / "warehouse.duckdb")) as con:
        for comando in comandos:
            con.execute(comando)
    return tmp_path


def test_conferir_esquema_bloqueia_as_golden_queries_de_relacao_com_coluna_removida(tmp_path: Path) -> None:
    (dim_cnae,) = [r for r in CATALOGO["relacoes"] if r["nome"] == "main.dim_cnae"]
    removida = dim_cnae["colunas"][-1]["nome"]
    raiz = _copia_mutada(
        tmp_path,
        [
            f"create table main.dim_cnae_m as select * exclude ({removida}) from main.dim_cnae",
            "drop view main.dim_cnae",
            "alter table main.dim_cnae_m rename to dim_cnae",
        ],
    )
    con = CONEXAO["conectar_somente_leitura"](raiz)
    problemas, bloqueadas = conferir_esquema(con, CATALOGO)
    con.close()
    assert problemas == [f"dim_cnae.{removida}: coluna ausente no banco (banco mais antigo)"]
    esperadas = sorted(g["id"] for g in CATALOGO["golden_queries"] if "dim_cnae" in g["tabelas"])
    assert bloqueadas == esperadas
    assert any(i.startswith("gq_semantica__") for i in bloqueadas)  # a semântica também é coberta


def test_conferir_esquema_num_banco_so_com_o_gold(tmp_path: Path) -> None:
    """Como no MotherDuck: sem staging, intermediate e seeds, nada é cobrado e nada é bloqueado."""
    fora_do_gold = [
        r["nome"] for r in CATALOGO["relacoes"] if r["camada"] not in ("core", "analytics", "original")
    ]
    with duckdb.connect(str(_raiz() / "warehouse.duckdb"), read_only=True) as con:
        tipos = dict(
            con.execute(
                "select table_name, table_type from information_schema.tables where table_schema = 'main'"
            ).fetchall()
        )
    comandos = [
        f"drop {'view' if tipos[n.removeprefix('main.')] == 'VIEW' else 'table'} {n}" for n in fora_do_gold
    ]
    con = CONEXAO["conectar_somente_leitura"](_copia_mutada(tmp_path, comandos))
    assert conferir_esquema(con, CATALOGO) == ([], [])
    con.close()
