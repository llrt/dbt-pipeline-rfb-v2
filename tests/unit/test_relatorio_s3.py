"""R3-06/P19: `rfb relatorio` com `RAIZ_DADOS=s3://` (httpfs + secret, URI S3 no compile).

Sem rede: o "bucket" é um servidor moto local; o warehouse tem uma view sobre Parquet em `s3://`,
como as que o dbt cria no target `s3`.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import boto3
import duckdb
import pytest
from moto.server import ThreadedMotoServer

from rfb_pipeline import relatorio
from rfb_pipeline.configuracao import CredenciaisS3, carregar_configuracao
from rfb_pipeline.relatorio import RelatorioErro, executar_analises, sql_conexao_s3

BUCKET = "balde-relatorio"


@pytest.fixture(scope="module")
def endpoint() -> Iterator[str]:
    servidor = ThreadedMotoServer(port=0)
    servidor.start()
    host, porta = servidor.get_host_and_port()
    yield f"http://{host}:{porta}"
    servidor.stop()


@pytest.fixture
def credenciais(endpoint: str) -> CredenciaisS3:
    return CredenciaisS3("testid", "testsecret", endpoint, url_style="path")


@pytest.fixture
def warehouse_s3(tmp_path: Path, endpoint: str, credenciais: CredenciaisS3) -> Path:
    """Warehouse com a view `main.mart` lendo `s3://<bucket>/gold/mart.parquet` (via moto)."""
    s3 = boto3.client(
        "s3",
        aws_access_key_id="testid",
        aws_secret_access_key="testsecret",
        endpoint_url=endpoint,
        region_name="us-east-1",
    )
    s3.create_bucket(Bucket=BUCKET)
    local = tmp_path / "mart.parquet"
    with duckdb.connect() as con:
        con.execute(f"copy (select 42 as resposta) to '{local}' (format parquet)")
    s3.upload_file(str(local), BUCKET, "gold/mart.parquet")
    banco = tmp_path / "warehouse.duckdb"
    with duckdb.connect(str(banco)) as con:
        for comando in sql_conexao_s3(credenciais):
            con.execute(comando)
        con.execute(
            f"create view main.mart as select * from read_parquet('s3://{BUCKET}/gold/mart.parquet')"
        )
    return banco


def test_sql_da_conexao_espelha_o_profile_s3() -> None:
    comandos = sql_conexao_s3(
        CredenciaisS3("id'x", "segredo", "https://fly.storage.tigris.dev", url_style="vhost")
    )
    assert comandos[:2] == ["INSTALL httpfs", "LOAD httpfs"]
    secret = comandos[2]
    assert secret.startswith("CREATE OR REPLACE TEMPORARY SECRET")
    for trecho in (
        "TYPE s3",
        "KEY_ID 'id''x'",
        "SECRET 'segredo'",
        "ENDPOINT 'fly.storage.tigris.dev'",
        "REGION 'auto'",
        "URL_STYLE 'vhost'",
        "USE_SSL true",
    ):
        assert trecho in secret


def test_view_sobre_s3_so_e_lida_com_o_preparo(
    warehouse_s3: Path, credenciais: CredenciaisS3
) -> None:
    sqls = {"q": "select resposta from main.mart"}
    with pytest.raises(RelatorioErro):  # sem secret: o DuckDB não alcança o "bucket"
        executar_analises(warehouse_s3, sqls)
    resultado = executar_analises(warehouse_s3, sqls, sql_conexao_s3(credenciais))
    assert resultado == {"q": (["resposta"], [(42,)])}


def test_erro_do_preparo_mascara_os_segredos(warehouse_s3: Path) -> None:
    with pytest.raises(RelatorioErro) as erro:
        executar_analises(
            warehouse_s3,
            {},
            ["select 'chave-secreta'::integer"],
            segredos=("chave-secreta",),
        )
    assert "chave-secreta" not in str(erro.value)
    assert "***" in str(erro.value)


def test_gerar_relatorio_em_s3_compila_com_a_uri_e_prepara_a_conexao(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, endpoint: str
) -> None:
    env = {
        "RAIZ_DADOS": "s3://balde/prefixo",
        "RAIZ_DADOS_LOCAL": str(tmp_path / "local"),
        "AWS_ACCESS_KEY_ID": "testid",
        "AWS_SECRET_ACCESS_KEY": "testsecret",
        "AWS_ENDPOINT_URL_S3": endpoint,
    }
    for chave, valor in env.items():
        monkeypatch.setenv(chave, valor)
    monkeypatch.delenv("CAMINHO_DUCKDB", raising=False)
    configuracao = carregar_configuracao(env)
    chamadas: dict = {}

    def _compilar(dir_transform, raiz, target, raiz_local=None):
        chamadas["compile"] = (raiz, target, raiz_local)
        return {"q": "select 1"}

    def _executar(warehouse, sqls, preparo=None, segredos=()):
        chamadas["executar"] = (warehouse, preparo, segredos)
        return {}

    monkeypatch.setattr(relatorio, "compilar_analises", _compilar)
    monkeypatch.setattr(relatorio, "executar_analises", _executar)
    monkeypatch.setattr(relatorio, "ler_qualidade", lambda _w: None)
    monkeypatch.setattr(relatorio, "renderizar", lambda _r, _q: "ok\n")
    relatorio.gerar_relatorio(configuracao, saida=tmp_path / "r.md")
    assert chamadas["compile"] == ("s3://balde/prefixo", "s3", tmp_path / "local")
    warehouse, preparo, segredos = chamadas["executar"]
    assert warehouse == tmp_path / "local" / "warehouse.duckdb"
    assert any("CREATE OR REPLACE TEMPORARY SECRET" in c for c in preparo)
    assert "testsecret" in segredos
