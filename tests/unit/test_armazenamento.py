from __future__ import annotations

import hashlib
from collections.abc import Iterator
from pathlib import Path

import boto3
import duckdb
import pytest
from moto.server import ThreadedMotoServer

from rfb_pipeline.armazenamento import sincronizar
from rfb_pipeline.configuracao import Config, ler_credenciais_s3
from rfb_pipeline.erros import CredenciaisS3FaltandoError, ErroIngestao

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
    from rfb_pipeline.configuracao import carregar_config

    return carregar_config(env=env)


def _criar_parquet(caminho: Path, valor: int) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"COPY (SELECT {valor} AS a) TO '{caminho}' (FORMAT parquet)")
    con.close()


class TestCredenciaisFaltando:
    def test_config_recusa_data_root_s3_sem_credenciais(self, tmp_path: Path) -> None:
        from rfb_pipeline.configuracao import carregar_config

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

    def test_arquivo_multipart_alterado_com_mesmo_tamanho_e_reenviado(
        self, tmp_path: Path, endpoint: str, cliente_s3
    ) -> None:
        """R1-07: acima de 8 MB o upload é multipart (ETag sem MD5); o tamanho não basta."""
        config = _config_s3(tmp_path / "local", endpoint, prefixo="multipart")
        grande = config.gold_dir / "grande.parquet"
        grande.parent.mkdir(parents=True)
        tamanho = 9 * 1024 * 1024
        grande.write_bytes(b"A" * tamanho)

        assert sincronizar(config, cliente_s3=cliente_s3) == ["multipart/gold/grande.parquet"]
        assert (
            "-"
            in cliente_s3.head_object(Bucket=BUCKET, Key="multipart/gold/grande.parquet")["ETag"]
        )
        assert sincronizar(config, cliente_s3=cliente_s3) == []

        grande.write_bytes(b"B" * tamanho)  # mesmo tamanho, conteúdo diferente
        assert sincronizar(config, cliente_s3=cliente_s3) == ["multipart/gold/grande.parquet"]
        corpo = cliente_s3.get_object(Bucket=BUCKET, Key="multipart/gold/grande.parquet")["Body"]
        assert corpo.read(1) == b"B"

    def test_grava_sha256_como_metadado_do_objeto(
        self, tmp_path: Path, endpoint: str, cliente_s3
    ) -> None:
        config = _config_s3(tmp_path / "local", endpoint, prefixo="meta")
        caminho = config.raw_dir / "bd" / "municipio.parquet"
        _criar_parquet(caminho, 5)

        sincronizar(config, cliente_s3=cliente_s3)

        cabecalho = cliente_s3.head_object(Bucket=BUCKET, Key="meta/raw/bd/municipio.parquet")
        assert cabecalho["Metadata"]["sha256"] == hashlib.sha256(caminho.read_bytes()).hexdigest()

    def test_objeto_sem_metadado_sha256_e_reenviado(
        self, tmp_path: Path, endpoint: str, cliente_s3
    ) -> None:
        config = _config_s3(tmp_path / "local", endpoint, prefixo="semmeta")
        caminho = config.raw_dir / "bd" / "municipio.parquet"
        _criar_parquet(caminho, 5)
        cliente_s3.put_object(
            Bucket=BUCKET, Key="semmeta/raw/bd/municipio.parquet", Body=caminho.read_bytes()
        )

        assert sincronizar(config, cliente_s3=cliente_s3) == ["semmeta/raw/bd/municipio.parquet"]
        assert sincronizar(config, cliente_s3=cliente_s3) == []

    def test_residuos_ocultos_nao_sobem(self, tmp_path: Path, endpoint: str, cliente_s3) -> None:
        config = _config_s3(tmp_path / "local", endpoint, prefixo="residuos")
        _criar_parquet(config.raw_dir / "bd" / "municipio.parquet", 5)
        _criar_parquet(config.raw_dir / "rfb" / "empresas" / ".tmp-abc" / "x.parquet", 1)
        (config.raw_dir / "bd" / ".tmp-manifesto.json").write_text("{}")

        assert sincronizar(config, cliente_s3=cliente_s3) == ["residuos/raw/bd/municipio.parquet"]

    def test_nao_falha_sem_raw_ou_gold_locais(
        self, tmp_path: Path, endpoint: str, cliente_s3
    ) -> None:
        config = _config_s3(tmp_path / "local-vazio", endpoint, prefixo="vazio")
        assert sincronizar(config, cliente_s3=cliente_s3) == []


class TestDuckDBLeDoBucket:
    """O secret vem do profile dbt `s3`; aqui só se prova que os parâmetros derivados de
    `CredenciaisS3` (endpoint sem esquema, SSL, estilo de URL) fazem o DuckDB ler do bucket."""

    def test_duckdb_le_parquet_do_moto_com_secret_derivado_das_credenciais(
        self, tmp_path: Path, endpoint: str, cliente_s3
    ) -> None:
        creds = ler_credenciais_s3(
            env={
                "AWS_ACCESS_KEY_ID": "testid",
                "AWS_SECRET_ACCESS_KEY": "testsecret",
                "AWS_ENDPOINT_URL_S3": endpoint,
                "S3_URL_STYLE": "path",
            }
        )
        assert creds.usa_ssl is False  # endpoint http:// nos testes com moto
        local_parquet = tmp_path / "origem.parquet"
        _criar_parquet(local_parquet, 42)
        cliente_s3.upload_file(str(local_parquet), BUCKET, "secret-teste/dado.parquet")

        con = duckdb.connect()
        con.execute("INSTALL httpfs")
        con.execute("LOAD httpfs")
        con.execute(
            "CREATE SECRET s3_secret (TYPE s3, KEY_ID ?, SECRET ?, ENDPOINT ?, REGION ?, "
            f"URL_STYLE ?, USE_SSL {'true' if creds.usa_ssl else 'false'})",
            [
                creds.access_key_id,
                creds.secret_access_key,
                creds.endpoint_sem_esquema,
                creds.region,
                creds.url_style,
            ],
        )
        resultado = con.execute(
            f"SELECT * FROM read_parquet('s3://{BUCKET}/secret-teste/dado.parquet')"
        ).fetchall()
        con.close()

        assert resultado == [(42,)]
