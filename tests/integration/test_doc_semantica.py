"""RSEM-10: a parte estática de `scripts/verificar_doc_semantica.py` roda no `make ci`.

Confere `conceitos.md` e `referencia/camada-semantica.md` contra os manifestos do `dbt parse`:
todo identificador entre crases existe no projeto, e todo link e âncora resolve. Os exemplos `mf`
só rodam com `--executar-exemplos` (fora do CI); os números citados na doc são conferidos em
`test_camada_semantica.py::test_numeros_citados_na_doc_batem_com_as_fixtures`.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "scripts" / "verificar_doc_semantica.py"
TARGET = RAIZ / "transform" / "target"

pytestmark = pytest.mark.skipif(
    not (TARGET / "semantic_manifest.json").is_file() or not (TARGET / "manifest.json").is_file(),
    reason="rode via make ci (gera os manifestos do dbt)",
)


def test_doc_da_camada_semantica_sem_pendencias() -> None:
    especificacao = importlib.util.spec_from_file_location("verificar_doc_semantica", SCRIPT)
    script = importlib.util.module_from_spec(especificacao)
    especificacao.loader.exec_module(script)
    _, conferidos, pendencias = script.verificar_estatico()
    assert len(conferidos) > 200
    assert not pendencias, "\n".join(pendencias)
