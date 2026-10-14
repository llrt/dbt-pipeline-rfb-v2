"""Incremento `enriquecimento_ibge` (ADR-0022) contra as fixtures do `make ci` (mês 2026-09).

`dim_municipio` com renda, VA, REGIC, polo de compras e CEMPRE; a ponte de destinos de compra; o
mart CEMPRE × RFB; as colunas do polo na área de mercado; a RN-30 coerente com o mart; as analyses
do caso e dos cenários de uso (docs/CENARIOS_DE_USO.md) e a seção nova do relatório do caso.

incremento: enriquecimento_ibge
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from rfb_pipeline.cli import main
from rfb_pipeline.regras import PADRAO_ANALISES, SUBPASTA_ANALISES, padronizar_linhas
from rfb_pipeline.relatorio import DIR_TRANSFORM, compilar_analises, executar_analises

pytestmark = pytest.mark.skipif(
    "RAIZ_DADOS" not in os.environ, reason="rode via make ci (exporta RAIZ_DADOS)"
)


def _raiz() -> Path:
    return Path(os.environ["RAIZ_DADOS"])


# ------------------------------------------------------------------------------- dim_municipio


def test_dim_municipio_traz_renda_regic_polo_e_cempre_de_fundao(consultar) -> None:
    (linha,) = consultar(
        "select renda_per_capita_media_2022, renda_per_capita_mediana_2022, moradores_renda_2022, "
        "regic_hierarquia_codigo, regic_hierarquia, regic_arranjo_populacional, "
        "id_municipio_polo_compras, nome_municipio_polo_compras, pct_compras_no_polo, ano_cempre, "
        "unidades_locais_cempre, pessoal_ocupado_cempre, ano_va "
        "from {dim_municipio} where nome_municipio = 'Fundão'"
    )
    assert tuple(float(v) for v in linha[:2]) == (1406.78, 1040.0)
    assert linha[2:] == (
        17961, "1C", "Metrópole", "Arranjo Populacional de Vitória/ES", "3205002", "Serra", 45.0,
        2024, 1054, 5125, 2021,
    )  # fmt: skip


def test_polo_de_compras_nulo_sem_ligacao_e_no_membro_menos_um(consultar) -> None:
    linhas = dict(
        consultar(
            "select nome_municipio, nome_municipio_polo_compras from {dim_municipio} "
            "where sigla_uf in ('ES', 'NI')"
        )
    )
    # Serra e Vitória não são origem na REGIC (Vitória está entre os 67 sem questionário)
    assert linhas == {
        "Aracruz": "Vitória", "Fundão": "Serra", "Linhares": "Vitória", "Serra": None,
        "Vitória": None, "NÃO INFORMADO": None,
    }  # fmt: skip


def test_participacoes_do_va_somam_100(consultar) -> None:
    (fora,) = consultar(
        "select count(*) from {dim_municipio} where ano_va is not null and abs(pct_va_agropecuaria "
        "+ pct_va_industria + pct_va_servicos + pct_va_adm_publica - 100) > 0.05"
    )
    assert fora == (0,)


# -------------------------------------------------------------------------------- ponte


def test_ponte_outros_vira_menos_um_e_posto_um_e_o_polo(consultar) -> None:
    outros = consultar(
        "select sk_municipio_origem, tema, pct, posto from {bridge_municipio_destino_compras} "
        "where eh_outros"
    )
    assert outros == [(3203205, "moveis_eletro", 3.33, None)]  # Q1 de "Outros" é 0: fica fora
    (soma,) = consultar(
        "select round(sum(pct), 6) from {bridge_municipio_destino_compras} "
        "where sk_municipio_origem = 3202207 and tema = 'moveis_eletro'"
    )
    assert soma == (100.0,)
    polos = consultar(
        "select pon.sk_municipio_origem, pon.sk_municipio_destino::varchar "
        "from {bridge_municipio_destino_compras} as pon "
        "where pon.tema = 'moveis_eletro' and pon.posto = 1 order by 1"
    )
    pelo_dim = consultar(
        "select sk_municipio, id_municipio_polo_compras from {dim_municipio} "
        "where id_municipio_polo_compras is not null order by 1"
    )
    assert polos == pelo_dim


# ------------------------------------------------------------------------ mart CEMPRE × RFB


def test_mart_emprego_tem_os_16_pares_e_nunca_imputa_sigilo(consultar) -> None:
    (total,) = consultar("select count(*) from {mart_emprego_setor_municipio}")
    assert total == (16,)
    sigilo = consultar(
        "select municipio, classe_cnae, unidades_locais_cempre, pessoal_ocupado_cempre, "
        "pessoal_por_unidade from {mart_emprego_setor_municipio} where tem_sigilo order by 1, 2"
    )
    assert sigilo == [
        ("Aracruz", "47415", 3, None, None),
        ("Linhares", "47415", 12, None, None),
        ("Serra", "20711", 2, None, None),
    ]


def test_mart_emprego_serra_tintas_cempre_ao_lado_dos_ativos_sem_mei(consultar) -> None:
    (linha,) = consultar(
        "select ano_cempre, unidades_locais_cempre, pessoal_ocupado_cempre, ativos_rfb, "
        "ativos_rfb_sem_mei, pessoal_por_unidade, razao_unidades_cempre_ativos_rfb, "
        "mes_referencia_rfb from {mart_emprego_setor_municipio} "
        "where municipio = 'Serra' and classe_cnae = '47415'"
    )
    assert linha == (2024, 33, 196, 1, 0, 5.94, 33.0, "2026-09")


def test_area_de_mercado_de_fundao_mostra_serra_e_os_ativos_de_tintas_no_polo(consultar) -> None:
    (linha,) = consultar(
        "select nome_municipio_polo_compras, pct_compras_no_polo, ativos_no_polo "
        "from {mart_concorrencia_area_mercado} "
        "where cnae_principal = '4741500' and municipio = 'Fundão'"
    )
    assert linha == ("Serra", 45.0, 1)


# ---------------------------------------------------------------------------------- RN-30


def test_rn30_avalia_os_pares_do_mart_e_viola_onde_ele_diz(consultar) -> None:
    sqls = compilar_analises(
        DIR_TRANSFORM, _raiz(), "ci", subpasta=SUBPASTA_ANALISES, padrao=PADRAO_ANALISES
    )
    analise = "rn_30_cempre_coerente_com_rfb"
    resultado = executar_analises(_raiz() / "warehouse.duckdb", {analise: sqls[analise]})
    _, linhas = padronizar_linhas(analise, resultado[analise])
    avaliados = sum(x.avaliados for x in linhas)
    violacoes = sum(x.violacoes for x in linhas)
    (esperado,) = consultar(
        "select count(*), count(*) filter (where coalesce(unidades_locais_cempre, 0) >= 3 "
        "and ativos_rfb_sem_mei = 0) from {mart_emprego_setor_municipio}"
    )
    assert (avaliados, violacoes) == esperado == (16, 8)


# ------------------------------------------------------------------------------- analyses

# (analysis, colunas, uma linha esperada) — números das fixtures do `make ci`; as linhas por
# analysis ficam em LINHAS
ANALISES = {
    "estudo_caso_enriquecimento_ibge": (
        ["ordem", "escopo", "municipio", "regic_hierarquia", "renda_per_capita_media_2022",
         "renda_per_capita_mediana_2022", "polo_compras", "pct_compras_no_polo", "ativos_cnae",
         "unidades_locais_cempre", "pessoal_ocupado_cempre", "tem_sigilo", "ano_cempre"],
        (2, "polo de compras", "Serra", "Metrópole", 1720.1, 1200.0, None, None, 1, 33, 196, False,
         2024),
    ),
    "cenario_renda_concorrencia": (
        ["municipio", "renda_per_capita_media_2022", "mediana_renda_uf", "populacao", "ativos",
         "ativos_por_10k_hab", "mediana_densidade_uf", "abaixo_da_mediana_densidade"],
        ("Vitória", 3351.64, 1650.2, 330000, 0, 0.0, 0.0, True),
    ),
    "cenario_polo_compras_evasao": (
        ["municipio", "regic_hierarquia", "polo_compras", "pct_compras_no_polo",
         "destinos_citados", "pct_outros", "ativos_no_municipio", "ativos_no_polo"],
        ("Fundão", "Metrópole", "Serra", 45.0, 3, 0.0, 1, 1),
    ),
    "cenario_tamanho_setor_cempre": (
        ["municipio", "classe_cnae", "descricao_classe", "ano_cempre", "unidades_locais_cempre",
         "pessoal_ocupado_cempre", "pessoal_assalariado_cempre", "salario_medio_mensal_aprox",
         "pessoal_por_unidade", "tem_sigilo", "ativos_rfb", "ativos_rfb_sem_mei",
         "razao_unidades_cempre_ativos_rfb", "mes_referencia_rfb"],
        ("Linhares", "47415", "Comercio varejista de tintas e materiais para pintura", 2024, 12,
         None, None, None, None, True, 0, 0, None, "2026-09"),
    ),
    "cenario_perfil_economico_va": (
        ["municipio", "ano_va", "pct_va_agropecuaria", "pct_va_industria", "pct_va_servicos",
         "pct_va_adm_publica", "atividade_predominante", "ativos", "ativos_por_10k_hab"],
        ("Fundão", 2021, 6.35, 47.62, 31.75, 14.29, "indústria", 1, 0.5),
    ),
    "cenario_hierarquia_urbana": (
        ["regic_hierarquia_codigo", "regic_hierarquia", "municipios", "municipios_com_ativo",
         "ativos", "populacao", "ativos_por_10k_hab"],
        ("1C", "Metrópole", 3, 2, 2, 870000, 0.02),
    ),
}  # fmt: skip


LINHAS = {
    "estudo_caso_enriquecimento_ibge": 3, "cenario_renda_concorrencia": 2,
    "cenario_polo_compras_evasao": 2, "cenario_tamanho_setor_cempre": 5,
    "cenario_perfil_economico_va": 5, "cenario_hierarquia_urbana": 5,
}  # fmt: skip


@pytest.fixture(scope="module")
def resultados() -> dict:
    sqls = compilar_analises(DIR_TRANSFORM, _raiz(), "ci", padrao="*.sql")
    alvo = {nome: sqls[nome] for nome in ANALISES}
    return executar_analises(_raiz() / "warehouse.duckdb", alvo)


def _normalizar(linha: tuple) -> tuple:
    return tuple(float(v) if type(v).__name__ == "Decimal" else v for v in linha)


@pytest.mark.parametrize("analise", sorted(ANALISES))
def test_analise_roda_nas_fixtures_com_as_colunas_e_a_linha_esperadas(
    analise: str, resultados: dict
) -> None:
    colunas, linhas = resultados[analise]
    esperadas, linha = ANALISES[analise]
    assert colunas == esperadas
    assert linha in [_normalizar(x) for x in linhas]
    assert len(linhas) == LINHAS[analise]


@pytest.mark.parametrize("analise", sorted(ANALISES))
def test_analise_so_traz_agregados_sem_cnpj_nem_nome(analise: str) -> None:
    """ADR-0008: nenhuma analysis do incremento lê o CNPJ ou o nome dos estabelecimentos."""
    linhas = (DIR_TRANSFORM / "analyses" / f"{analise}.sql").read_text(encoding="utf-8")
    texto = "\n".join(x for x in linhas.splitlines() if not x.lstrip().startswith("--"))
    for proibido in ("cnpj", "razao_social", "nome_fantasia", "fct_estabelecimentos"):
        assert proibido not in texto.lower(), proibido


def test_relatorio_do_caso_traz_a_secao_do_ibge(tmp_path: Path) -> None:
    destino = tmp_path / "relatorio.md"
    assert main(["relatorio", "--saida", str(destino), "--target", "ci"]) == 0
    texto = destino.read_text(encoding="utf-8")
    assert "## Enriquecimento com o IBGE (renda, rede urbana e CEMPRE)" in texto
    caso = "| município do caso | Fundão | Metrópole | 1406,78 | 1040,00 | Serra | 45,00 | 1 |"
    assert caso in texto
    assert (
        "os moradores de Fundão/ES vão principalmente a **Serra** (45,0 % desses "
        "deslocamentos), onde há **1** ativo do CNAE 4741500."
    ) in texto
    assert "### Polo de compras dos municípios da UF" in texto
    assert "| Linhares | 47415 |" in texto and "| True | 0 | 0 |" in texto  # sigilo sinalizado


# ------------------------------------------------------------ compatibilidade do modo offline


def test_pipeline_offline_sem_ibge_sai_0_e_constroi_o_gold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Condição da v1.4 ser minor: um espelho `--origem-local` da v1.3 (sem `ibge/`) funciona.

    dbt real num `RAIZ_DADOS` temporário (target e logs do dbt também temporários, para não tocar
    no `transform/target` do `make ci`). As colunas do IBGE saem NULL, a ponte sai vazia, o mart
    CEMPRE × RFB só tem os pares da RFB e a RN-30 os avalia sem violação; o relatório do caso sai.
    """
    import shutil

    from rfb_pipeline.relatorio import _como_dict

    fixtures = Path(__file__).resolve().parents[2] / ".tmp" / "ci" / "fixtures"
    origem = tmp_path / "espelho-v1.3"
    shutil.copytree(fixtures, origem, ignore=shutil.ignore_patterns("ibge"))
    raiz = tmp_path / "dados"
    monkeypatch.setenv("RAIZ_DADOS", str(raiz))
    monkeypatch.delenv("CAMINHO_DUCKDB", raising=False)
    monkeypatch.setenv("DBT_TARGET_PATH", str(tmp_path / "target"))
    monkeypatch.setenv("DBT_LOG_PATH", str(tmp_path / "logs"))

    argumentos = ["--origem-local", str(origem), "--permitir-incompleto", "--target", "ci"]
    codigo = main(
        ["pipeline", *argumentos, "--sem-publicar", "--sem-relatorio", "--mes", "2026-09"]
    )

    assert codigo == 0
    assert capsys.readouterr().out.count("AVISO") == 6  # as seis tabelas IBGE, publicadas vazias
    gold = raiz / "gold"

    def consultar(sql: str) -> list[tuple]:
        import duckdb

        with duckdb.connect() as con:
            return con.execute(sql.replace("{gold}", str(gold))).fetchall()

    assert consultar(
        "select count(*), count(renda_per_capita_media_2022), count(regic_hierarquia), "
        "count(id_municipio_polo_compras), count(unidades_locais_cempre), count(ano_va) "
        "from '{gold}/dim_municipio.parquet'"
    ) == [(9, 0, 0, 0, 0, 8)]  # o VA vem da Base dos Dados, não do IBGE direto
    # relação vazia: o dbt-duckdb grava uma linha toda NULL no Parquet (a view do warehouse filtra)
    assert consultar(
        "select count(sk_municipio_origem) from '{gold}/bridge_municipio_destino_compras.parquet'"
    ) == [(0,)]
    assert consultar(
        "select count(*), count(unidades_locais_cempre), min(ativos_rfb) "
        "from '{gold}/mart_emprego_setor_municipio.parquet'"
    ) == [(8, 0, 1)]  # só os pares com ativo na RFB
    assert consultar(
        "select count(id_municipio_polo_compras), count(ativos_no_polo) "
        "from '{gold}/mart_concorrencia_area_mercado.parquet'"
    ) == [(0, 0)]

    sqls = compilar_analises(
        DIR_TRANSFORM, raiz, "ci", subpasta=SUBPASTA_ANALISES, padrao="rn_30_*.sql"
    )
    analise = "rn_30_cempre_coerente_com_rfb"
    _, linhas = padronizar_linhas(
        analise, executar_analises(raiz / "warehouse.duckdb", sqls)[analise]
    )
    assert (sum(x.avaliados for x in linhas), sum(x.violacoes for x in linhas)) == (8, 0)

    destino = tmp_path / "relatorio.md"
    assert main(["relatorio", "--saida", str(destino), "--target", "ci"]) == 0
    texto = destino.read_text(encoding="utf-8")
    assert "_Fundão/ES não tem polo de compras na REGIC 2018._" in texto
    caso = _como_dict(
        executar_analises(
            raiz / "warehouse.duckdb",
            {"c": compilar_analises(DIR_TRANSFORM, raiz, "ci")["estudo_caso_enriquecimento_ibge"]},
        )["c"]
    )
    assert [r["escopo"] for r in caso] == ["município do caso", "UF"]
