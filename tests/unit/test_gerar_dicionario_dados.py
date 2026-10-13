# ruff: noqa: E501
"""Regras do gerador do dicionário de dados (ADR-0019) sobre um manifesto mínimo, sem dbt."""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import gerar_dicionario_dados as gerador  # noqa: E402


def _modelo(nome: str, caminho: str, colunas: dict, **extra) -> dict:
    return {
        "resource_type": "model",
        "package_name": "rfb",
        "name": nome,
        "original_file_path": caminho,
        "description": f"Modelo {nome}.",
        "config": extra.pop("config", {"materialized": "table"}),
        "meta": extra.pop("meta", {}),
        "columns": colunas,
        "depends_on": {"nodes": extra.pop("depende", [])},
        **extra,
    }


def _teste(
    uid: str, modelo: str, coluna: str | None, nome: str, severidade: str = "error", **kwargs
) -> dict:
    return {
        "unique_id": uid,
        "resource_type": "test",
        "package_name": "rfb",
        "column_name": coluna,
        "config": {"severity": severidade},
        "test_metadata": {
            "name": nome,
            "kwargs": {"model": f"{{{{ get_where_subquery(ref('{modelo}')) }}}}", **kwargs},
        },
    }


def _manifesto() -> dict:
    """`dim_a` (dimensão) e `fct_b` (fato) com um teste de cada tipo, em `error` e em `warn`."""
    nos = {
        "model.rfb.dim_a": _modelo(
            "dim_a",
            "models/marts/core/_core.yml",
            {
                "sk_a": {"description": "Chave.", "data_type": "integer"},
                "codigo": {"description": "Código natural.", "data_type": "varchar"},
                "sem_teste": {"description": "Sem teste.", "data_type": "varchar"},
            },
            meta={"grao": "a (`sk_a`)"},
        ),
        "model.rfb.fct_b": _modelo(
            "fct_b",
            "models/marts/core/_core.yml",
            {
                "id": {"description": "Identificador.", "data_type": "varchar"},
                "sk_a": {"description": "Chave de `dim_a`.", "data_type": "integer"},
                "sk_orfa": {
                    "description": "Sem -1.",
                    "data_type": "integer",
                    "config": {"meta": {"membro_desconhecido": False}},
                },
                "situacao": {"description": "Situação.", "data_type": "varchar"},
                "mes": {
                    "description": "Mês.",
                    "data_type": "varchar",
                    "meta": {"fk_declarada": "dim_a.sk_a"},
                },
            },
            meta={"grao": "b (`id`)"},
            depende=["model.rfb.dim_a", "source.rfb.rfb.empresas"],
        ),
        "model.rfb.fct_sem_chave": _modelo(
            "fct_sem_chave",
            "models/marts/core/_core.yml",
            {"codigo_rfb": {"description": "Código.", "data_type": "varchar"}},
            meta={"grao": "linha (`codigo`)"},
        ),
        "test.rfb.t1": _teste("test.rfb.t1", "dim_a", "sk_a", "unique"),
        "test.rfb.t2": _teste("test.rfb.t2", "dim_a", "sk_a", "not_null"),
        "test.rfb.t3": _teste("test.rfb.t3", "dim_a", "codigo", "not_null", "warn"),
        "test.rfb.t4": _teste("test.rfb.t4", "dim_a", "codigo", "unique", "warn"),
        "test.rfb.t5": _teste("test.rfb.t5", "fct_b", "id", "unique"),
        "test.rfb.t6": _teste(
            "test.rfb.t6", "fct_b", "sk_a", "relationships", to="ref('dim_a')", field="sk_a"
        ),
        "test.rfb.t7": _teste(
            "test.rfb.t7", "fct_b", "situacao", "accepted_values", "warn", values=["1", "2"]
        ),
        "test.rfb.t8": _teste(
            "test.rfb.t8", "fct_b", "sk_orfa", "relationships", to="ref('dim_a')", field="sk_a"
        ),
        "test.rfb.t9": _teste("test.rfb.t9", "fct_b", "sk_a", "not_null"),
        "test.rfb.t10": _teste("test.rfb.t10", "fct_sem_chave", "codigo_rfb", "unique", "warn"),
    }
    fonte = {
        "package_name": "rfb",
        "source_name": "rfb",
        "name": "empresas",
        "description": "Fonte.",
        "meta": {"grao": "empresa (`cnpj_raiz`)"},
        "columns": {
            "cnpj_raiz": {
                "description": "Raiz.",
                "data_type": "varchar",
                "meta": {"campo_leiaute": "CNPJ BÁSICO"},
            },
            "_arquivo_origem": {"description": "Arquivo.", "data_type": "varchar"},
        },
        "depends_on": {"nodes": []},
    }
    return {
        "nodes": nos,
        "sources": {"source.rfb.rfb.empresas": fonte},
        "semantic_models": {},
        "metrics": {},
    }


