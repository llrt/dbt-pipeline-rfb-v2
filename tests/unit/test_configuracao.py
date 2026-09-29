from __future__ import annotations

from pathlib import Path

import pytest

from rfb_pipeline.configuracao import carregar_configuracao, ler_credenciais_s3
from rfb_pipeline.erros import ConfiguracaoInvalidaErro, CredenciaisS3FaltandoErro


def test_carregar_configuracao_usa_padroes_sem_sobrescritas(tmp_path: Path) -> None:
    configuracao = carregar_configuracao(env={"DATA_ROOT": str(tmp_path / "data")})

    assert configuracao.raiz_dados == (tmp_path / "data").resolve()
    assert configuracao.max_taxa_rejeito == 0.0001
    assert configuracao.velocidade_minima_bps == 50 * 1024
    assert configuracao.janela_lentidao_s == 60.0
    assert configuracao.duckdb_memory_limit == "8GB"
    assert configuracao.duckdb_threads == 4


def test_carregar_configuracao_le_sobrescritas_do_ambiente(tmp_path: Path) -> None:
    env = {
        "DATA_ROOT": str(tmp_path / "data"),
        "RFB_MAX_TAXA_REJEITO": "0.05",
        "RFB_VELOCIDADE_MINIMA_BPS": "1000",
        "RFB_JANELA_LENTIDAO_S": "30",
        "DUCKDB_MEMORY_LIMIT": "2GB",
        "DUCKDB_THREADS": "8",
    }

    configuracao = carregar_configuracao(env=env)

    assert configuracao.max_taxa_rejeito == 0.05
    assert configuracao.velocidade_minima_bps == 1000.0
    assert configuracao.janela_lentidao_s == 30.0
    assert configuracao.duckdb_memory_limit == "2GB"
    assert configuracao.duckdb_threads == 8


def test_carregar_configuracao_raiz_dados_s3_usa_diretorio_local_para_o_el(tmp_path: Path) -> None:
    configuracao = carregar_configuracao(
        env={
            "DATA_ROOT": "s3://meu-bucket/prefixo",
            "DATA_ROOT_LOCAL": str(tmp_path / "local"),
            "AWS_ACCESS_KEY_ID": "id",
            "AWS_SECRET_ACCESS_KEY": "secret",
            "AWS_ENDPOINT_URL_S3": "https://fly.storage.tigris.dev",
        }
    )

    assert configuracao.raiz_dados_uri == "s3://meu-bucket/prefixo"
    assert configuracao.raiz_dados_s3 == "s3://meu-bucket/prefixo"
    assert configuracao.raiz_dados == (tmp_path / "local").resolve()
    assert configuracao.raw_dir == (tmp_path / "local").resolve() / "raw"


def test_carregar_configuracao_raiz_dados_s3_sem_credenciais_falha_nomeando_faltantes() -> None:
    with pytest.raises(CredenciaisS3FaltandoErro) as exc_info:
        carregar_configuracao(env={"DATA_ROOT": "s3://meu-bucket/prefixo"})

    mensagem = str(exc_info.value)
    assert "AWS_ACCESS_KEY_ID" in mensagem
    assert "AWS_SECRET_ACCESS_KEY" in mensagem
    assert "AWS_ENDPOINT_URL_S3" in mensagem


def test_carregar_configuracao_raiz_dados_local_padrao_quando_nao_definido() -> None:
    configuracao = carregar_configuracao(
        env={
            "DATA_ROOT": "s3://meu-bucket/prefixo",
            "AWS_ACCESS_KEY_ID": "id",
            "AWS_SECRET_ACCESS_KEY": "secret",
            "AWS_ENDPOINT_URL_S3": "https://fly.storage.tigris.dev",
        }
    )

    assert configuracao.raiz_dados == Path("./data").resolve()


def test_ler_credenciais_s3_deriva_endpoint_sem_esquema_e_ssl() -> None:
    credenciais = ler_credenciais_s3(
        env={
            "AWS_ACCESS_KEY_ID": "id",
            "AWS_SECRET_ACCESS_KEY": "secret",
            "AWS_ENDPOINT_URL_S3": "https://fly.storage.tigris.dev",
        }
    )

    assert credenciais.endpoint_sem_esquema == "fly.storage.tigris.dev"
    assert credenciais.usa_ssl is True
    assert credenciais.url_style == "vhost"


