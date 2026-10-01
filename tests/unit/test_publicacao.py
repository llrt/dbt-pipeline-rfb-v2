"""T42 (PUB-01): publicação do gold — SQL gerado, seleção, ausência de configuração, token."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from rfb_pipeline import cli, publicacao
from rfb_pipeline.configuracao import carregar_configuracao
from rfb_pipeline.erros import ErroIngestao
from rfb_pipeline.publicacao import Dataset, descobrir_datasets, gerar_sql_tabela, publicar

TOKEN = "tok-segredo-123"


def _montar_gold(gold: Path) -> None:
    gold.mkdir(parents=True)
    con = duckdb.connect()
    con.execute(
        f"COPY (SELECT 1 AS a UNION ALL SELECT 2) TO '{gold}/dim_x.parquet' (FORMAT parquet)"
    )
    con.execute(f"COPY (SELECT 7 AS b) TO '{gold}/dim_y.parquet' (FORMAT parquet)")
    for mes, n in (("2026-08", 3), ("2026-09", 5)):
        pasta = gold / "fct_serie" / f"mes_referencia={mes}"
        pasta.mkdir(parents=True)
        con.execute(
            f"COPY (SELECT range AS v FROM range({n})) TO '{pasta}/data_0.parquet' (FORMAT parquet)"
        )
    con.close()


@pytest.fixture
def gold(tmp_path: Path) -> Path:
    _montar_gold(tmp_path / "gold")
    return tmp_path / "gold"


def test_descobre_arquivos_e_diretorios_particionados(gold: Path) -> None:
    datasets = {d.nome: d for d in descobrir_datasets(gold)}
    assert set(datasets) == {"dim_x", "dim_y", "fct_serie"}
    assert not datasets["dim_x"].particionado
    assert datasets["fct_serie"].particionado
    assert datasets["fct_serie"].padrao.endswith("fct_serie/*/*.parquet")


def test_sql_gerado() -> None:
    simples = gerar_sql_tabela("rfb", Dataset("dim_x", "/g/dim_x.parquet", particionado=False))
    assert simples == (
        'CREATE OR REPLACE TABLE "rfb".main."dim_x" AS '
        "SELECT * FROM read_parquet('/g/dim_x.parquet')"
    )
    mensal = gerar_sql_tabela("rfb", Dataset("fct_serie", "/g/fct_serie/*/*.parquet", True))
    assert "hive_partitioning = true" in mensal


def test_nomes_invalidos_sao_recusados() -> None:
    with pytest.raises(ErroIngestao):
        gerar_sql_tabela("rfb; drop", Dataset("x", "/g/x.parquet", False))
    with pytest.raises(ErroIngestao):
        gerar_sql_tabela("rfb", Dataset('x"y', "/g/x.parquet", False))


def test_publica_todas_as_tabelas_com_contagens_e_particao(gold: Path, tmp_path: Path) -> None:
    destino = tmp_path / "destino.duckdb"
    publicadas = publicar(gold, str(destino), "rfb")
    assert {t.nome: t.linhas for t in publicadas} == {"dim_x": 2, "dim_y": 1, "fct_serie": 8}
    with duckdb.connect(str(destino), read_only=True) as con:
        meses = con.execute(
            "SELECT mes_referencia, count(*) FROM fct_serie GROUP BY 1 ORDER BY 1"
        ).fetchall()
    assert [(str(m), n) for m, n in meses] == [("2026-08", 3), ("2026-09", 5)]


def test_republicar_substitui_a_tabela(gold: Path, tmp_path: Path) -> None:
    destino = str(tmp_path / "destino.duckdb")
    publicar(gold, destino, "rfb")
    publicadas = publicar(gold, destino, "rfb", tabelas=["dim_x"])
    assert [(t.nome, t.linhas) for t in publicadas] == [("dim_x", 2)]


def test_selecao_de_tabelas(gold: Path, tmp_path: Path) -> None:
    destino = tmp_path / "d.duckdb"
    publicadas = publicar(gold, str(destino), "rfb", tabelas=["dim_y", "fct_serie"])
    assert sorted(t.nome for t in publicadas) == ["dim_y", "fct_serie"]
    with pytest.raises(ErroIngestao, match="inexistente"):
        publicar(gold, str(destino), "rfb", tabelas=["nao_existe"])


def test_sem_variaveis_nada_e_publicado_e_nao_conecta(
    gold: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def _nao_deve_conectar(*_a: object, **_k: object) -> None:
        raise AssertionError("não deveria conectar sem configuração")

    monkeypatch.setattr(publicacao.duckdb, "connect", _nao_deve_conectar)
    configuracao = carregar_configuracao({"RAIZ_DADOS": str(gold.parent)})
    ambientes = [
        {},
        {"MOTHERDUCK_TOKEN": TOKEN},
        {"MOTHERDUCK_BANCO": "rfb"},
        {"MOTHERDUCK_TOKEN": "", "MOTHERDUCK_BANCO": "rfb"},
    ]
    for env in ambientes:
        assert publicacao.publicar_motherduck(configuracao, env=env) is None
    assert "MotherDuck não configurado; nada publicado" in capsys.readouterr().out


def test_cli_sem_variaveis_sai_com_zero(
    gold: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("RAIZ_DADOS", str(gold.parent))
    monkeypatch.delenv("MOTHERDUCK_TOKEN", raising=False)
    monkeypatch.delenv("MOTHERDUCK_BANCO", raising=False)
    assert cli.main(["publicar", "--destino", "motherduck"]) == 0
    assert "nada publicado" in capsys.readouterr().out


def test_raiz_s3_e_recusada_quando_configurado(gold: Path) -> None:
    configuracao = carregar_configuracao(
        {
            "RAIZ_DADOS": "s3://bucket/p",
            "RAIZ_DADOS_LOCAL": str(gold.parent),
            "AWS_ACCESS_KEY_ID": "a",
            "AWS_SECRET_ACCESS_KEY": "b",
            "AWS_ENDPOINT_URL_S3": "https://x",
        }
    )
    env = {"MOTHERDUCK_TOKEN": TOKEN, "MOTHERDUCK_BANCO": "rfb"}
    with pytest.raises(ErroIngestao, match="s3://"):
        publicacao.publicar_motherduck(configuracao, env=env)


def test_token_nao_aparece_em_saida_nem_erro(
    gold: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("motherduck_token", raising=False)
    configuracao = carregar_configuracao({"RAIZ_DADOS": str(gold.parent)})
    env = {"MOTHERDUCK_TOKEN": TOKEN, "MOTHERDUCK_BANCO": "rfb"}
    real = publicacao.duckdb.connect

    def _conectar(*a: object, **k: object):
        con = real(*a, **k)
        original = con.execute

        class _Proxy:
            def execute(self, sql: str, *args: object):
                if sql.startswith("ATTACH"):
                    # simula erro do MotherDuck que ecoa o token
                    raise duckdb.Error(f"auth falhou com token {TOKEN}")
                return original(sql, *args)

            def __enter__(self):
                return self

            def __exit__(self, *_a: object) -> None:
                con.close()

        return _Proxy()

    monkeypatch.setattr(publicacao.duckdb, "connect", _conectar)
    with pytest.raises(ErroIngestao) as erro:
        publicacao.publicar_motherduck(configuracao, env=env)
    saida = capsys.readouterr()
    assert TOKEN not in str(erro.value)
    assert TOKEN not in saida.out + saida.err
    assert "***" in str(erro.value)
    monkeypatch.delenv("motherduck_token", raising=False)


def test_sql_gerado_nunca_contem_o_token(gold: Path) -> None:
    for dataset in descobrir_datasets(gold):
        assert TOKEN not in gerar_sql_tabela("rfb", dataset)


def test_falha_no_meio_desfaz_a_publicacao_inteira(gold: Path, tmp_path: Path) -> None:
    """R4-03: `dim_x` é recriada antes de `dim_y` falhar; a transação a desfaz."""
    destino = str(tmp_path / "destino.duckdb")
    publicar(gold, destino, "rfb")
    with duckdb.connect() as con:  # o gold do mês seguinte: dim_x muda, dim_y corrompe
        con.execute(f"COPY (SELECT range AS a FROM range(10)) TO '{gold}/dim_x.parquet'")
    (gold / "dim_y.parquet").write_bytes(b"isto nao e parquet")
    vistas: list[str] = []
    with pytest.raises(ErroIngestao, match="transação desfeita"):
        publicar(gold, destino, "rfb", ao_publicar=lambda t: vistas.append(t.nome))
    assert vistas == []
    with duckdb.connect(destino, read_only=True) as con:
        assert con.execute("SELECT count(*) FROM dim_x").fetchone() == (2,)
        assert con.execute("SELECT count(*) FROM dim_y").fetchone() == (1,)


def test_cli_recusa_publicar_com_build_em_andamento(
    gold: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """R4-03: com `_estado/em_andamento.json` o gold pode estar misto; nada é publicado."""
    from rfb_pipeline.orquestracao import marcar_em_andamento

    monkeypatch.setenv("RAIZ_DADOS", str(gold.parent))
    monkeypatch.setenv("MOTHERDUCK_TOKEN", TOKEN)
    monkeypatch.setenv("MOTHERDUCK_BANCO", "rfb")

    def _nao_deve_publicar(*_a: object, **_k: object) -> None:
        raise AssertionError("não deveria publicar com o gold em reconstrução")

    monkeypatch.setattr(cli, "publicar_motherduck", _nao_deve_publicar)
    marcar_em_andamento(carregar_configuracao({"RAIZ_DADOS": str(gold.parent)}), "2026-09")
    assert cli.main(["publicar", "--destino", "motherduck"]) == 1
    erro = capsys.readouterr().err
    assert "rfb publicar recusado" in erro and "gold pode estar misto" in erro
    assert "rfb pipeline --mes 2026-09" in erro
