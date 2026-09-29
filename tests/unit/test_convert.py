from __future__ import annotations

import gzip
import logging
import sys
import zipfile
from datetime import date, datetime
from pathlib import Path

import duckdb
import pytest

from rfb_pipeline.config import Config
from rfb_pipeline.convert import (
    EntidadeVaziaError,
    ResultadoConversao,
    TaxaRejeitoExcedidaError,
    ZipCorrompidoError,
    ZipInseguroError,
    converter_entidade_rfb,
    converter_tabela_bd,
    data_referencia_do_nome,
    extrair_zip_seguro,
)
from rfb_pipeline.errors import ErroIngestao
from rfb_pipeline.schemas import ENTIDADES_RFB, TABELAS_BD

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import gen_fixtures  # noqa: E402

MES = "2026-09"
INGERIDO_EM = datetime(2026, 9, 28, 10, 30, 0)


@pytest.fixture(scope="module")
def fixtures(tmp_path_factory: pytest.TempPathFactory) -> Path:
    saida = tmp_path_factory.mktemp("fixtures")
    gen_fixtures.gerar_fixtures(saida)
    return saida


@pytest.fixture
def config(tmp_path: Path) -> Config:
    raiz = tmp_path / "data"
    return Config(
        data_root=raiz, data_root_uri=str(raiz), duckdb_memory_limit="1GB", duckdb_threads=2
    )


def _zip(fixtures: Path, nome: str) -> Path:
    return fixtures / "rfb" / MES / nome


def _particao(config: Config, entidade: str) -> Path:
    return config.raw_dir / "rfb" / entidade / f"mes_referencia={MES}"


def _ler(parquet: Path | str) -> list[dict]:
    rel = duckdb.sql(f"SELECT * FROM read_parquet('{parquet}', hive_partitioning=false)")
    return [dict(zip(rel.columns, linha, strict=True)) for linha in rel.fetchall()]


def _schema(parquet: Path) -> dict[str, str]:
    rel = duckdb.sql(f"SELECT * FROM read_parquet('{parquet}', hive_partitioning=false)")
    return dict(zip(rel.columns, (str(t) for t in rel.types), strict=True))


def _converter(fixtures: Path, config: Config, entidade: str, zips: list[str]):
    return converter_entidade_rfb(
        [_zip(fixtures, z) for z in zips],
        ENTIDADES_RFB[entidade],
        MES,
        config,
        ingerido_em=INGERIDO_EM,
    )


def _zip_malformado(destino: Path, nome_zip: str, validas: int, invalidas: int) -> Path:
    """Zip no formato Empresas com `invalidas` linhas de colunas a menos/mais."""
    linhas = [f'"{i:08d}";"EMPRESA {i}";"2062";"49";"1000,00";"01";""' for i in range(validas)]
    linhas += [
        '"99999999";"QUEBRADA"' if i % 2 else '"1";"2";"3";"4";"5";"6";"7";"8"'
        for i in range(invalidas)
    ]
    destino.mkdir(parents=True, exist_ok=True)
    caminho = destino / nome_zip
    with zipfile.ZipFile(caminho, "w") as zf:
        zf.writestr("K3241.K03200Y0.D60912.EMPRECSV", ("\n".join(linhas) + "\n").encode("latin-1"))
    return caminho


# ------------------------------------------------------------------ fixtures


def test_empresas_e_estabelecimentos_contagens_da_spec(fixtures: Path, config: Config) -> None:
    empresas = _converter(fixtures, config, "empresas", ["Empresas0.zip"])
    estab = _converter(fixtures, config, "estabelecimentos", ["Estabelecimentos0.zip"])

    assert [(r.linhas, r.linhas_rejeitadas) for r in empresas] == [(14, 0)]
    assert [(r.linhas, r.linhas_rejeitadas) for r in estab] == [(15, 0)]
    assert len(_ler(empresas[0].parquet[0])) == 14
    assert len(_ler(estab[0].parquet[0])) == 15
    assert not (config.rejeitos_dir / "empresas").exists()


