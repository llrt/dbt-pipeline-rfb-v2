"""Ingestão das fontes do IBGE (`rfb_pipeline.ibge`), sem rede: SIDRA e geoftp simulados.

incremento: enriquecimento_ibge
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import httpx
import openpyxl
import pytest

from rfb_pipeline.configuracao import Configuracao
from rfb_pipeline.erros import (
    HostNaoPermitidoErro,
    PlanilhaIBGEErro,
    SidraErro,
    SidraLimiteExcedidoErro,
)
from rfb_pipeline.esquemas import TABELAS_IBGE
from rfb_pipeline.ibge import (
    CATEGORIA_TOTAL_CEMPRE,
    MUNICIPIOS_ESTIMADOS,
    ConsultaSidra,
    consultar_sidra,
    fatiar_categorias,
    ingerir_ibge,
    ler_aba_xlsx,
    ler_manifesto_ibge,
    normalizar_coluna,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import gerar_fixtures  # noqa: E402

INGERIDO_EM = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)
HOSTS = ("apisidra.ibge.gov.br", "geoftp.ibge.gov.br")


def _configuracao(raiz: Path) -> Configuracao:
    return Configuracao(raiz_dados=raiz, raiz_dados_uri=str(raiz), tentativas=2)


def _raw(raiz: Path, tabela: str) -> list[tuple]:
    caminho = raiz / "raw" / "ibge" / tabela / f"{tabela}.parquet"
    return duckdb.sql(f"select * exclude (_ingerido_em) from '{caminho}'").fetchall()


# --------------------------------------------------------------------------- fatiamento


def test_fatiamento_do_cempre_fica_no_limite_de_50000_valores() -> None:
    categorias = [str(i) for i in range(674)]  # 673 classes + Total
    modelo = ConsultaSidra("9528", "n6", ("706", "707", "708", "662"), "2024", (("12762", ("0",)),))
    por_categoria = modelo.valores_estimados(MUNICIPIOS_ESTIMADOS)
    fatias = fatiar_categorias(categorias, por_categoria, 50_000)

    assert [c for f in fatias for c in f] == categorias
    assert all(len(f) * por_categoria <= 50_000 for f in fatias)
    assert len(fatias) == 337  # 2 categorias por requisição: 2 × 5.600 × 4 = 44.800 valores
    with pytest.raises(ValueError, match="acima do limite"):
        fatiar_categorias(categorias, 50_001, 50_000)


def test_url_da_sidra_usa_codigos_sem_cabecalho() -> None:
    consulta = ConsultaSidra(
        "10295", "n6", ("13604", "13431"), "2022", (("2", ("6794",)), ("86", ("95251",)))
    )
    assert consulta.url("https://apisidra.ibge.gov.br/values") == (
        "https://apisidra.ibge.gov.br/values/t/10295/n6/all/v/13604,13431/p/2022"
        "/c2/6794/c86/95251/f/c/h/n"
    )
    ultimo = ConsultaSidra("9528", "n1", ("706",), "last 1", (("12762", ("all",)),), formato="a")
    assert "/p/last%201/c12762/all/f/a/h/n" in ultimo.url("https://apisidra.ibge.gov.br/values")


# ------------------------------------------------------------------------------- SIDRA


def _cliente(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_excedeu_o_limite_vira_erro_claro() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400, text="Quantidade de valores solicitados: 66840 excedeu o limite: 50000"
        )

    with pytest.raises(SidraLimiteExcedidoErro, match="excedeu o limite: 50000"):
        consultar_sidra(
            _cliente(handler),
            "https://apisidra.ibge.gov.br/values/t/9528",
            hosts_permitidos=HOSTS,
            tentativas=3,
            dormir=lambda _s: None,
        )


def test_resposta_vazia_ou_texto_vira_erro_e_5xx_tenta_de_novo() -> None:
    respostas = iter([httpx.Response(503), httpx.Response(200, json=[])])

    with pytest.raises(SidraErro, match="resposta vazia"):
        consultar_sidra(
            _cliente(lambda _r: next(respostas)),
            "https://apisidra.ibge.gov.br/values/t/1",
            hosts_permitidos=HOSTS,
            tentativas=3,
            dormir=lambda _s: None,
        )
    with pytest.raises(SidraErro, match="não é JSON"):
        consultar_sidra(
            _cliente(lambda _r: httpx.Response(200, text="Tabela inexistente")),
            "https://apisidra.ibge.gov.br/values/t/1",
            hosts_permitidos=HOSTS,
            tentativas=1,
        )


def test_allowlist_recusa_host_fora_da_lista() -> None:
    assert set(HOSTS) <= set(_configuracao(Path("/tmp/x")).hosts_permitidos)
    with pytest.raises(HostNaoPermitidoErro):
        consultar_sidra(
            _cliente(lambda _r: httpx.Response(200, json=[{"V": "1"}])),
            "https://servicodados.ibge.gov.br/api/v3/agregados",
            hosts_permitidos=HOSTS,
            tentativas=1,
        )


def test_parse_de_f_c_h_n_preserva_codigos_e_simbolos_como_texto(tmp_path: Path) -> None:
    """A resposta `/f/c/h/n` vai ao raw com as chaves em minúsculas e `V` como publicado."""
    gerar_fixtures.gerar_fixtures(tmp_path / "fx")
    raiz = tmp_path / "dados"
    ingerir_ibge(_configuracao(raiz), ingerido_em=INGERIDO_EM, origem_local=tmp_path / "fx")

    colunas = [
        c[0]
        for c in duckdb.sql(
            f"describe select * from '{raiz}/raw/ibge/cempre_municipio_cnae/*.parquet'"
        ).fetchall()
    ]
    assert colunas == [
        "nc",
        "mc",
        "v",
        "d1c",
        "d2c",
        "d3c",
        "d4c",
        "_arquivo_origem",
        "_ingerido_em",
    ]
    tipos = duckdb.sql(
        f"select distinct column_type from (describe select * exclude (_ingerido_em) "
        f"from '{raiz}/raw/ibge/cempre_municipio_cnae/*.parquet')"
    ).fetchall()
    assert tipos == [("VARCHAR",)]
    valores = {linha[2] for linha in _raw(raiz, "cempre_municipio_cnae")}
    assert {"-", "X", "..", "..."} <= valores
    renda = {(r[3], r[4]): r[2] for r in _raw(raiz, "renda_censo_2022_municipio")}
    assert renda[("3202207", "13534")] == "1040.00"  # texto, sem virar 1040.0
    assert renda[("3202207", "13431")] == "1406.78"


# ----------------------------------------------------------------- CEMPRE: retomada


_CATEGORIAS = [
    ("117897", "Total"),
    ("117452", "47.4 Comércio varejista de material de construção"),
    ("117065", "20.5 Fabricação de defensivos agrícolas e desinfestantes domissanitários"),
    ("117453", "47.41-5 Comércio varejista de tintas e materiais para pintura"),
    ("117456", "47.44-0 Comércio varejista de ferragens, madeira e materiais de construção"),
    ("117073", "20.71-1 Fabricação de tintas, vernizes, esmaltes e lacas"),
]


class _SidraFalsa:
    """SIDRA simulada: categorias (`/n1`), CEMPRE fatiado (`/n6`, 9528) e renda (10295)."""

    def __init__(self, falhar_na_fatia: int | None = None, periodo: str = "2024") -> None:
        self.falhar_na_fatia = falhar_na_fatia
        self.periodo = periodo
        self.fatias_pedidas: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if request.url.host == "geoftp.ibge.gov.br":
            return httpx.Response(404)
        partes = request.url.path.split("/")
        if "/n1/" in url:
            return httpx.Response(
                200,
                json=[
                    {
                        "NC": "1",
                        "NN": "Brasil",
                        "MC": "1020",
                        "MN": "Unidades",
                        "V": "10",
                        "D1C": "1",
                        "D1N": "Brasil",
                        "D2C": "706",
                        "D2N": "Número de unidades locais",
                        "D3C": self.periodo,
                        "D3N": self.periodo,
                        "D4C": c,
                        "D4N": n,
                    }  # fmt: skip
                    for c, n in _CATEGORIAS
                ],
            )
        if "/t/9528/" in url:
            categorias = partes[partes.index("c12762") + 1].split(",")
            self.fatias_pedidas.append(",".join(categorias))
            if self.falhar_na_fatia == len(self.fatias_pedidas):
                return httpx.Response(400, text="Erro simulado")
            return httpx.Response(
                200,
                json=[
                    {
                        "NC": "6",
                        "MC": "45",
                        "V": "X" if c == "117453" else "1",
                        "D1C": m,
                        "D2C": v,
                        "D3C": self.periodo,
                        "D4C": c,
                    }  # fmt: skip
                    for c in categorias
                    for m in ("3202207", "3205002")
                    for v in ("706", "707", "708", "662")
                ],
            )
        raise AssertionError(f"URL inesperada: {url}")


def _cempre(raiz: Path, sidra: _SidraFalsa, *, renovar: bool = False) -> None:
    from rfb_pipeline.ibge import _Ingestao

    ingestao = _Ingestao(
        _configuracao(raiz),
        origem_local=None,
        renovar=renovar,
        ingerido_em=INGERIDO_EM,
        http=_cliente(sidra),
        dormir=lambda _s: None,
    )
    periodo, categorias = ingestao.categorias_cempre()
    ingestao.cempre_municipio(periodo, categorias)


def test_cempre_baixa_so_classes_e_total_e_retoma_sem_refazer_fatias(tmp_path: Path) -> None:
    raiz = tmp_path / "dados"
    primeira = _SidraFalsa(falhar_na_fatia=2)
    with pytest.raises(SidraErro, match="Erro simulado"):
        _cempre(raiz, primeira)
    # 3 classes (`20.5` e `47.4` não são classes) + Total = 4 categorias -> 2 fatias de 2
    assert primeira.fatias_pedidas == ["117073,117453", "117456,117897"]
    assert not (raiz / "raw" / "ibge" / "cempre_municipio_cnae").exists()
    pasta = raiz / "_baixados" / "ibge" / "sidra" / "cempre_municipio_cnae" / "2024"
    assert len(list(pasta.glob("fatia-*.parquet"))) == 1

    segunda = _SidraFalsa()
    _cempre(raiz, segunda)
    assert segunda.fatias_pedidas == ["117456,117897"]  # a fatia 1 foi reaproveitada
    linhas = _raw(raiz, "cempre_municipio_cnae")
    assert len(linhas) == 4 * 2 * 4
    assert {linha[6] for linha in linhas} == {"117073", "117453", "117456", CATEGORIA_TOTAL_CEMPRE}
    assert not pasta.exists()  # fatias apagadas depois de publicar
    entrada = ler_manifesto_ibge(_configuracao(raiz))["cempre_municipio_cnae"]
    assert (entrada.periodo, entrada.requisicoes, entrada.linhas) == ("2024", 2, 32)


def test_cempre_do_mesmo_periodo_nao_rebaixa_salvo_renovar(tmp_path: Path) -> None:
    raiz = tmp_path / "dados"
    _cempre(raiz, _SidraFalsa())

    de_novo = _SidraFalsa()
    _cempre(raiz, de_novo)
    assert de_novo.fatias_pedidas == []

    ano_novo = _SidraFalsa(periodo="2025")
    _cempre(raiz, ano_novo)
    assert len(ano_novo.fatias_pedidas) == 2

    renovado = _SidraFalsa(periodo="2025")
    _cempre(raiz, renovado, renovar=True)
    assert len(renovado.fatias_pedidas) == 2


# --------------------------------------------------------------------------- planilhas


def _xlsx(caminho: Path, abas: dict[str, list[list]]) -> Path:
    livro = openpyxl.Workbook()
    livro.remove(livro.active)
    for nome, linhas in abas.items():
        aba = livro.create_sheet(nome)
        for linha in linhas:
            aba.append(linha)
    livro.save(caminho)
    return caminho


def test_leitura_de_xlsx_normaliza_cabecalho_e_texto_das_celulas(tmp_path: Path) -> None:
    caminho = _xlsx(
        tmp_path / "m.xlsx",
        {
            "Hierarquia e região": [
                [
                    "codmun",
                    "Múltiplas Subordinações",
                    "Região de influência - vínculação",
                    "Q1",
                    None,
                ],
                ["3202207", 1, "Vitória (ES)", 46.6666666666667, None],
                [3205002, 2.0, None, 45, None],
                [None, None, None, None, None],
            ],
            "Notas": [["x"]],
        },
    )
    colunas, cabecalho, linhas = ler_aba_xlsx(caminho, "Hierarquia e região")

    assert colunas == ["codmun", "multiplas_subordinacoes", "regiao_de_influencia_vinculacao", "q1"]
    assert cabecalho[1] == "Múltiplas Subordinações"
    assert list(linhas) == [
        ["3202207", "1", "Vitória (ES)", "46.6666666666667"],
        ["3205002", "2", None, "45"],
    ]
    assert normalizar_coluna("Hierarquia - grupo") == "hierarquia_grupo"


def test_xlsx_sem_aba_ou_com_coluna_repetida_falha(tmp_path: Path) -> None:
    caminho = _xlsx(tmp_path / "m.xlsx", {"A": [["Q1", "q1"], [1, 2]]})
    with pytest.raises(PlanilhaIBGEErro, match="aba 'B' ausente"):
        ler_aba_xlsx(caminho, "B")
    with pytest.raises(PlanilhaIBGEErro, match="repetidas"):
        ler_aba_xlsx(caminho, "A")


# ------------------------------------------------------------------- origem local


def test_origem_local_converte_tudo_e_pula_arquivos_iguais(tmp_path: Path, capsys) -> None:
    gerar_fixtures.gerar_fixtures(tmp_path / "fx")
    raiz = tmp_path / "dados"
    configuracao = _configuracao(raiz)

    entradas = ingerir_ibge(configuracao, ingerido_em=INGERIDO_EM, origem_local=tmp_path / "fx")
    assert sorted(e.tabela for e in entradas) == sorted(TABELAS_IBGE)
    assert all(e.sha256 and e.bytes > 0 and e.linhas > 0 for e in entradas)
    ligacoes = {(r[2], r[12]): (r[21], r[22]) for r in _raw(raiz, "regic_2018_ligacoes")}
    assert ligacoes[("3202207", "3205002")] == ("46.6666666666667", "45")
    assert ligacoes[("3202207", "3205309")] == ("30", "38.3333333333333")
    caminho_manifesto = raiz / "_manifestos" / "ibge" / "manifesto.json"
    manifesto = json.loads(caminho_manifesto.read_text(encoding="utf-8"))
    assert set(manifesto["tabelas"]) == set(TABELAS_IBGE)
    publicados = sorted(p.relative_to(raiz).as_posix() for p in (raiz / "raw").rglob("*"))
    assert publicados == ["raw/ibge"] + [
        caminho
        for t in sorted(TABELAS_IBGE)
        for caminho in (f"raw/ibge/{t}", f"raw/ibge/{t}/{t}.parquet")
    ]  # só o Parquet: JSON, CSV e xlsx extraído ficam fora do raw
    assert not list((raiz / "_tmp").glob("extracao-ibge-*"))

    capsys.readouterr()
    ingerir_ibge(configuracao, ingerido_em=INGERIDO_EM, origem_local=tmp_path / "fx")
    saida = capsys.readouterr().out
    assert saida.count("pulada (arquivo local sem mudanças)") == len(TABELAS_IBGE)


# incremento: enriquecimento_ibge — compatibilidade do modo offline (espelho sem `ibge/`, v1.3)
def test_origem_local_sem_ibge_avisa_e_publica_raw_vazio_com_o_esquema(
    tmp_path: Path, capsys
) -> None:
    origem = tmp_path / "espelho-v1.3"
    origem.mkdir()
    raiz = tmp_path / "dados"

    entradas = ingerir_ibge(_configuracao(raiz), ingerido_em=INGERIDO_EM, origem_local=origem)

    assert entradas == ()  # nada no manifesto: a próxima execução com os arquivos converte tudo
    saida = capsys.readouterr().out
    assert saida.count("AVISO") == len(TABELAS_IBGE)
    for nome, tabela in TABELAS_IBGE.items():
        caminho = raiz / "raw" / "ibge" / nome / f"{nome}.parquet"
        colunas = duckdb.sql(f"describe select * from '{caminho}'").fetchall()
        assert [c[0] for c in colunas] == [*tabela.colunas, "_arquivo_origem", "_ingerido_em"]
        assert {c[1] for c in colunas[:-1]} == {"VARCHAR"}
        assert colunas[-1][1] == "TIMESTAMP"
        assert _raw(raiz, nome) == []


def test_origem_local_sem_um_arquivo_mantem_o_raw_existente_e_converte_os_demais(
    tmp_path: Path, capsys
) -> None:
    gerar_fixtures.gerar_fixtures(tmp_path / "fx")
    raiz = tmp_path / "dados"
    configuracao = _configuracao(raiz)
    ingerir_ibge(configuracao, ingerido_em=INGERIDO_EM, origem_local=tmp_path / "fx")
    antes = _raw(raiz, "renda_censo_2022_municipio")
    (tmp_path / "fx" / "ibge" / "renda_censo_2022_municipio.json").unlink()
    (tmp_path / "fx" / "ibge" / "REGIC2018_Municipios_Hierarquia_e_regiao.xlsx").unlink()
    capsys.readouterr()

    entradas = ingerir_ibge(configuracao, ingerido_em=INGERIDO_EM, origem_local=tmp_path / "fx")

    saida = capsys.readouterr().out
    assert "ibge.renda_censo_2022_municipio: AVISO" in saida
    assert "mantido o raw existente" in saida
    assert saida.count("AVISO") == 2
    assert saida.count("pulada (arquivo local sem mudanças)") == len(TABELAS_IBGE) - 2
    assert _raw(raiz, "renda_censo_2022_municipio") == antes
    assert sorted(e.tabela for e in entradas) == sorted(TABELAS_IBGE)  # o manifesto anterior fica


def test_colunas_do_esquema_ibge_batem_com_a_fonte_dbt() -> None:
    import yaml

    fonte = Path(__file__).resolve().parents[2] / "transform/models/staging/ibge/_ibge__sources.yml"
    (ibge,) = yaml.safe_load(fonte.read_text(encoding="utf-8"))["sources"]
    declaradas = {
        t["name"]: tuple(c["name"] for c in t["columns"] if not c["name"].startswith("_"))
        for t in ibge["tables"]
    }
    assert declaradas == {nome: t.colunas for nome, t in TABELAS_IBGE.items()}
