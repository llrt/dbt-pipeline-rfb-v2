from __future__ import annotations

import hashlib
import time
from pathlib import Path

from rfb_pipeline.configuracao import Config
from rfb_pipeline.manifesto import (
    ArquivoManifesto,
    Manifesto,
    caminho_manifesto,
    escrever_manifesto,
    ler_manifesto,
    precisa_reconverter,
    sha256_arquivo,
)


def _config(data_root: Path) -> Config:
    return Config(data_root=data_root, data_root_uri=str(data_root))


def _manifesto_empresas(
    *, nome: str = "Empresas0.zip", bytes_: int = 1, sha256: str = "x"
) -> Manifesto:
    return Manifesto(
        mes_referencia="2026-09",
        data_referencia="2026-09-12",
        iniciado_em="2026-09-12T00:00:00",
        concluido_em="2026-09-12T00:01:00",
        arquivos=(
            ArquivoManifesto(
                nome=nome,
                bytes=bytes_,
                sha256=sha256,
                entidade="empresas",
                linhas_lidas=14,
                linhas_rejeitadas=0,
                parquet=("part-Empresas0.parquet",),
            ),
        ),
    )


def test_sha256_arquivo_e_deterministico_e_confere_com_hashlib(tmp_path: Path) -> None:
    arquivo = tmp_path / "a.zip"
    arquivo.write_bytes(b"conteudo de teste" * 10_000)

    assert sha256_arquivo(arquivo) == sha256_arquivo(arquivo)
    assert sha256_arquivo(arquivo) == hashlib.sha256(arquivo.read_bytes()).hexdigest()


def test_manifesto_tem_os_campos_exigidos_e_resumo_por_entidade(tmp_path: Path) -> None:
    config = _config(tmp_path)
    arquivos = (
        ArquivoManifesto(
            nome="Empresas0.zip",
            bytes=123,
            sha256="abc",
            entidade="empresas",
            linhas_lidas=14,
            linhas_rejeitadas=0,
            parquet=("part-Empresas0.parquet",),
        ),
        ArquivoManifesto(
            nome="Estabelecimentos0.zip",
            bytes=456,
            sha256="def",
            entidade="estabelecimentos",
            linhas_lidas=16,
            linhas_rejeitadas=1,
            parquet=("part-Estabelecimentos0.parquet",),
        ),
    )
    manifesto = Manifesto(
        mes_referencia="2026-09",
        data_referencia="2026-09-12",
        iniciado_em="2026-09-12T00:00:00",
        concluido_em="2026-09-12T00:01:00",
        arquivos=arquivos,
    )

    caminho = escrever_manifesto(config, manifesto)

    assert caminho == caminho_manifesto(config, "2026-09")
    lido = ler_manifesto(config, "2026-09")
    assert lido == manifesto
    assert lido.entidades == {
        "empresas": {"linhas": 14, "rejeitadas": 0},
        "estabelecimentos": {"linhas": 15, "rejeitadas": 1},
    }
    conteudo = caminho.read_text(encoding="utf-8")
    campos = ("mes_referencia", "data_referencia", "iniciado_em", "concluido_em", "versao_pipeline")
    for campo in campos:
        assert campo in conteudo


def test_ler_manifesto_inexistente_retorna_none(tmp_path: Path) -> None:
    assert ler_manifesto(_config(tmp_path), "2026-09") is None


def test_precisa_reconverter_sem_manifesto_anterior(tmp_path: Path) -> None:
    assert precisa_reconverter(
        _config(tmp_path), None, "empresas", "2026-09", [("Empresas0.zip", 1, "x")]
    )


def test_precisa_reconverter_pula_quando_zips_identicos_e_particao_existe(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    particao = config.raw_dir / "rfb" / "empresas" / "mes_referencia=2026-09"
    particao.mkdir(parents=True)
    parquet = particao / "part-Empresas0.parquet"
    parquet.write_bytes(b"conteudo")
    mtime_antes = parquet.stat().st_mtime_ns

    manifesto = _manifesto_empresas()

    resultado = precisa_reconverter(
        config, manifesto, "empresas", "2026-09", [("Empresas0.zip", 1, "x")]
    )

    assert resultado is False
    time.sleep(0.01)
    assert parquet.stat().st_mtime_ns == mtime_antes


def test_precisa_reconverter_quando_zip_mudou_de_tamanho_ou_hash(tmp_path: Path) -> None:
    config = _config(tmp_path)
    (config.raw_dir / "rfb" / "empresas" / "mes_referencia=2026-09").mkdir(parents=True)
    manifesto = _manifesto_empresas()

    assert precisa_reconverter(
        config, manifesto, "empresas", "2026-09", [("Empresas0.zip", 2, "y")]
    )


def test_precisa_reconverter_quando_particao_nao_existe_em_disco(tmp_path: Path) -> None:
    config = _config(tmp_path)
    manifesto = _manifesto_empresas()

    assert precisa_reconverter(
        config, manifesto, "empresas", "2026-09", [("Empresas0.zip", 1, "x")]
    )


def test_precisa_reconverter_force_sempre_reconverte(tmp_path: Path) -> None:
    config = _config(tmp_path)
    (config.raw_dir / "rfb" / "empresas" / "mes_referencia=2026-09").mkdir(parents=True)
    manifesto = _manifesto_empresas()

    assert precisa_reconverter(
        config,
        manifesto,
        "empresas",
        "2026-09",
        [("Empresas0.zip", 1, "x")],
        force=True,
    )


def test_sha256_arquivo_valor_conhecido(tmp_path: Path) -> None:
    """Valor fixo (FIPS 180 'abc'): o teste não espelha a implementação (R1-10; M20)."""
    arquivo = tmp_path / "abc.bin"
    arquivo.write_bytes(b"abc")

    assert sha256_arquivo(arquivo) == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
    vazio = tmp_path / "vazio.bin"
    vazio.write_bytes(b"")
    assert sha256_arquivo(vazio) == (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
