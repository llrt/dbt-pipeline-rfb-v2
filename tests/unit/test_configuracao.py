from __future__ import annotations

from pathlib import Path

import pytest

from rfb_pipeline.configuracao import carregar_config, ler_credenciais_s3
from rfb_pipeline.erros import ConfiguracaoInvalidaError, CredenciaisS3FaltandoError


def test_carregar_config_usa_padroes_sem_overrides(tmp_path: Path) -> None:
    config = carregar_config(env={"DATA_ROOT": str(tmp_path / "data")})

    assert config.data_root == (tmp_path / "data").resolve()
    assert config.max_taxa_rejeito == 0.0001
    assert config.velocidade_minima_bps == 50 * 1024
    assert config.janela_lentidao_s == 60.0
    assert config.duckdb_memory_limit == "8GB"
    assert config.duckdb_threads == 4


def test_carregar_config_le_overrides_do_ambiente(tmp_path: Path) -> None:
    env = {
        "DATA_ROOT": str(tmp_path / "data"),
        "RFB_MAX_TAXA_REJEITO": "0.05",
        "RFB_VELOCIDADE_MINIMA_BPS": "1000",
        "RFB_JANELA_LENTIDAO_S": "30",
        "DUCKDB_MEMORY_LIMIT": "2GB",
        "DUCKDB_THREADS": "8",
    }

    config = carregar_config(env=env)

    assert config.max_taxa_rejeito == 0.05
    assert config.velocidade_minima_bps == 1000.0
    assert config.janela_lentidao_s == 30.0
    assert config.duckdb_memory_limit == "2GB"
    assert config.duckdb_threads == 8


def test_carregar_config_data_root_s3_usa_diretorio_local_para_o_el(tmp_path: Path) -> None:
    config = carregar_config(
        env={
            "DATA_ROOT": "s3://meu-bucket/prefixo",
            "DATA_ROOT_LOCAL": str(tmp_path / "local"),
            "AWS_ACCESS_KEY_ID": "id",
            "AWS_SECRET_ACCESS_KEY": "secret",
            "AWS_ENDPOINT_URL_S3": "https://fly.storage.tigris.dev",
        }
    )

    assert config.data_root_uri == "s3://meu-bucket/prefixo"
    assert config.data_root_s3 == "s3://meu-bucket/prefixo"
    assert config.data_root == (tmp_path / "local").resolve()
    assert config.raw_dir == (tmp_path / "local").resolve() / "raw"


def test_carregar_config_data_root_s3_sem_credenciais_falha_nomeando_faltantes() -> None:
    with pytest.raises(CredenciaisS3FaltandoError) as exc_info:
        carregar_config(env={"DATA_ROOT": "s3://meu-bucket/prefixo"})

    mensagem = str(exc_info.value)
    assert "AWS_ACCESS_KEY_ID" in mensagem
    assert "AWS_SECRET_ACCESS_KEY" in mensagem
    assert "AWS_ENDPOINT_URL_S3" in mensagem


def test_carregar_config_data_root_local_padrao_quando_nao_definido() -> None:
    config = carregar_config(
        env={
            "DATA_ROOT": "s3://meu-bucket/prefixo",
            "AWS_ACCESS_KEY_ID": "id",
            "AWS_SECRET_ACCESS_KEY": "secret",
            "AWS_ENDPOINT_URL_S3": "https://fly.storage.tigris.dev",
        }
    )

    assert config.data_root == Path("./data").resolve()


def test_ler_credenciais_s3_deriva_endpoint_sem_esquema_e_ssl() -> None:
    creds = ler_credenciais_s3(
        env={
            "AWS_ACCESS_KEY_ID": "id",
            "AWS_SECRET_ACCESS_KEY": "secret",
            "AWS_ENDPOINT_URL_S3": "https://fly.storage.tigris.dev",
        }
    )

    assert creds.endpoint_sem_esquema == "fly.storage.tigris.dev"
    assert creds.usa_ssl is True
    assert creds.url_style == "vhost"


