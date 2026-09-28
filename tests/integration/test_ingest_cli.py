"""Testes de integração do `rfb ingest`: fluxo completo sobre fixtures e caminhos de erro.

As asserções de fluxo feliz leem `DATA_ROOT` do ambiente — exportado por `make ci`, que já
gerou fixtures e rodou `rfb ingest --origem-local` antes de chamar o dbt e o pytest. Sem
`DATA_ROOT`, o módulo inteiro é pulado (os caminhos de erro também dependem do gerador de
fixtures, então mantemos a mesma trava).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from rfb_pipeline import cli
from rfb_pipeline.errors import TaxaRejeitoExcedidaError
from rfb_pipeline.schemas import ENTIDADES_RFB, TABELAS_BD

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import gen_fixtures  # noqa: E402

pytestmark = pytest.mark.skipif(
    "DATA_ROOT" not in os.environ, reason="rode via make ci (exporta DATA_ROOT)"
)


def _data_root() -> Path:
    return Path(os.environ["DATA_ROOT"])


def _mes_ingerido() -> str:
    manifests_dir = _data_root() / "_manifests"
    nomes = sorted(p.stem for p in manifests_dir.glob("*.json"))
    assert nomes, "nenhum manifesto encontrado em _manifests/; rode `rfb ingest` antes"
    return nomes[-1]


class TestFluxoCompleto:
    def test_datasets_das_9_entidades_rfb_foram_criados(self) -> None:
        mes = _mes_ingerido()
        for entidade in ENTIDADES_RFB:
            particao = _data_root() / "raw" / "rfb" / entidade / f"mes_referencia={mes}"
            assert particao.is_dir(), f"partição ausente: {particao}"
            assert list(particao.glob("*.parquet")), f"nenhum parquet em {particao}"

    def test_datasets_das_4_tabelas_bd_foram_criados(self) -> None:
        for tabela in TABELAS_BD:
            parquet = _data_root() / "raw" / "bd" / tabela / f"{tabela}.parquet"
            assert parquet.is_file(), f"parquet ausente: {parquet}"

    def test_manifesto_presente_com_contagens_do_cenario_de_fixtures(self) -> None:
        mes = _mes_ingerido()
        manifesto_path = _data_root() / "_manifests" / f"{mes}.json"
        assert manifesto_path.is_file()
        dados = json.loads(manifesto_path.read_text(encoding="utf-8"))
        assert dados["entidades"]["empresas"]["linhas"] == 14
        assert dados["entidades"]["estabelecimentos"] == {"linhas": 15, "rejeitadas": 0}
        for campo in ("mes_referencia", "data_referencia", "iniciado_em", "concluido_em"):
            assert dados.get(campo)


class TestCaminhosDeErro:
    def test_mes_inexistente_sai_com_codigo_1_e_lista_disponiveis(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        origem_local = tmp_path / "fixtures"
        gen_fixtures.gerar_fixtures(origem_local)
        monkeypatch.setenv("DATA_ROOT", str(tmp_path / "data"))

        codigo = cli.main(["ingest", "--mes", "2099-01", "--origem-local", str(origem_local)])

        assert codigo == 1
        erro = capsys.readouterr().err
        assert "2099-01" in erro
        assert gen_fixtures.MES_REFERENCIA in erro

    def test_taxa_de_rejeito_excedida_sai_com_codigo_1(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        origem_local = tmp_path / "fixtures"
        gen_fixtures.gerar_fixtures(origem_local)
        monkeypatch.setenv("DATA_ROOT", str(tmp_path / "data"))

        def _sempre_excede(*_args: object, **_kwargs: object) -> None:
            raise TaxaRejeitoExcedidaError("empresas", 0.5, 0.0001, "raw/_rejeitos/empresas")

        monkeypatch.setattr(cli, "converter_entidade_rfb", _sempre_excede)

        codigo = cli.main(
            ["ingest", "--mes", gen_fixtures.MES_REFERENCIA, "--origem-local", str(origem_local)]
        )

        assert codigo == 1
        assert "taxa de rejeito" in capsys.readouterr().err
