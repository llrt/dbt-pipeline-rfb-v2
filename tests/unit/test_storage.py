from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import boto3
import duckdb
import pytest
from moto.server import ThreadedMotoServer

from rfb_pipeline.config import Config
from rfb_pipeline.errors import CredenciaisS3FaltandoError, ErroIngestao
from rfb_pipeline.storage import sincronizar, sql_create_secret

BUCKET = "meu-bucket"


@pytest.fixture(scope="module")
def servidor_moto() -> Iterator[ThreadedMotoServer]:
    servidor = ThreadedMotoServer(port=0)
    servidor.start()
    yield servidor
    servidor.stop()


@pytest.fixture
def endpoint(servidor_moto: ThreadedMotoServer) -> str:
    host, port = servidor_moto.get_host_and_port()
    return f"http://{host}:{port}"


@pytest.fixture
def cliente_s3(endpoint: str):
    s3 = boto3.client(
        "s3",
        aws_access_key_id="testid",
        aws_secret_access_key="testsecret",
        endpoint_url=endpoint,
        region_name="us-east-1",
    )
    s3.create_bucket(Bucket=BUCKET)
    yield s3
    objetos = s3.list_objects_v2(Bucket=BUCKET).get("Contents", [])
    for obj in objetos:
        s3.delete_object(Bucket=BUCKET, Key=obj["Key"])
    s3.delete_bucket(Bucket=BUCKET)


def _config_s3(data_root_local: Path, endpoint: str, *, prefixo: str = "prefixo") -> Config:
    env = {
        "AWS_ACCESS_KEY_ID": "testid",
        "AWS_SECRET_ACCESS_KEY": "testsecret",
        "AWS_ENDPOINT_URL_S3": endpoint,
        "DATA_ROOT_LOCAL": str(data_root_local),
        "DATA_ROOT": f"s3://{BUCKET}/{prefixo}",
    }
    from rfb_pipeline.config import carregar_config

    return carregar_config(env=env)


def _criar_parquet(caminho: Path, valor: int) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"COPY (SELECT {valor} AS a) TO '{caminho}' (FORMAT parquet)")
    con.close()


class TestCredenciaisFaltando:
    def test_config_recusa_data_root_s3_sem_credenciais(self, tmp_path: Path) -> None:
        from rfb_pipeline.config import carregar_config

        with pytest.raises(CredenciaisS3FaltandoError) as exc_info:
            carregar_config(env={"DATA_ROOT": f"s3://{BUCKET}/prefixo"})

        assert "AWS_ACCESS_KEY_ID" in str(exc_info.value)

    def test_sincronizar_recusa_data_root_local(self, tmp_path: Path) -> None:
        config = Config(data_root=tmp_path, data_root_uri=str(tmp_path))
        with pytest.raises(ErroIngestao):
            sincronizar(config)


class TestSincronizar:
    def test_envia_raw_e_gold_pulando_objetos_ja_sincronizados(
        self, tmp_path: Path, endpoint: str, cliente_s3
    ) -> None:
        config = _config_s3(tmp_path / "local", endpoint)
        _criar_parquet(config.raw_dir / "rfb" / "empresas" / "empresas.parquet", 1)
        _criar_parquet(config.gold_dir / "bh_empresas.parquet", 2)

        enviados = sincronizar(config, cliente_s3=cliente_s3)

        assert sorted(enviados) == [
            "prefixo/gold/bh_empresas.parquet",
            "prefixo/raw/rfb/empresas/empresas.parquet",
        ]
        objetos = cliente_s3.list_objects_v2(Bucket=BUCKET).get("Contents", [])
        chaves = {o["Key"] for o in objetos}
        assert chaves == {
            "prefixo/gold/bh_empresas.parquet",
            "prefixo/raw/rfb/empresas/empresas.parquet",
        }

        # segunda sincronização: nada mudou -> nenhum objeto reenviado
        enviados_de_novo = sincronizar(config, cliente_s3=cliente_s3)
        assert enviados_de_novo == []

    def test_reenvia_quando_o_conteudo_muda(
        self, tmp_path: Path, endpoint: str, cliente_s3
    ) -> None:
        config = _config_s3(tmp_path / "local", endpoint, prefixo="outro-prefixo")
        caminho = config.raw_dir / "bd" / "municipio.parquet"
        _criar_parquet(caminho, 1)

        primeiro_envio = sincronizar(config, cliente_s3=cliente_s3)
        assert primeiro_envio == ["outro-prefixo/raw/bd/municipio.parquet"]

        _criar_parquet(caminho, 2)  # conteúdo (e tamanho) muda
        segundo_envio = sincronizar(config, cliente_s3=cliente_s3)
        assert segundo_envio == ["outro-prefixo/raw/bd/municipio.parquet"]

    def test_nao_falha_sem_raw_ou_gold_locais(
        self, tmp_path: Path, endpoint: str, cliente_s3
    ) -> None:
        config = _config_s3(tmp_path / "local-vazio", endpoint, prefixo="vazio")
        assert sincronizar(config, cliente_s3=cliente_s3) == []


class TestSqlCreateSecret:
    def test_recusa_config_sem_data_root_s3(self, tmp_path: Path) -> None:
        config = Config(data_root=tmp_path, data_root_uri=str(tmp_path))
        with pytest.raises(ErroIngestao):
            sql_create_secret(config)

    def test_duckdb_le_parquet_do_moto_com_o_secret_gerado(
        self, tmp_path: Path, endpoint: str, cliente_s3, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testid")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testsecret")
        monkeypatch.setenv("AWS_ENDPOINT_URL_S3", endpoint)
        monkeypatch.setenv("S3_URL_STYLE", "path")

        config = _config_s3(tmp_path / "local", endpoint, prefixo="secret-teste")
        local_parquet = tmp_path / "origem.parquet"
        _criar_parquet(local_parquet, 42)
        cliente_s3.upload_file(str(local_parquet), BUCKET, "secret-teste/dado.parquet")

        sql = sql_create_secret(config)
        assert "USE_SSL false" in sql  # endpoint http:// nos testes com moto
        assert "URL_STYLE 'path'" in sql

        con = duckdb.connect()
        con.execute("INSTALL httpfs")
        con.execute("LOAD httpfs")
        con.execute(sql)
        resultado = con.execute(
            f"SELECT * FROM read_parquet('s3://{BUCKET}/secret-teste/dado.parquet')"
        ).fetchall()
        con.close()

        assert resultado == [(42,)]