def test_ler_credenciais_s3_http_sem_ssl_e_url_style_customizado() -> None:
    creds = ler_credenciais_s3(
        env={
            "AWS_ACCESS_KEY_ID": "id",
            "AWS_SECRET_ACCESS_KEY": "secret",
            "AWS_ENDPOINT_URL_S3": "http://localhost:5000",
            "S3_URL_STYLE": "path",
        }
    )

    assert creds.endpoint_sem_esquema == "localhost:5000"
    assert creds.usa_ssl is False
    assert creds.url_style == "path"


def test_ler_credenciais_s3_lista_todas_as_variaveis_faltantes() -> None:
    with pytest.raises(CredenciaisS3FaltandoError) as exc_info:
        ler_credenciais_s3(env={})

    assert exc_info.value.faltando == [
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_ENDPOINT_URL_S3",
    ]


def test_config_dirs_derivados_de_data_root(tmp_path: Path) -> None:
    config = carregar_config(env={"DATA_ROOT": str(tmp_path)})

    assert config.raw_dir == tmp_path / "raw"
    assert config.manifests_dir == tmp_path / "_manifests"
    assert config.rejeitos_dir == tmp_path / "raw" / "_rejeitos"
    assert config.gold_dir == tmp_path / "gold"
    assert config.downloads_dir("2026-09") == tmp_path / "_downloads" / "2026-09"


def test_variaveis_vazias_equivalem_a_ausentes(tmp_path: Path) -> None:
    """`cp .env.example .env` com chaves vazias não pode quebrar nem desviar a ingestão."""
    config = carregar_config(
        env={
            "DATA_ROOT": "",
            "DATA_ROOT_LOCAL": "",
            "DUCKDB_THREADS": "",
            "DUCKDB_MEMORY_LIMIT": "  ",
            "RFB_MAX_TAXA_REJEITO": "",
            "RFB_VELOCIDADE_MINIMA_BPS": "",
            "RFB_JANELA_LENTIDAO_S": "",
            "RFB_MAX_RETOMADAS": "",
            "RFB_TIMEOUT_TOTAL_S": "",
        }
    )

    assert config.data_root == Path("./data").resolve()
    assert config.data_root_s3 is None
    assert config.duckdb_threads == 4
    assert config.duckdb_memory_limit == "8GB"
    assert config.max_taxa_rejeito == 0.0001
    assert config.max_retomadas == 50
    assert config.timeout_total_s == 3600.0


def test_data_root_local_vazio_no_modo_s3_usa_o_padrao() -> None:
    config = carregar_config(
        env={
            "DATA_ROOT": "s3://meu-bucket/prefixo",
            "DATA_ROOT_LOCAL": "",
            "AWS_ACCESS_KEY_ID": "id",
            "AWS_SECRET_ACCESS_KEY": "secret",
            "AWS_ENDPOINT_URL_S3": "https://fly.storage.tigris.dev",
        }
    )

    assert config.data_root == Path("./data").resolve()


def test_tetos_de_download_lidos_do_ambiente(tmp_path: Path) -> None:
    config = carregar_config(
        env={
            "DATA_ROOT": str(tmp_path),
            "RFB_MAX_RETOMADAS": "7",
            "RFB_TIMEOUT_TOTAL_S": "120.5",
        }
    )

    assert config.max_retomadas == 7
    assert config.timeout_total_s == 120.5


@pytest.mark.parametrize(
    ("variavel", "valor"),
    [("DUCKDB_THREADS", "muitas"), ("RFB_MAX_RETOMADAS", "1.5"), ("RFB_TIMEOUT_TOTAL_S", "x")],
)
def test_valor_numerico_invalido_vira_erro_de_ingestao(tmp_path: Path, variavel, valor) -> None:
    with pytest.raises(ConfiguracaoInvalidaError) as exc_info:
        carregar_config(env={"DATA_ROOT": str(tmp_path), variavel: valor})

    assert variavel in str(exc_info.value)


def test_env_example_carregado_como_esta_nao_quebra(tmp_path: Path) -> None:
    """Regressão R1-09: valores de `.env.example` (sem edição) precisam ser aceitos."""
    from dotenv import dotenv_values

    exemplo = Path(__file__).resolve().parents[2] / ".env.example"
    env = {k: v for k, v in dotenv_values(exemplo).items() if v is not None}

    config = carregar_config(env=env)

    assert config.data_root == Path("./data").resolve()