def test_ler_credenciais_s3_http_sem_ssl_e_url_style_customizado() -> None:
    credenciais = ler_credenciais_s3(
        env={
            "AWS_ACCESS_KEY_ID": "id",
            "AWS_SECRET_ACCESS_KEY": "secret",
            "AWS_ENDPOINT_URL_S3": "http://localhost:5000",
            "S3_URL_STYLE": "path",
        }
    )

    assert credenciais.endpoint_sem_esquema == "localhost:5000"
    assert credenciais.usa_ssl is False
    assert credenciais.url_style == "path"


def test_ler_credenciais_s3_lista_todas_as_variaveis_faltantes() -> None:
    with pytest.raises(CredenciaisS3FaltandoErro) as exc_info:
        ler_credenciais_s3(env={})

    assert exc_info.value.faltando == [
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_ENDPOINT_URL_S3",
    ]


def test_configuracao_dirs_derivados_de_raiz_dados(tmp_path: Path) -> None:
    configuracao = carregar_configuracao(env={"DATA_ROOT": str(tmp_path)})

    assert configuracao.raw_dir == tmp_path / "raw"
    assert configuracao.manifestos_dir == tmp_path / "_manifests"
    assert configuracao.rejeitos_dir == tmp_path / "raw" / "_rejeitos"
    assert configuracao.gold_dir == tmp_path / "gold"
    assert configuracao.baixados_dir("2026-09") == tmp_path / "_downloads" / "2026-09"


def test_variaveis_vazias_equivalem_a_ausentes(tmp_path: Path) -> None:
    """`cp .env.example .env` com chaves vazias não pode quebrar nem desviar a ingestão."""
    configuracao = carregar_configuracao(
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

    assert configuracao.raiz_dados == Path("./data").resolve()
    assert configuracao.raiz_dados_s3 is None
    assert configuracao.duckdb_threads == 4
    assert configuracao.duckdb_memory_limit == "8GB"
    assert configuracao.max_taxa_rejeito == 0.0001
    assert configuracao.max_retomadas == 50
    assert configuracao.tempo_limite_total_s == 3600.0


def test_raiz_dados_local_vazio_no_modo_s3_usa_o_padrao() -> None:
    configuracao = carregar_configuracao(
        env={
            "DATA_ROOT": "s3://meu-bucket/prefixo",
            "DATA_ROOT_LOCAL": "",
            "AWS_ACCESS_KEY_ID": "id",
            "AWS_SECRET_ACCESS_KEY": "secret",
            "AWS_ENDPOINT_URL_S3": "https://fly.storage.tigris.dev",
        }
    )

    assert configuracao.raiz_dados == Path("./data").resolve()


def test_tetos_de_baixa_lidos_do_ambiente(tmp_path: Path) -> None:
    configuracao = carregar_configuracao(
        env={
            "DATA_ROOT": str(tmp_path),
            "RFB_MAX_RETOMADAS": "7",
            "RFB_TIMEOUT_TOTAL_S": "120.5",
        }
    )

    assert configuracao.max_retomadas == 7
    assert configuracao.tempo_limite_total_s == 120.5


@pytest.mark.parametrize(
    ("variavel", "valor"),
    [("DUCKDB_THREADS", "muitas"), ("RFB_MAX_RETOMADAS", "1.5"), ("RFB_TIMEOUT_TOTAL_S", "x")],
)
def test_valor_numerico_invalido_vira_erro_de_ingestao(tmp_path: Path, variavel, valor) -> None:
    with pytest.raises(ConfiguracaoInvalidaErro) as exc_info:
        carregar_configuracao(env={"DATA_ROOT": str(tmp_path), variavel: valor})

    assert variavel in str(exc_info.value)


def test_env_example_carregado_como_esta_nao_quebra(tmp_path: Path) -> None:
    """Regressão R1-09: valores de `.env.example` (sem edição) precisam ser aceitos."""
    from dotenv import dotenv_values

    exemplo = Path(__file__).resolve().parents[2] / ".env.example"
    env = {k: v for k, v in dotenv_values(exemplo).items() if v is not None}

    configuracao = carregar_configuracao(env=env)

    assert configuracao.raiz_dados == Path("./data").resolve()
