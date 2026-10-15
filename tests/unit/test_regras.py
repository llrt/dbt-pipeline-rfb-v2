"""Regras de negócio (ADR-0020): catálogo, padronização das linhas e renderização do relatório."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from rfb_pipeline import regras
from rfb_pipeline.caminhos import CATALOGO_REGRAS, RELATORIO_REGRAS_NEGOCIO
from rfb_pipeline.regras import (
    SEM_INTERPRETACAO,
    Interpretacao,
    Linha,
    Regra,
    RegrasErro,
    compor_interpretacao,
    cruzar_com_catalogo,
    interpretacao_existente,
    ler_catalogo,
    marcador,
    padronizar_linhas,
    renderizar,
    traz_identificador,
)

RAIZ = Path(__file__).resolve().parents[2]
ANALISES = RAIZ / "transform" / "analyses" / "regras_negocio"


# ---------------------------------------------------------------------------- catálogo


def test_catalogo_e_analyses_correspondem_um_para_um() -> None:
    """Toda seção RN-xx aponta para uma analysis existente e vice-versa (mutação d)."""
    catalogo = ler_catalogo()
    arquivos = {p.stem for p in ANALISES.glob("rn_*.sql")}
    assert 15 <= len(catalogo) <= 30
    assert {r.analise for r in catalogo.values()} == arquivos
    for rid, regra in catalogo.items():
        assert regra.analise.startswith(f"rn_{rid[3:]}_"), rid
        assert regra.tipo in regras.TIPOS_REGRA


def test_catalogo_tem_fonte_e_leitura_em_toda_regra() -> None:
    secoes = CATALOGO_REGRAS.read_text(encoding="utf-8").split("\n### RN-")[1:]
    assert len(secoes) == len(ler_catalogo())
    for secao in secoes:
        for campo in ("**Enunciado:**", "**Fonte:**", "**Dados:**", "**Conceito:**", "**Leitura"):
            assert campo in secao, f"RN-{secao[:2]} sem {campo}"


def _catalogo(tmp_path: Path, corpo: str) -> Path:
    caminho = tmp_path / "REGRAS.md"
    caminho.write_text(corpo, encoding="utf-8")
    return caminho


def test_ler_catalogo_le_titulo_tipo_e_analysis(tmp_path: Path) -> None:
    caminho = _catalogo(
        tmp_path,
        "# x\n\n### Grupo\n\n### RN-01 — Regra um\n\n- **Tipo:** legal.\n"
        "- **Analysis:** `transform/analyses/regras_negocio/rn_01_um.sql`.\n",
    )
    assert ler_catalogo(caminho) == {"RN-01": Regra("RN-01", "Regra um", "legal", "rn_01_um")}


@pytest.mark.parametrize(
    ("corpo", "mensagem"),
    [
        ("### RN-01 — Sem tipo\n"
         "- **Analysis:** `transform/analyses/regras_negocio/rn_01_a.sql`\n", "sem tipo"),
        ("### RN-01 — Sem analysis\n- **Tipo:** legal.\n", "sem analise"),
        ("### RN-01 — Tipo errado\n- **Tipo:** palpite.\n"
         "- **Analysis:** `transform/analyses/regras_negocio/rn_01_a.sql`\n", "tipo inválido"),
        ("# vazio\n", "nenhuma regra"),
    ],
)  # fmt: skip
def test_ler_catalogo_recusa_secao_incompleta(tmp_path: Path, corpo: str, mensagem: str) -> None:
    with pytest.raises(RegrasErro, match=mensagem):
        ler_catalogo(_catalogo(tmp_path, corpo))


# ---------------------------------------------------------------------------- linhas


def test_padronizar_linhas_aceita_quebra_agregada() -> None:
    tabela = (["regra", "situacao", "avaliados", "violacoes"], [("RN-03", "ATIVA", 10, 2)])
    assert padronizar_linhas("rn_03_x", tabela) == (
        "RN-03",
        [Linha((("situacao", "ATIVA"),), 10, 2)],
    )


def test_padronizar_linhas_sem_linhas_e_universo_vazio() -> None:
    assert padronizar_linhas("rn_14_x", (["regra", "avaliados", "violacoes"], [])) == ("RN-14", [])


@pytest.mark.parametrize(
    ("colunas", "linha", "mensagem"),
    [
        (["regra", "avaliados"], ("RN-01", 1), "faltam as colunas violacoes"),
        (
            ["regra", "cnpj_completo", "avaliados", "violacoes"],
            ("RN-01", "x", 1, 0),
            "cnpj_completo",
        ),
        (["regra", "nome", "avaliados", "violacoes"], ("RN-01", "x", 1, 0), "nome"),
        (["regra", "uf", "avaliados", "violacoes"], ("RN-01", "11222333000181", 1, 0), "CNPJ"),
        (["regra", "uf", "avaliados", "violacoes"], ("RN-01", "PINTE 52998224725", 1, 0), "CPF"),
        (
            ["regra", "situacao", "avaliados", "violacoes"],
            ("RN-01", "ATIVA 14.141.414/0001-55", 1, 0),
            "identificador",
        ),
        (["regra", "avaliados", "violacoes"], ("RN-02", 1, 0), "!= RN-01"),
        (["regra", "avaliados", "violacoes"], ("RN-01", 1, 2), "violacoes"),
        (["regra", "avaliados", "violacoes"], ("RN-01", -1, 0), "inteiro"),
        (["regra", "avaliados", "violacoes"], ("RN-01", 1, True), "inteiro"),
        (["regra", "avaliados", "violacoes"], ("RN-01", 1.5, 0), "inteiro"),
    ],
)
def test_padronizar_linhas_recusa_fora_do_padrao(colunas, linha, mensagem) -> None:
    with pytest.raises(RegrasErro, match=mensagem):
        padronizar_linhas("rn_01_x", (colunas, [linha]))


def test_padronizar_linhas_exige_nome_de_arquivo_no_padrao() -> None:
    with pytest.raises(RegrasErro, match="nome fora do padrão"):
        padronizar_linhas("regra_01", (["regra", "avaliados", "violacoes"], [("RN-01", 1, 0)]))


@pytest.mark.parametrize(
    "valor",
    [
        "11222333000181",  # CNPJ
        "11.222.333/0001-81",  # CNPJ com máscara
        "ATIVA 14.141.414/0001-55",  # CNPJ formatado depois de um rótulo (RRN-01, M7)
        "ATIVA 14141414",  # CNPJ básico (RRN-01, M8)
        "11.222.333",  # CNPJ básico com máscara
        "52998224725",  # CPF
        "529.982.247-25",  # CPF com máscara
        "12ABC34501DE35",  # CNPJ alfanumérico (IN 2.119, art. 2º, parágrafo único)
        "12.ABC.345/01DE-35",  # CNPJ alfanumérico com máscara
        "x 12abc34501de35",  # minúsculas
        "2026-09-13",  # data completa: 8 dígitos (as quebras usam rótulos)
    ],
)
def test_traz_identificador_recusa(valor: str) -> None:
    assert traz_identificador(valor)


@pytest.mark.parametrize(
    "valor",
    [
        "ATIVA",
        "2026",
        "2062 Sociedade Empresária Limitada",
        "4741500",  # CNAE: 7 dígitos
        "opção até 1º de janeiro seguinte",
        "1350 ENTIDADE PÚBLICA SOB REGIME ESPECIAL",
        "basedosdados.regiao_metropolitana_2017",
        "observabilidade.dq_historico_testes",
        "mais de um, no máximo um não baixado",
        "2 ou mais",
    ],
)
def test_traz_identificador_aceita_rotulos(valor: str) -> None:
    assert not traz_identificador(valor)


def test_padronizar_linhas_aceita_numeros_que_nao_sao_identificadores() -> None:
    tabela = (["regra", "ano", "avaliados", "violacoes"], [("RN-01", 2026, 73000000, 0)])
    rid, (linha,) = padronizar_linhas("rn_01_x", tabela)
    assert linha.quebra == (("ano", "2026"),)


# ---------------------------------------------------------------------------- cruzamento

CATALOGO = {
    "RN-01": Regra("RN-01", "Regra um", "legal", "rn_01_um"),
    "RN-02": Regra("RN-02", "Regra dois", "estrutural", "rn_02_dois"),
}
SEM_QUEBRA = ["regra", "avaliados", "violacoes"]


def test_cruzar_com_catalogo_exige_correspondencia() -> None:
    ok = {"rn_01_um": (SEM_QUEBRA, [("RN-01", 5, 1)]), "rn_02_dois": (SEM_QUEBRA, [])}
    assert cruzar_com_catalogo(CATALOGO, ok) == {"RN-01": [Linha((), 5, 1)], "RN-02": []}
    with pytest.raises(RegrasErro, match="sem analysis: RN-02"):
        cruzar_com_catalogo(CATALOGO, {"rn_01_um": ok["rn_01_um"]})
    with pytest.raises(RegrasErro, match="RN-03 não tem seção"):
        cruzar_com_catalogo(CATALOGO, {**ok, "rn_03_tres": (SEM_QUEBRA, [("RN-03", 1, 0)])})
    with pytest.raises(RegrasErro, match="aponta para rn_02_dois"):
        cruzar_com_catalogo(
            CATALOGO, {"rn_01_um": ok["rn_01_um"], "rn_02_outro": (SEM_QUEBRA, [("RN-02", 1, 0)])}
        )


# ---------------------------------------------------------------------------- renderização


def _linhas() -> dict[str, list[Linha]]:
    return {
        "RN-01": [
            Linha((("situacao", "ATIVA"),), 70_000_000, 3),
            Linha((("situacao", "BAIXADA"),), 3_000_000, 1_500_000),
        ],
        "RN-02": [Linha((), 16, 0)],
    }


def test_renderizar_resumo_e_quebras() -> None:
    texto = renderizar(CATALOGO, _linhas(), "2026-09", "2026-09-12")
    assert texto.startswith("# Relatório das regras de negócio — 2026-09\n")
    assert "**2** regras avaliadas: **1** sem violação e **1** com violação." in texto
    catalogo = "../referencia/regras-negocio.md"
    assert (
        f"| [RN-01]({catalogo}#rn-01) | Regra um | legal | 73.000.000 | 1.500.003 | 2,05 % |"
        in texto
    )
    assert f"| [RN-02]({catalogo}#rn-02) | Regra dois | estrutural | 16 | 0 | 0 % |" in texto
    assert "### RN-02" not in texto  # sem violação: só no resumo
    quebra = texto.split("### RN-01 — Regra um")[1]
    assert quebra.index("| BAIXADA |") < quebra.index("| ATIVA |")  # mais violações primeiro
    assert "| ATIVA | 70.000.000 | 3 | < 0,01 % |" in quebra
    assert "**1.500.003** violações em **73.000.000** avaliados (2,05 %)" in quebra
    assert texto.rstrip().endswith(
        "_Sem interpretação manual (escreva abaixo do comentário acima)._"
    )
    assert renderizar(CATALOGO, _linhas(), "2026-09", "2026-09-12") == texto  # determinístico


def test_links_do_relatorio_gerado_resolvem_para_arquivo_e_ancora(tmp_path: Path) -> None:
    """Greptile PR #9: o "Como ler" por regra apontava para o próprio relatório."""
    sys.path.insert(0, str(RAIZ / "scripts"))
    import verificar_links_docs as v

    catalogo = ler_catalogo()
    linhas = {rid: [Linha((("situacao", "ATIVA"),), 10, 1)] for rid in catalogo}
    texto = renderizar(catalogo, linhas, "2026-09", "2026-09-12")
    # o arquivo gerado no CI fica fora de docs/; os links são relativos à pasta do relatório
    gerado = RELATORIO_REGRAS_NEGOCIO.with_name("_gerado-no-teste.md")
    gerado.write_text(texto, encoding="utf-8")
    try:
        assert v.links(texto)
        assert v.verificar_arquivo(gerado) == []
    finally:
        gerado.unlink()