def _secao(texto: str, nome: str) -> str:
    return texto.split(f"#### `{nome}`\n", 1)[1].split("\n#### ", 1)[0]


def _linha(secao: str, coluna: str) -> list[str]:
    linha = next(x for x in secao.splitlines() if x.startswith(f"| `{coluna}` |"))
    return [c.strip() for c in linha.strip("|").split(" | ")]


def test_nulidade_distingue_error_warn_e_sem_teste() -> None:
    texto = gerador.gerar(_manifesto())
    dim = _secao(texto, "dim_a")
    assert _linha(dim, "sk_a")[3] == "não (`not_null`)"
    assert "em geral não (`not_null` `warn`: pode haver exceções)" in _linha(dim, "codigo")[3]
    assert _linha(dim, "sem_teste")[3] == "não testado"


def test_dominio_marca_warn_em_accepted_values() -> None:
    fato = _secao(gerador.gerar(_manifesto()), "fct_b")
    assert _linha(fato, "situacao")[4] == "valores: `1`, `2` (`warn`)"


def test_chave_primaria_e_outras_chaves_marcam_warn() -> None:
    texto = gerador.gerar(_manifesto())
    dim = _secao(texto, "dim_a")
    assert "| Chave primária (testada) | `sk_a` |" in dim
    assert "| Outras chaves únicas | `codigo` (`warn`) |" in dim


def test_unique_warn_fora_do_grao_nao_vira_chave_primaria() -> None:
    """`unique` só em `warn` e fora de `meta.grao`: a tabela fica 'não testada' e o grão, 'declarado'."""
    secao = _secao(gerador.gerar(_manifesto()), "fct_sem_chave")
    assert "| Chave primária (testada) | não testada |" in secao
    assert "| Outras chaves únicas | `codigo_rfb` (`warn`) |" in secao
    assert "| Grão (declarado, não testado) |" in secao
    assert "| Grão (declarado, não testado) |" not in _secao(gerador.gerar(_manifesto()), "dim_a")


def test_fks_testada_e_declarada_aparecem_com_a_origem() -> None:
    fato = _secao(gerador.gerar(_manifesto()), "fct_b")
    assert "`sk_a` → [`dim_a`](#dim_a).`sk_a` (testada)" in fato
    assert "`mes` → [`dim_a`](#dim_a).`sk_a` (declarada)" in fato


def test_membro_desconhecido_false_troca_a_nota_do_menos_um() -> None:
    fato = _secao(gerador.gerar(_manifesto()), "fct_b")
    assert "sem par na dimensão → chave `-1`" in _linha(fato, "sk_a")[6]
    assert "não recebe a chave `-1`" in _linha(fato, "sk_orfa")[6]


def test_le_de_e_usada_por_vem_do_depends_on() -> None:
    texto = gerador.gerar(_manifesto())
    assert "| Lê de | [`dim_a`](#dim_a), `rfb.empresas` |" not in texto  # a fonte é linkada
    assert "| Lê de | [`dim_a`](#dim_a), [`rfb.empresas`](#rfb-empresas) |" in _secao(
        texto, "fct_b"
    )
    assert "| Usada por | [`fct_b`](#fct_b) |" in _secao(texto, "dim_a")
    assert "| Usada por | [`fct_b`](#fct_b) |" in _secao(texto, "rfb.empresas")


def test_fonte_lista_tambem_as_colunas_tecnicas() -> None:
    secao = _secao(gerador.gerar(_manifesto()), "rfb.empresas")
    assert "coluna técnica da ingestão" in _linha(secao, "_arquivo_origem")[5]
    assert "leiaute RFB: **CNPJ BÁSICO**" in _linha(secao, "cnpj_raiz")[5]


def test_particao_do_gold_usa_mes_referencia() -> None:
    no = _modelo(
        "fct_p", "models/marts/core/x.yml", {},
        config={"materialized": "external", "options": {"partition_by": "mes_referencia"}},
    )  # fmt: skip
    tabela = gerador.Tabela("gold-fct", "ref:fct_p", "fct_p", no, "model", "model.rfb.fct_p")
    assert (
        gerador._localizacao(tabela)[1]
        == "`gold/fct_p/mes_referencia=AAAA-MM/` (relativo a `RAIZ_DADOS`)"
    )


def test_saida_nao_depende_da_ordem_do_manifesto() -> None:
    """RDIC-07: o *partial parse* reordena `nodes`; a saída tem de ser a mesma."""
    esperado = gerador.gerar(_manifesto())
    for semente in range(5):
        manifesto = _manifesto()
        itens = list(manifesto["nodes"].items())
        random.Random(semente).shuffle(itens)
        manifesto["nodes"] = dict(itens)
        assert gerador.gerar(manifesto) == esperado
