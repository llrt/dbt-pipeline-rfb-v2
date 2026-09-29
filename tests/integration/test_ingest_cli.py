"""Testes de integração do `rfb ingest`: fluxo completo sobre fixtures e caminhos de erro.

As asserções de fluxo feliz leem `DATA_ROOT` do ambiente — exportado por `make ci`, que já
gerou fixtures e rodou `rfb ingest --origem-local` antes de chamar o dbt e o pytest. Sem
`DATA_ROOT`, o módulo inteiro é pulado (os caminhos de erro também dependem do gerador de
fixtures, então mantemos a mesma trava).
"""

from __future__ import annotations

import dataclasses
import fcntl
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

from rfb_pipeline import cli
from rfb_pipeline.erros import EntidadeVaziaError, TaxaRejeitoExcedidaError
from rfb_pipeline.esquemas import ENTIDADES_RFB, TABELAS_BD

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
            [
                "ingest",
                "--mes",
                gen_fixtures.MES_REFERENCIA,
                "--origem-local",
                str(origem_local),
                "--permitir-incompleto",
            ]
        )

        assert codigo == 1
        assert "taxa de rejeito" in capsys.readouterr().err


class TestRedeIndisponivel:
    def test_webdav_fora_do_ar_sai_com_codigo_1_sem_traceback_e_com_url(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        import httpx

        from rfb_pipeline import cliente_rfb

        def _fora_do_ar(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("[Errno 8] sem rede", request=request)

        original = httpx.Client

        def _cliente(*args: object, **kwargs: object) -> httpx.Client:
            kwargs["transport"] = httpx.MockTransport(_fora_do_ar)
            return original(*args, **kwargs)

        monkeypatch.setattr(cliente_rfb.httpx, "Client", _cliente)
        monkeypatch.setattr(cliente_rfb.time, "sleep", lambda _s: None)
        monkeypatch.setenv("DATA_ROOT", str(tmp_path / "data"))

        codigo = cli.main(["ingest"])

        assert codigo == 1
        erro = capsys.readouterr().err
        assert "arquivos.receitafederal.gov.br" in erro
        assert "Traceback" not in erro


def _fixtures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    origem_local = tmp_path / "fixtures"
    gen_fixtures.gerar_fixtures(origem_local)
    data = tmp_path / "data"
    monkeypatch.setenv("DATA_ROOT", str(data))
    return origem_local, data


def _args(origem_local: Path, *extra: str) -> list[str]:
    return [
        "ingest",
        "--mes",
        gen_fixtures.MES_REFERENCIA,
        "--origem-local",
        str(origem_local),
        *extra,
    ]


class TestExecucaoSegura:
    def test_mes_incompleto_falha_listando_faltantes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        origem_local, data = _fixtures(tmp_path, monkeypatch)

        codigo = cli.main(_args(origem_local))

        assert codigo == 1
        erro = capsys.readouterr().err
        assert "incompleto" in erro
        assert "Empresas1.zip" in erro
        assert "--permitir-incompleto" in erro
        assert not (data / "raw").exists()

    def test_permitir_incompleto_ingere(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        origem_local, data = _fixtures(tmp_path, monkeypatch)

        assert cli.main(_args(origem_local, "--permitir-incompleto")) == 0
        assert (data / "_manifests" / f"{gen_fixtures.MES_REFERENCIA}.json").is_file()
        assert "faltam" in capsys.readouterr().err

    def test_segunda_execucao_simultanea_sai_1_e_nao_limpa_residuos(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        origem_local, data = _fixtures(tmp_path, monkeypatch)
        residuo = data / "raw" / "rfb" / "empresas" / ".tmp-em-uso"
        residuo.mkdir(parents=True)
        (data / "_estado").mkdir()

        with (data / "_estado" / "rfb.lock").open("a+") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            codigo = cli.main(_args(origem_local, "--permitir-incompleto"))

        assert codigo == 1
        assert "execução em andamento" in capsys.readouterr().err
        assert residuo.is_dir()  # a limpeza só roda com o lock

    def test_lock_e_liberado_ao_terminar_e_residuos_sao_limpos(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        origem_local, data = _fixtures(tmp_path, monkeypatch)
        residuos = [
            data / "raw" / "rfb" / "empresas" / ".tmp-x",
            data / "raw" / "bd" / "municipio" / ".tmp-y",
            data / "raw" / "_rejeitos" / "empresas" / ".old-z",
            data / "_tmp" / "extract-empresas-1",
        ]
        for r in residuos:
            r.mkdir(parents=True)

        assert cli.main(_args(origem_local, "--permitir-incompleto")) == 0
        assert cli.main(_args(origem_local, "--permitir-incompleto")) == 0  # lock liberado
        assert not any(r.exists() for r in residuos)

    def test_manifesto_gravado_incrementalmente_por_entidade(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        origem_local, data = _fixtures(tmp_path, monkeypatch)
        original = cli.converter_entidade_rfb

        def _falha_na_terceira(zips, entidade, *args, **kwargs):
            if entidade.nome == "simples":
                raise TaxaRejeitoExcedidaError("simples", 0.5, 0.0001, "x")
            return original(zips, entidade, *args, **kwargs)

        monkeypatch.setattr(cli, "converter_entidade_rfb", _falha_na_terceira)

        assert cli.main(_args(origem_local, "--permitir-incompleto")) == 1

        manifesto = json.loads(
            (data / "_manifests" / f"{gen_fixtures.MES_REFERENCIA}.json").read_text("utf-8")
        )
        assert set(manifesto["entidades"]) == {"empresas", "estabelecimentos"}
        assert manifesto["concluido_em"] is None

        # a execução seguinte pula o que já estava convertido
        monkeypatch.setattr(cli, "converter_entidade_rfb", original)
        assert cli.main(_args(origem_local, "--permitir-incompleto")) == 0
        final = json.loads(
            (data / "_manifests" / f"{gen_fixtures.MES_REFERENCIA}.json").read_text("utf-8")
        )
        assert final["concluido_em"]
        assert len(final["entidades"]) == 9

    def test_data_referencia_nula_gera_aviso(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        origem_local, _ = _fixtures(tmp_path, monkeypatch)
        original = cli.converter_entidade_rfb

        def _sem_data(*args, **kwargs):
            return [dataclasses.replace(r, data_referencia=None) for r in original(*args, **kwargs)]

        monkeypatch.setattr(cli, "converter_entidade_rfb", _sem_data)

        assert cli.main(_args(origem_local, "--permitir-incompleto")) == 0
        erro = capsys.readouterr().err
        assert "_data_referencia ficou NULL" in erro
        assert "nenhuma data de referência" in erro


class TestLigacaoDoCli:
    def _parquets(self, data: Path) -> dict[Path, int]:
        return {p: p.stat().st_mtime_ns for p in (data / "raw" / "rfb").rglob("*.parquet")}

    def test_segunda_execucao_nao_reescreve_e_force_reescreve(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Ingestão AC 12 ligada ao CLI (R1-10; M4): o pulo não é só `precisa_reconverter`."""
        origem_local, data = _fixtures(tmp_path, monkeypatch)
        extra = ("--permitir-incompleto",)

        assert cli.main(_args(origem_local, *extra)) == 0
        primeiro = self._parquets(data)
        assert primeiro

        assert cli.main(_args(origem_local, *extra)) == 0
        assert self._parquets(data) == primeiro  # nada reescrito
        assert "pulada (sem mudanças)" in capsys.readouterr().out

        assert cli.main(_args(origem_local, *extra, "--force")) == 0
        depois = self._parquets(data)
        assert set(depois) == set(primeiro)
        assert all(depois[p] != primeiro[p] for p in primeiro)  # todos reescritos

    def test_manifesto_do_cli_tem_o_sha256_real_dos_zips(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Ingestão AC 14 (M20): sha256 do manifesto == hashlib do zip de origem."""
        origem_local, data = _fixtures(tmp_path, monkeypatch)
        assert cli.main(_args(origem_local, "--permitir-incompleto")) == 0

        manifesto = json.loads(
            (data / "_manifests" / f"{gen_fixtures.MES_REFERENCIA}.json").read_text("utf-8")
        )
        assert manifesto["arquivos"]
        for arquivo in manifesto["arquivos"]:
            zip_origem = origem_local / "rfb" / gen_fixtures.MES_REFERENCIA / arquivo["nome"]
            assert arquivo["sha256"] == hashlib.sha256(zip_origem.read_bytes()).hexdigest()
            assert arquivo["bytes"] == zip_origem.stat().st_size

    def test_entidade_vazia_sai_com_codigo_1_e_mensagem(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        origem_local, _ = _fixtures(tmp_path, monkeypatch)

        def _vazia(*_a: object, **_k: object) -> None:
            raise EntidadeVaziaError("estabelecimentos", ["Estabelecimentos3.zip"])

        monkeypatch.setattr(cli, "converter_entidade_rfb", _vazia)

        assert cli.main(_args(origem_local, "--permitir-incompleto")) == 1
        erro = capsys.readouterr().err
        assert "estabelecimentos" in erro
        assert "0 linhas" in erro
        assert "Estabelecimentos3.zip" in erro