def test_renderizar_singular_e_universo_vazio() -> None:
    linhas = {"RN-01": [Linha((), 1, 1)], "RN-02": []}
    texto = renderizar(CATALOGO, linhas, "2026-09", "2026-09-12")
    assert "**1** violação em **1** avaliado (100,00 %)" in texto
    assert "| Regra dois | estrutural | 0 | 0 | — |" in texto


def test_renderizar_mostra_faixas_informativas_sem_violacao() -> None:
    faixas = [
        Linha((("campo", "início"), ("faixa", "até a data do extrato")), 10, 0),
        Linha((("campo", "início"), ("faixa", "dia seguinte ao extrato")), 2, 0),
    ]
    texto = renderizar(CATALOGO, {"RN-01": faixas, "RN-02": [Linha((), 3, 0)]}, "2026-09", "x")
    assert "_Nenhuma regra violada._" in texto
    secao = texto.split("## Faixas informativas")[1].split("## Interpretação")[0]
    assert "### RN-01 — Regra um" in secao and "### RN-02" not in secao
    assert "| início | dia seguinte ao extrato | 2 | 0 | 0 % |" in secao
    sem_faixa = renderizar(CATALOGO, {"RN-01": [Linha((), 1, 0)], "RN-02": []}, "2026-09", "x")
    assert "## Faixas informativas" not in sem_faixa