def test_resultado_e_caminho_publicado(fixtures: Path, config: Config) -> None:
    (resultado,) = _converter(fixtures, config, "empresas", ["Empresas0.zip"])

    esperado = _particao(config, "empresas") / "part-Empresas0.parquet"
    assert resultado == ResultadoConversao(
        entidade="empresas",
        arquivo_origem="Empresas0.zip",
        arquivo_interno="K3241.K03200Y0.D60912.EMPRECSV",
        linhas=14,
        linhas_rejeitadas=0,
        parquet=(esperado,),
        data_referencia=date(2026, 9, 12),
    )
    assert esperado.is_file()
    # Nenhum temporário ou CSV extraído sobra.
    assert sorted(p.name for p in (config.raw_dir / "rfb" / "empresas").iterdir()) == [
        f"mes_referencia={MES}"
    ]
    assert not any((config.data_root / "_tmp").glob("extract-*"))


def test_razao_social_terminada_em_barra_invertida(fixtures: Path, config: Config) -> None:
    (r,) = _converter(fixtures, config, "empresas", ["Empresas0.zip"])
    linhas = {x["cnpj_raiz"]: x for x in _ler(r.parquet[0])}

    assert linhas["13131313"]["razao_social"] == "EMPRESA EXTERIOR LTDA\\"


def test_campo_multilinha_e_um_unico_registro(fixtures: Path, config: Config) -> None:
    (r,) = _converter(fixtures, config, "estabelecimentos", ["Estabelecimentos0.zip"])
    linhas = [
        x for x in _ler(r.parquet[0]) if (x["cnpj_raiz"], x["cnpj_ordem"]) == ("11111111", "0002")
    ]

    assert len(linhas) == 1
    assert linhas[0]["nome_fantasia"] == "TINTAS FUNDAO\nFILIAL SERRA"


def test_colunas_tecnicas_e_cnae_texto(fixtures: Path, config: Config) -> None:
    (r,) = _converter(fixtures, config, "estabelecimentos", ["Estabelecimentos0.zip"])
    linhas = _ler(r.parquet[0])

    assert {x["_data_referencia"] for x in linhas} == {date(2026, 9, 12)}
    assert {x["_mes_referencia"] for x in linhas} == {MES}
    assert {x["_arquivo_origem"] for x in linhas} == {"Estabelecimentos0.zip"}
    assert {x["_ingerido_em"] for x in linhas} == {INGERIDO_EM}
    assert "0111301" in {x["cnae_principal"] for x in linhas}


def test_cnae_dominio_preserva_zero_a_esquerda(fixtures: Path, config: Config) -> None:
    (r,) = _converter(fixtures, config, "cnaes", ["Cnaes.zip"])

    assert "0111301" in {x["codigo"] for x in _ler(r.parquet[0])}
    assert r.data_referencia == date(2026, 9, 12)


def test_simples_data_referencia_formato_simples(fixtures: Path, config: Config) -> None:
    (r,) = _converter(fixtures, config, "simples", ["Simples.zip"])

    assert r.arquivo_interno == "F.K03200$W.SIMPLES.CSV.D60912"
    assert {x["_data_referencia"] for x in _ler(r.parquet[0])} == {date(2026, 9, 12)}


def test_schema_parquet_rfb(fixtures: Path, config: Config) -> None:
    (r,) = _converter(fixtures, config, "estabelecimentos", ["Estabelecimentos0.zip"])
    entidade = ENTIDADES_RFB["estabelecimentos"]

    assert _schema(r.parquet[0]) == {
        **dict.fromkeys(entidade.colunas, "VARCHAR"),
        "_arquivo_origem": "VARCHAR",
        "_mes_referencia": "VARCHAR",
        "_data_referencia": "DATE",
        "_ingerido_em": "TIMESTAMP",
    }
    metadados = duckdb.sql(
        f"SELECT DISTINCT compression FROM parquet_metadata('{r.parquet[0]}')"
    ).fetchall()
    assert metadados == [("ZSTD",)]


