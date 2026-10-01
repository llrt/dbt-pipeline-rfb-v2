"""`rfb relatorio` contra as fixtures (CASE-01): relatório afirma 1 concorrente ativo e 4 inativos.

Roda sobre o `warehouse.duckdb` e o `gold/` de `RAIZ_DADOS` (exportados por `make ci`).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from rfb_pipeline.cli import main

pytestmark = pytest.mark.skipif(
    "RAIZ_DADOS" not in os.environ, reason="rode via make ci (exporta RAIZ_DADOS)"
)


def _gerar(destino: Path) -> str:
    assert main(["relatorio", "--saida", str(destino), "--target", "ci"]) == 0
    return destino.read_text(encoding="utf-8")


def test_relatorio_do_estudo_de_caso_nas_fixtures(tmp_path: Path) -> None:
    texto = _gerar(tmp_path / "relatorio.md")
    assert "Em Fundão/ES há **1** concorrente ativo e **4** inativos no CNAE 4741500." in texto
    assert "| 3 anos | 5 | 4 | 80,0% |" in texto
    assert "FABRICA DE TINTAS SERRA SA | Serra | ES | 2071100 | principal | 18,66 |" in texto
    assert "MERCADO LINHARES | Linhares | ES | 4679699 | secundario | 73,68 |" in texto
    assert "o notebook 4 original retornava 0 nas buscas por microrregião" in texto
    assert "## Qualidade dos dados (última execução dbt)" in texto
    # incremento: enriquecimento_bd — área de mercado de Fundão (vizinhos: Aracruz e Serra)
    assert "## Área de mercado (enriquecimento com a Base dos Dados)" in texto
    assert "| 2 vizinhos | 1 | 0 |" in texto
    assert "| Região metropolitana (RM Grande Vitória) | 2 | 4 |" in texto
    assert "**0,1489** ativos por mil domicílios e **0,003484** por km²" in texto


def test_relatorio_e_deterministico_exceto_a_linha_da_execucao(tmp_path: Path) -> None:
    def corpo(texto: str) -> list[str]:
        return [linha for linha in texto.splitlines() if not linha.startswith("> Execução dbt")]

    assert corpo(_gerar(tmp_path / "a.md")) == corpo(_gerar(tmp_path / "b.md"))


def test_secao_de_qualidade_lista_os_avisos_do_historico_real(tmp_path: Path) -> None:
    """RBP-08 (N17): os avisos da última execução do `make ci` aparecem no relatório."""
    from rfb_pipeline.relatorio import ler_qualidade

    warehouse = Path(os.environ["RAIZ_DADOS"]) / "warehouse.duckdb"
    qualidade = ler_qualidade(warehouse)
    assert qualidade is not None, "histórico de testes ausente; rode `make ci`"
    resumo, pendentes = qualidade
    avisos = {nome for nome, status, *_ in pendentes if status == "warn"}
    assert avisos, "o `make ci` tem avisos conhecidos (cnaes_sem_par_bd, cnpj_dv_valido…)"
    assert len(avisos) == resumo["avisos"]
    texto = _gerar(tmp_path / "relatorio.md")
    for nome in avisos:
        assert f"`{nome}` | warn" in texto