def test_renderizar_limita_as_quebras() -> None:
    muitas = [Linha((("uf", f"U{i:02d}"),), 10, i + 1) for i in range(25)]
    texto = renderizar(CATALOGO, {"RN-01": muitas, "RN-02": []}, "2026-09", "2026-09-12")
    assert f"_Mostrando {regras.LIMITE_QUEBRAS} de 25 linhas._" in texto
    assert "| U24 |" in texto and "| U00 |" not in texto


def test_interpretacao_manual_e_preservada_no_mesmo_mes(tmp_path: Path) -> None:
    saida = tmp_path / "relatorio.md"
    assert interpretacao_existente(saida) is None
    saida.write_text("# antigo\n\n" + marcador("2026-10") + "\nTexto à mão.\n", encoding="utf-8")
    anterior = interpretacao_existente(saida)
    assert anterior == Interpretacao("2026-10", "Texto à mão.\n")
    manual, aviso = compor_interpretacao(anterior, "2026-10")
    assert (manual, aviso) == ("Texto à mão.\n", None)
    texto = renderizar(CATALOGO, _linhas(), "2026-10", "2026-10-11", manual)
    assert "## Interpretação de 2026-10\n" in texto
    assert texto.endswith(marcador("2026-10") + "\nTexto à mão.\n")
    assert "# antigo" not in texto
    saida.write_text("# sem marcador\n", encoding="utf-8")
    assert interpretacao_existente(saida) is None