def test_varios_zips_da_entidade_um_parquet_cada(
    fixtures: Path, config: Config, tmp_path: Path
) -> None:
    origem = tmp_path / "origem"
    origem.mkdir()
    for n in (0, 1):
        (origem / f"Empresas{n}.zip").write_bytes(_zip(fixtures, "Empresas0.zip").read_bytes())

    resultados = converter_entidade_rfb(
        [origem / "Empresas1.zip", origem / "Empresas0.zip"],
        ENTIDADES_RFB["empresas"],
        MES,
        config,
        ingerido_em=INGERIDO_EM,
    )

    assert [r.arquivo_origem for r in resultados] == ["Empresas0.zip", "Empresas1.zip"]
    assert sorted(p.name for p in _particao(config, "empresas").iterdir()) == [
        "part-Empresas0.parquet",
        "part-Empresas1.parquet",
    ]
    glob = config.raw_dir / "rfb" / "empresas" / "*" / "*.parquet"
    total = duckdb.sql(
        f"SELECT count(*), count(DISTINCT mes_referencia) "
        f"FROM read_parquet('{glob}', hive_partitioning=true)"
    ).fetchone()
    assert total == (28, 1)


def test_reconversao_substitui_particao(fixtures: Path, config: Config) -> None:
    _converter(fixtures, config, "empresas", ["Empresas0.zip"])
    lixo = _particao(config, "empresas") / "part-Antigo.parquet"
    lixo.write_bytes(b"x")

    _converter(fixtures, config, "empresas", ["Empresas0.zip"])

    assert [p.name for p in _particao(config, "empresas").iterdir()] == ["part-Empresas0.parquet"]


# --------------------------------------------------------------- data_referencia


@pytest.mark.parametrize(
    ("nome", "mes", "esperado"),
    [
        ("K3241.K03200Y0.D60912.ESTABELE", "2026-09", date(2026, 9, 12)),
        ("F.K03200$W.SIMPLES.CSV.D60912", "2026-09", date(2026, 9, 12)),
        ("F.K03200$Z.D60912.CNAECSV", "2026-09", date(2026, 9, 12)),
        # Dígito do ano diferente do ano de referência: ano mais recente <= 2026 terminado em 5/9.
        ("K3241.K03200Y0.D51220.EMPRECSV", "2026-01", date(2025, 12, 20)),
        ("K3241.K03200Y0.D91220.EMPRECSV", "2026-01", date(2019, 12, 20)),
        ("K3241.K03200Y0.D00105.EMPRECSV", "2030-01", date(2030, 1, 5)),
        ("K3241.K03200Y0.EMPRECSV", "2026-09", None),
        ("K3241.K03200Y0.D61399.EMPRECSV", "2026-09", None),
    ],
)
def test_data_referencia_do_nome(nome: str, mes: str, esperado: date | None) -> None:
    assert data_referencia_do_nome(nome, mes) == esperado


# ------------------------------------------------------------- limiar de rejeito


def test_limiar_excedido_grava_rejeitos_e_nao_publica(config: Config, tmp_path: Path) -> None:
    zip_ruim = _zip_malformado(tmp_path / "origem", "Empresas0.zip", validas=10, invalidas=2)

    with pytest.raises(TaxaRejeitoExcedidaError) as exc:
        converter_entidade_rfb(
            [zip_ruim], ENTIDADES_RFB["empresas"], MES, config, ingerido_em=INGERIDO_EM
        )

    rejeitos = config.rejeitos_dir / "empresas" / f"mes_referencia={MES}" / "rejeitos.parquet"
    assert exc.value.entidade == "empresas"
    assert exc.value.taxa == pytest.approx(2 / 12)
    assert exc.value.limiar == config.max_taxa_rejeito
    assert exc.value.caminho_rejeitos == str(rejeitos)
    linhas_rej = _ler(rejeitos)
    assert {x["arquivo_origem"] for x in linhas_rej} == {"Empresas0.zip"}
    assert len({x["linha"] for x in linhas_rej}) == 2
    assert not _particao(config, "empresas").exists()
    assert list((config.raw_dir / "rfb" / "empresas").iterdir()) == []


def test_rejeitos_abaixo_do_limiar_publica(config: Config, tmp_path: Path) -> None:
    zip_ruim = _zip_malformado(tmp_path / "origem", "Empresas0.zip", validas=10, invalidas=1)
    cfg = Config(
        data_root=config.data_root, data_root_uri=config.data_root_uri, max_taxa_rejeito=0.5
    )

    (r,) = converter_entidade_rfb(
        [zip_ruim], ENTIDADES_RFB["empresas"], MES, cfg, ingerido_em=INGERIDO_EM
    )

    assert (r.linhas, r.linhas_rejeitadas) == (10, 1)
    assert (cfg.rejeitos_dir / "empresas" / f"mes_referencia={MES}" / "rejeitos.parquet").is_file()


