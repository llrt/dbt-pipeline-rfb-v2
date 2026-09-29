"""`_resolver_mes` do CLI: mais recente completo e mês incompleto (R1-03, R1-10)."""

from __future__ import annotations

from pathlib import Path

import pytest

from rfb_pipeline import cli
from rfb_pipeline.cliente_rfb import ArquivoRemoto
from rfb_pipeline.erros import MesIncompletoErro, MesInexistenteErro
from rfb_pipeline.esquemas import ARQUIVOS_ESPERADOS_MES, arquivos_faltantes

COMPLETO = list(ARQUIVOS_ESPERADOS_MES)
PARCIAL = ["Empresas0.zip", "Estabelecimentos0.zip", "Estabelecimentos1.zip"]


class ClienteFalso:
    """Substituto de `ClienteRFB`: `{mes: [nomes de arquivo]}`."""

    def __init__(self, meses: dict[str, list[str]]) -> None:
        self._meses = meses

    def listar_meses(self) -> list[str]:
        return sorted(self._meses)

    def listar_arquivos(self, mes: str) -> list[ArquivoRemoto]:
        return [ArquivoRemoto(n, 1) for n in self._meses[mes]]


def _origem_local(tmp_path: Path, meses: dict[str, list[str]]) -> Path:
    for mes, nomes in meses.items():
        pasta = tmp_path / "rfb" / mes
        pasta.mkdir(parents=True)
        for nome in nomes:
            (pasta / nome).write_bytes(b"")
    return tmp_path


def test_lista_esperada_tem_27_arquivos() -> None:
    assert len(ARQUIVOS_ESPERADOS_MES) == 27
    assert ARQUIVOS_ESPERADOS_MES[0] == "Empresas0.zip"
    assert "Empresas9.zip" in ARQUIVOS_ESPERADOS_MES
    assert "Estabelecimentos9.zip" in ARQUIVOS_ESPERADOS_MES
    assert not any(n.startswith("Socios") for n in ARQUIVOS_ESPERADOS_MES)


def test_arquivos_faltantes() -> None:
    assert arquivos_faltantes(COMPLETO) == []
    assert arquivos_faltantes(COMPLETO[:-1]) == ["Qualificacoes.zip"]
    assert len(arquivos_faltantes(PARCIAL)) == 27 - 3


@pytest.mark.parametrize("origem", ["remoto", "local"])
class TestModos:
    def _resolver(self, tmp_path: Path, origem: str, meses: dict, mes=None, **kw) -> str:
        if origem == "remoto":
            return cli._resolver_mes(mes, ClienteFalso(meses), None, **kw)
        return cli._resolver_mes(mes, None, _origem_local(tmp_path, meses), **kw)

    def test_sem_mes_escolhe_o_mais_recente_completo(self, tmp_path, origem) -> None:
        meses = {"2026-07": COMPLETO, "2026-08": COMPLETO, "2026-09": COMPLETO}
        assert self._resolver(tmp_path, origem, meses) == "2026-09"

    def test_sem_mes_ignora_incompleto_com_aviso(self, tmp_path, origem, capsys) -> None:
        meses = {"2026-08": COMPLETO, "2026-09": PARCIAL}
        assert self._resolver(tmp_path, origem, meses) == "2026-08"
        aviso = capsys.readouterr().err
        assert "2026-09" in aviso
        assert "incompletos" in aviso

    def test_sem_mes_nenhum_completo_falha_listando_faltantes(self, tmp_path, origem) -> None:
        with pytest.raises(MesIncompletoErro) as exc:
            self._resolver(tmp_path, origem, {"2026-09": PARCIAL})
        assert "Empresas1.zip" in str(exc.value)
        assert "Simples.zip" in str(exc.value)

    def test_mes_explicito_incompleto_falha(self, tmp_path, origem) -> None:
        with pytest.raises(MesIncompletoErro) as exc:
            self._resolver(tmp_path, origem, {"2026-09": PARCIAL}, mes="2026-09")
        assert exc.value.mes == "2026-09"
        assert "Estabelecimentos9.zip" in exc.value.faltantes

    def test_mes_explicito_incompleto_com_permitir(self, tmp_path, origem) -> None:
        meses = {"2026-09": PARCIAL}
        resolvido = self._resolver(tmp_path, origem, meses, mes="2026-09", permitir_incompleto=True)
        assert resolvido == "2026-09"

    def test_sem_mes_com_permitir_pega_o_mais_recente(self, tmp_path, origem) -> None:
        meses = {"2026-08": COMPLETO, "2026-09": PARCIAL}
        assert self._resolver(tmp_path, origem, meses, permitir_incompleto=True) == "2026-09"

    def test_mes_inexistente(self, tmp_path, origem) -> None:
        with pytest.raises(MesInexistenteErro):
            self._resolver(tmp_path, origem, {"2026-09": COMPLETO}, mes="2020-01")

    def test_sem_meses_disponiveis(self, tmp_path, origem) -> None:
        if origem == "local":
            (tmp_path / "rfb").mkdir()
        with pytest.raises(MesInexistenteErro):
            if origem == "remoto":
                cli._resolver_mes(None, ClienteFalso({}), None)
            else:
                cli._resolver_mes(None, None, tmp_path)
