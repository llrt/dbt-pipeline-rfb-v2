from __future__ import annotations

import csv
import gzip
import hashlib
import io
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import gerar_fixtures  # noqa: E402


def _hash_tree(root: Path) -> dict[str, str]:
    hashes = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            hashes[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def _ler_zip_rfb(
    root: Path, nome_zip: str, mes: str = gerar_fixtures.MES_REFERENCIA
) -> tuple[str, list[list[str]]]:
    with zipfile.ZipFile(root / "rfb" / mes / nome_zip) as zf:
        nome_interno = zf.namelist()[0]
        texto = zf.read(nome_interno).decode("latin-1")
    linhas = list(csv.reader(io.StringIO(texto), delimiter=";", quotechar='"'))
    return nome_interno, linhas


def test_determinismo_bytes_identicos(tmp_path: Path) -> None:
    saida1 = tmp_path / "run1"
    saida2 = tmp_path / "run2"
    gerar_fixtures.gerar_fixtures(saida1)
    gerar_fixtures.gerar_fixtures(saida2)

    assert _hash_tree(saida1) == _hash_tree(saida2)
    assert len(_hash_tree(saida1)) > 0


def test_encoding_latin1_contem_bytes_de_a_til(tmp_path: Path) -> None:
    gerar_fixtures.gerar_fixtures(tmp_path)
    with zipfile.ZipFile(
        tmp_path / "rfb" / gerar_fixtures.MES_REFERENCIA / "Estabelecimentos0.zip"
    ) as zf:
        conteudo_bytes = zf.read(zf.namelist()[0])

    # "Ã" (U+00C3) em latin-1 é o byte 0xC3.
    assert "Ã".encode("latin-1") in conteudo_bytes
    assert conteudo_bytes.decode("latin-1")  # decodifica sem erro


def test_linha_k_tem_barra_invertida_antes_da_aspa_de_fechamento(tmp_path: Path) -> None:
    gerar_fixtures.gerar_fixtures(tmp_path)
    with zipfile.ZipFile(tmp_path / "rfb" / gerar_fixtures.MES_REFERENCIA / "Empresas0.zip") as zf:
        texto = zf.read(zf.namelist()[0]).decode("latin-1")

    assert '"EMPRESA EXTERIOR LTDA\\";"2062"' in texto

    _, linhas = _ler_zip_rfb(tmp_path, "Empresas0.zip")
    linha_k = next(linha for linha in linhas if linha[0] == "13131313")
    assert linha_k[1] == "EMPRESA EXTERIOR LTDA\\"


def test_linha_o_quebra_de_linha_dentro_de_aspas_mantem_registro_unico(tmp_path: Path) -> None:
    gerar_fixtures.gerar_fixtures(tmp_path)
    with zipfile.ZipFile(
        tmp_path / "rfb" / gerar_fixtures.MES_REFERENCIA / "Estabelecimentos0.zip"
    ) as zf:
        texto = zf.read(zf.namelist()[0]).decode("latin-1")

    assert "TINTAS FUNDAO\nFILIAL SERRA" in texto

    _, linhas = _ler_zip_rfb(tmp_path, "Estabelecimentos0.zip")
    linha_o = next(linha for linha in linhas if linha[0] == "11111111" and linha[1] == "0002")
    assert linha_o[4] == "TINTAS FUNDAO\nFILIAL SERRA"


def test_contagem_estabelecimentos_e_empresas(tmp_path: Path) -> None:
    gerar_fixtures.gerar_fixtures(tmp_path)

    _, linhas_estab = _ler_zip_rfb(tmp_path, "Estabelecimentos0.zip")
    _, linhas_emp = _ler_zip_rfb(tmp_path, "Empresas0.zip")

    assert len(linhas_estab) == 16
    # 15 raízes + a linha "fantasma" que repete a raiz de B (R4-05)
    assert len(linhas_emp) == 16
    assert len({linha[0] for linha in linhas_emp}) == 15


def test_dv_valido_em_todos_exceto_l(tmp_path: Path) -> None:
    gerar_fixtures.gerar_fixtures(tmp_path)
    _, linhas = _ler_zip_rfb(tmp_path, "Estabelecimentos0.zip")

    # id L = cnpj_raiz 14141414
    for linha in linhas:
        raiz, ordem, dv = linha[0], linha[1], linha[2]
        correto = gerar_fixtures.calcular_dv_cnpj(raiz + ordem)
        if raiz == "14141414":
            assert dv != correto
        else:
            assert dv == correto


def test_nomes_internos_dos_zips_seguem_o_padrao_real(tmp_path: Path) -> None:
    gerar_fixtures.gerar_fixtures(tmp_path)

    nome_empresas, _ = _ler_zip_rfb(tmp_path, "Empresas0.zip")
    nome_estab, _ = _ler_zip_rfb(tmp_path, "Estabelecimentos0.zip")
    nome_cnaes, _ = _ler_zip_rfb(tmp_path, "Cnaes.zip")

    assert nome_empresas == "K3241.K03200Y0.D60912.EMPRECSV"
    assert nome_estab == "K3241.K03200Y0.D60912.ESTABELE"
    assert nome_cnaes == "F.K03200$Z.D60912.CNAECSV"

    with zipfile.ZipFile(tmp_path / "rfb" / gerar_fixtures.MES_REFERENCIA / "Simples.zip") as zf:
        assert zf.namelist()[0] == "F.K03200$W.SIMPLES.CSV.D60912"


def test_bd_csv_gz_utf8_com_header(tmp_path: Path) -> None:
    gerar_fixtures.gerar_fixtures(tmp_path)

    for nome_tabela, colunas_esperadas in [
        ("municipio", 27),
        ("cnae_2", 14),
        ("populacao", 4),
        ("pib", 9),
        ("censo_2022_municipio", 13),  # incremento: enriquecimento_bd
        ("regiao_metropolitana_2017", 8),  # incremento: enriquecimento_bd
        ("vizinhanca_municipio", 3),  # incremento: enriquecimento_bd
    ]:
        with gzip.open(tmp_path / "bd" / f"{nome_tabela}.csv.gz", "rt", encoding="utf-8") as fh:
            linhas = list(csv.reader(fh))
        assert len(linhas[0]) == colunas_esperadas


def test_bd_municipio_8_registros_exceto_exterior_e_boa_esperanca(tmp_path: Path) -> None:
    gerar_fixtures.gerar_fixtures(tmp_path)
    with gzip.open(tmp_path / "bd" / "municipio.csv.gz", "rt", encoding="utf-8") as fh:
        linhas = list(csv.DictReader(fh))

    assert len(linhas) == 8
    ids_rf = {linha["id_municipio_rf"] for linha in linhas}
    assert "9707" not in ids_rf
    assert "1182" not in ids_rf


def _ler_bd(raiz: Path, nome: str) -> list[dict[str, str]]:
    with gzip.open(raiz / "bd" / f"{nome}.csv.gz", "rt", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# incremento: enriquecimento_bd
def test_bd_censo_2022_fundao_e_agua_branca_pi_ausente(tmp_path: Path) -> None:
    gerar_fixtures.gerar_fixtures(tmp_path)
    linhas = {r["id_municipio"]: r for r in _ler_bd(tmp_path, "censo_2022_municipio")}

    fundao = linhas["3202207"]
    assert (fundao["domicilios"], fundao["populacao"], fundao["area"]) == ("6715", "17951", "287")
    assert (fundao["idade_mediana"], fundao["indice_envelhecimento"]) == ("37", "67.68")
    assert "2200202" not in linhas  # sem Censo: denominadores NULL
    assert len(linhas) == 7


# incremento: enriquecimento_bd
def test_bd_regiao_metropolitana_so_fundao_serra_vitoria(tmp_path: Path) -> None:
    gerar_fixtures.gerar_fixtures(tmp_path)
    linhas = _ler_bd(tmp_path, "regiao_metropolitana_2017")

    assert {r["id_municipio"] for r in linhas} == {"3202207", "3205002", "3205309"}
    assert {r["nome_regiao_metropolitana"] for r in linhas} == {"RM Grande Vitória"}
    assert all(r["geometria"].startswith("POLYGON") for r in linhas)


# incremento: enriquecimento_bd
def test_bd_vizinhanca_traz_sujeira_e_ano_antigo(tmp_path: Path) -> None:
    gerar_fixtures.gerar_fixtures(tmp_path)
    linhas = _ler_bd(tmp_path, "vizinhanca_municipio")
    pares = [(r["ano"], r["id_municipio_1"], r["id_municipio_2"]) for r in linhas]

    assert ("2019", "3202207", "3203205") in pares  # só no ano antigo
    assert pares.count(("2020", "3202207", "3200607")) == 2  # duplicata
    assert ("2020", "3203205", "3203205") in pares  # autopar
    assert ("2020", "3205309", "3202207") not in pares  # assimetria: o modelo simetriza


def test_dominio_rfb_municipios_sem_acento_maiusculo(tmp_path: Path) -> None:
    gerar_fixtures.gerar_fixtures(tmp_path)
    _, linhas = _ler_zip_rfb(tmp_path, "Municipios.zip")
    mapa = {codigo: descricao for codigo, descricao in linhas}

    assert mapa["5643"] == "FUNDAO"
    assert mapa["9707"] == "EXTERIOR"
    assert mapa["1182"] == "BOA ESPERANCA DO NORTE"


def test_mes_anterior_tem_15_estabelecimentos_sem_a_linha_o(tmp_path: Path) -> None:
    gerar_fixtures.gerar_fixtures(tmp_path)
    _, atual = _ler_zip_rfb(tmp_path, "Estabelecimentos0.zip")
    _, anterior = _ler_zip_rfb(tmp_path, "Estabelecimentos0.zip", gerar_fixtures.MES_ANTERIOR)

    assert len(atual) == 16
    assert len(anterior) == 15
    # O é a filial de A (raiz 11111111, ordem 0002): só existe em 2026-09.
    assert ("11111111", "0002") in {(linha[0], linha[1]) for linha in atual}
    assert ("11111111", "0002") not in {(linha[0], linha[1]) for linha in anterior}
    assert {(linha[0], linha[1]) for linha in anterior} < {(linha[0], linha[1]) for linha in atual}


def test_mes_anterior_tem_15_raizes_e_nomes_internos_d60810(tmp_path: Path) -> None:
    gerar_fixtures.gerar_fixtures(tmp_path)
    mes = gerar_fixtures.MES_ANTERIOR

    nome_empresas, empresas = _ler_zip_rfb(tmp_path, "Empresas0.zip", mes)
    nome_estab, _ = _ler_zip_rfb(tmp_path, "Estabelecimentos0.zip", mes)
    nome_cnaes, _ = _ler_zip_rfb(tmp_path, "Cnaes.zip", mes)
    nome_simples, _ = _ler_zip_rfb(tmp_path, "Simples.zip", mes)

    assert len(empresas) == 16  # 15 raízes + a linha "fantasma" (R4-05)
    assert len({linha[0] for linha in empresas}) == 15
    assert nome_empresas == "K3241.K03200Y0.D60810.EMPRECSV"
    assert nome_estab == "K3241.K03200Y0.D60810.ESTABELE"
    assert nome_cnaes == "F.K03200$Z.D60810.CNAECSV"
    assert nome_simples == "F.K03200$W.SIMPLES.CSV.D60810"


def test_mes_anterior_tem_todos_os_zips_do_mes_atual(tmp_path: Path) -> None:
    gerar_fixtures.gerar_fixtures(tmp_path)
    atual = {p.name for p in (tmp_path / "rfb" / gerar_fixtures.MES_REFERENCIA).iterdir()}
    anterior = {p.name for p in (tmp_path / "rfb" / gerar_fixtures.MES_ANTERIOR).iterdir()}

    assert atual == anterior
    assert len(atual) == 9