def test_rejeitos_contados_por_arquivo_sem_acumular(config: Config, tmp_path: Path) -> None:
    origem = tmp_path / "origem"
    zips = [
        _zip_malformado(origem, "Empresas0.zip", validas=10, invalidas=1),
        _zip_malformado(origem, "Empresas1.zip", validas=5, invalidas=2),
        _zip_malformado(origem, "Empresas2.zip", validas=3, invalidas=0),
    ]
    cfg = Config(
        data_root=config.data_root, data_root_uri=config.data_root_uri, max_taxa_rejeito=0.5
    )

    resultados = converter_entidade_rfb(
        zips, ENTIDADES_RFB["empresas"], MES, cfg, ingerido_em=INGERIDO_EM
    )

    assert [(r.linhas, r.linhas_rejeitadas) for r in resultados] == [(10, 1), (5, 2), (3, 0)]
    rejeitos = _ler(cfg.rejeitos_dir / "empresas" / f"mes_referencia={MES}" / "rejeitos.parquet")
    assert sorted({(x["arquivo_origem"], x["linha"]) for x in rejeitos}) == [
        ("Empresas0.zip", 11),
        ("Empresas1.zip", 6),
        ("Empresas1.zip", 7),
    ]


def test_falha_preserva_particao_anterior(fixtures: Path, config: Config, tmp_path: Path) -> None:
    (anterior,) = _converter(fixtures, config, "empresas", ["Empresas0.zip"])
    conteudo = anterior.parquet[0].read_bytes()
    zip_ruim = _zip_malformado(tmp_path / "origem", "Empresas0.zip", validas=1, invalidas=5)

    with pytest.raises(TaxaRejeitoExcedidaError):
        converter_entidade_rfb(
            [zip_ruim], ENTIDADES_RFB["empresas"], MES, config, ingerido_em=INGERIDO_EM
        )

    assert [p.name for p in _particao(config, "empresas").iterdir()] == ["part-Empresas0.parquet"]
    assert anterior.parquet[0].read_bytes() == conteudo
    assert sorted(p.name for p in (config.raw_dir / "rfb" / "empresas").iterdir()) == [
        f"mes_referencia={MES}"
    ]


def test_falha_no_segundo_zip_nao_publica_nada(
    fixtures: Path, config: Config, tmp_path: Path
) -> None:
    corrompido = tmp_path / "Empresas1.zip"
    corrompido.write_bytes(b"isto nao e um zip")

    with pytest.raises(ZipCorrompidoError):
        converter_entidade_rfb(
            [_zip(fixtures, "Empresas0.zip"), corrompido],
            ENTIDADES_RFB["empresas"],
            MES,
            config,
            ingerido_em=INGERIDO_EM,
        )

    assert list((config.raw_dir / "rfb" / "empresas").iterdir()) == []
    assert not any((config.data_root / "_tmp").glob("extract-*"))


# ------------------------------------------------------------------ contagem > 0


def _zip_vazio(destino: Path, nome_zip: str, nome_interno: str) -> Path:
    destino.mkdir(parents=True, exist_ok=True)
    caminho = destino / nome_zip
    with zipfile.ZipFile(caminho, "w") as zf:
        zf.writestr(nome_interno, b"")
    return caminho


def test_entidade_com_zero_linhas_nao_e_publicada(
    fixtures: Path, config: Config, tmp_path: Path
) -> None:
    (anterior,) = _converter(fixtures, config, "estabelecimentos", ["Estabelecimentos0.zip"])
    conteudo = anterior.parquet[0].read_bytes()
    vazio = _zip_vazio(
        tmp_path / "origem", "Estabelecimentos0.zip", "K3241.K03200Y0.D60912.ESTABELE"
    )

    with pytest.raises(EntidadeVaziaError) as exc:
        converter_entidade_rfb(
            [vazio], ENTIDADES_RFB["estabelecimentos"], MES, config, ingerido_em=INGERIDO_EM
        )

    assert exc.value.entidade == "estabelecimentos"
    assert exc.value.arquivos == ["Estabelecimentos0.zip"]
    assert isinstance(exc.value, ErroIngestao)
    assert [p.name for p in _particao(config, "estabelecimentos").iterdir()] == [
        "part-Estabelecimentos0.parquet"
    ]
    assert anterior.parquet[0].read_bytes() == conteudo
    assert sorted(p.name for p in (config.raw_dir / "rfb" / "estabelecimentos").iterdir()) == [
        f"mes_referencia={MES}"
    ]
    assert not any((config.data_root / "_tmp").glob("extract-*"))