def test_interpretacao_de_outro_mes_vira_anterior_e_avisa() -> None:
    """RRN-07: no mês novo, o texto velho sai de baixo dos números novos e o comando avisa."""
    manual, aviso = compor_interpretacao(
        Interpretacao("2026-09", "\n3.247 empresas MEI.\n"), "2026-10"
    )
    assert manual.startswith(SEM_INTERPRETACAO)
    assert "## Interpretação anterior (2026-09)\n" in manual
    assert manual.rstrip().endswith("3.247 empresas MEI.")
    assert aviso is not None and "2026-09" in aviso and "2026-10" in aviso
    # mesmo mês de novo, sem revisão: o aviso continua
    assert compor_interpretacao(Interpretacao("2026-10", manual), "2026-10") == (manual, aviso)
    # revisado (seção anterior apagada): sem aviso
    assert compor_interpretacao(Interpretacao("2026-10", "\nNovo.\n"), "2026-10")[1] is None


def test_interpretacao_mantem_uma_so_secao_anterior() -> None:
    dois_meses = compor_interpretacao(Interpretacao("2026-09", "\nSetembro.\n"), "2026-10")[0]
    # outubro não foi escrito: novembro mantém a de setembro
    manual, aviso = compor_interpretacao(Interpretacao("2026-10", dois_meses), "2026-11")
    assert manual.count("## Interpretação anterior") == 1
    assert "## Interpretação anterior (2026-09)" in manual and "Setembro." in manual
    assert "2026-09" in aviso
    # outubro escrito: novembro guarda só o de outubro
    escrito = "\nOutubro.\n" + dois_meses.split(SEM_INTERPRETACAO, 1)[1]
    manual, _ = compor_interpretacao(Interpretacao("2026-10", escrito), "2026-11")
    assert "## Interpretação anterior (2026-10)" in manual and "Outubro." in manual
    assert "Setembro." not in manual
    # nada escrito em nenhum mês: nada a preservar
    assert compor_interpretacao(Interpretacao("2026-10", SEM_INTERPRETACAO), "2026-11") == (
        None,
        None,
    )


@pytest.mark.parametrize(
    ("violacoes", "avaliados", "esperado"),
    [
        (0, 10, "0 %"),
        (1, 3, "33,33 %"),
        (1, 1_000_000, "< 0,01 %"),
        (0, 0, "—"),
        (5, 5, "100,00 %"),
    ],
)
def test_percentual(violacoes: int, avaliados: int, esperado: str) -> None:
    assert regras._pct(violacoes, avaliados) == esperado


def test_preparo_local_le_memoria_e_threads_do_ambiente(tmp_path: Path, monkeypatch) -> None:
    from rfb_pipeline.configuracao import carregar_configuracao

    (tmp_path / "_tmp").mkdir()
    monkeypatch.setenv("RAIZ_DADOS", str(tmp_path))
    monkeypatch.setenv("DUCKDB_MEMORY_LIMIT", "16GB")
    monkeypatch.setenv("DUCKDB_THREADS", "4")
    comandos = regras._preparo_local(carregar_configuracao())
    assert comandos == [
        "SET memory_limit = '16GB'",
        "SET threads = 4",
        f"SET temp_directory = '{tmp_path / '_tmp'}'",
    ]