def test_dominio_pequeno_vazio_nao_e_publicado(config: Config, tmp_path: Path) -> None:
    vazio = _zip_vazio(tmp_path / "origem", "Cnaes.zip", "F.K03200$Z.D60912.CNAECSV")

    with pytest.raises(EntidadeVaziaError) as exc:
        converter_entidade_rfb(
            [vazio], ENTIDADES_RFB["cnaes"], MES, config, ingerido_em=INGERIDO_EM
        )

    assert exc.value.entidade == "cnaes"
    assert list((config.raw_dir / "rfb" / "cnaes").iterdir()) == []


def test_arquivo_vazio_entre_nao_vazios_gera_aviso_e_publica(
    fixtures: Path, config: Config, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    origem = tmp_path / "origem"
    origem.mkdir()
    (origem / "Empresas0.zip").write_bytes(_zip(fixtures, "Empresas0.zip").read_bytes())
    vazio = _zip_vazio(origem, "Empresas1.zip", "K3241.K03200Y1.D60912.EMPRECSV")

    with caplog.at_level(logging.WARNING, logger="rfb_pipeline.convert"):
        resultados = converter_entidade_rfb(
            [origem / "Empresas0.zip", vazio],
            ENTIDADES_RFB["empresas"],
            MES,
            config,
            ingerido_em=INGERIDO_EM,
        )

    assert [(r.arquivo_origem, r.linhas) for r in resultados] == [
        ("Empresas0.zip", 14),
        ("Empresas1.zip", 0),
    ]
    assert all(r.parquet[0].is_file() for r in resultados)
    avisos = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(avisos) == 1
    assert "Empresas1.zip" in avisos[0].getMessage()
    assert "0 linhas" in avisos[0].getMessage()


def test_bd_sem_linhas_nao_e_publicada(fixtures: Path, config: Config, tmp_path: Path) -> None:
    csv_gz = tmp_path / "municipio.csv.gz"
    csv_gz.write_bytes(gzip.compress(b"id_municipio,id_municipio_rf,nome\n"))
    anterior = converter_tabela_bd(
        fixtures / "bd" / "municipio.csv.gz",
        TABELAS_BD["municipio"],
        config,
        ingerido_em=INGERIDO_EM,
    )
    conteudo = anterior.parquet[0].read_bytes()

    with pytest.raises(EntidadeVaziaError) as exc:
        converter_tabela_bd(csv_gz, TABELAS_BD["municipio"], config, ingerido_em=INGERIDO_EM)

    assert (exc.value.entidade, exc.value.arquivos) == ("municipio", ["municipio.csv.gz"])
    assert anterior.parquet[0].read_bytes() == conteudo
    assert sorted(p.name for p in (config.raw_dir / "bd").iterdir()) == ["municipio"]


# ------------------------------------------------------------------------ zips


def _zip_com_entrada(caminho: Path, nome_entrada: str) -> Path:
    with zipfile.ZipFile(caminho, "w") as zf:
        zf.writestr("ok.csv", b'"a";"b"\n')
        zf.writestr(nome_entrada, b"malicioso")
    return caminho


@pytest.mark.parametrize(
    "entrada", ["../evil.csv", "sub/../../evil.csv", "/tmp/evil-rfb-b3.csv", "..\\evil.csv"]
)
def test_zip_slip_recusado_sem_escrever(tmp_path: Path, entrada: str) -> None:
    zip_path = _zip_com_entrada(tmp_path / "mal.zip", entrada)
    destino = tmp_path / "destino" / "extracao"

    with pytest.raises(ZipInseguroError) as exc:
        extrair_zip_seguro(zip_path, destino)

    assert exc.value.entrada == entrada
    assert list(destino.iterdir()) == []  # nem a entrada legítima é extraída
    assert not (tmp_path / "destino" / "evil.csv").exists()
    assert not Path("/tmp/evil-rfb-b3.csv").exists()


def test_zip_slip_via_conversao_nao_escreve_em_raw(config: Config, tmp_path: Path) -> None:
    zip_path = _zip_com_entrada(tmp_path / "Empresas0.zip", "../evil.csv")

    with pytest.raises(ZipInseguroError):
        converter_entidade_rfb(
            [zip_path], ENTIDADES_RFB["empresas"], MES, config, ingerido_em=INGERIDO_EM
        )

    assert list((config.raw_dir / "rfb" / "empresas").iterdir()) == []
    assert not (config.data_root / "_tmp" / "evil.csv").exists()


def test_extracao_normal(fixtures: Path, tmp_path: Path) -> None:
    extraidos = extrair_zip_seguro(_zip(fixtures, "Cnaes.zip"), tmp_path / "x")

    assert [p.name for p in extraidos] == ["F.K03200$Z.D60912.CNAECSV"]
    assert extraidos[0].read_bytes().startswith(b'"')


def test_zip_ilegivel(config: Config, tmp_path: Path) -> None:
    ruim = tmp_path / "Empresas0.zip"
    ruim.write_bytes(b"PK\x03\x04 truncado")

    with pytest.raises(ZipCorrompidoError):
        converter_entidade_rfb(
            [ruim], ENTIDADES_RFB["empresas"], MES, config, ingerido_em=INGERIDO_EM
        )

    assert list((config.raw_dir / "rfb" / "empresas").iterdir()) == []


def test_zip_com_crc_invalido(fixtures: Path, config: Config, tmp_path: Path) -> None:
    ruim = tmp_path / "Empresas0.zip"
    with zipfile.ZipFile(ruim, "w", compression=zipfile.ZIP_STORED) as zf:
        zf.writestr("K3241.K03200Y0.D60912.EMPRECSV", b'"1";"2";"3";"4";"5";"6";"7"\n' * 50)
    dados = bytearray(ruim.read_bytes())
    dados[100] ^= 0xFF  # corrompe o conteúdo sem tocar nos cabeçalhos
    ruim.write_bytes(bytes(dados))

    with pytest.raises(ZipCorrompidoError):
        converter_entidade_rfb(
            [ruim], ENTIDADES_RFB["empresas"], MES, config, ingerido_em=INGERIDO_EM
        )

    assert list((config.raw_dir / "rfb" / "empresas").iterdir()) == []
    assert not any((config.data_root / "_tmp").glob("extract-*"))


# -------------------------------------------------------------------------- BD


def test_bd_cnae2_multilinha_e_subclasse_texto(fixtures: Path, config: Config) -> None:
    r = converter_tabela_bd(
        fixtures / "bd" / "cnae_2.csv.gz", TABELAS_BD["cnae_2"], config, ingerido_em=INGERIDO_EM
    )

    destino = config.raw_dir / "bd" / "cnae_2" / "cnae_2.parquet"
    assert r.parquet == (destino,)
    assert (r.entidade, r.arquivo_origem, r.arquivo_interno) == ("cnae_2", "cnae_2.csv.gz", None)
    linhas = _ler(destino)
    assert r.linhas == len(linhas) == len(gen_fixtures._CNAE2_BD)
    assert "0111301" in {x["subclasse"] for x in linhas}
    assert any("\n" in v for x in linhas for v in x.values() if isinstance(v, str))
    assert _schema(destino) == {
        **dict.fromkeys(gen_fixtures.HEADER_CNAE2_BD, "VARCHAR"),
        "_arquivo_origem": "VARCHAR",
        "_ingerido_em": "TIMESTAMP",
    }
    assert sorted(p.name for p in (config.raw_dir / "bd").iterdir()) == ["cnae_2"]


def test_bd_reconversao_substitui(fixtures: Path, config: Config) -> None:
    for _ in range(2):
        r = converter_tabela_bd(
            fixtures / "bd" / "municipio.csv.gz",
            TABELAS_BD["municipio"],
            config,
            ingerido_em=INGERIDO_EM,
        )
    assert r.linhas == 8
    assert sorted(p.name for p in (config.raw_dir / "bd").iterdir()) == ["municipio"]
