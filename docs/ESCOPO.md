# Escopo: original × adição × adaptado

> Marcação no código: `meta.escopo` + tag `escopo_<valor>` em cada nó dbt ([ADR-0006](adr/0006-marcacao-escopo.md)).
> Listar pelo dbt: `dbt ls --select tag:escopo_original` (ou `escopo_adicao`, `escopo_adaptado`).
> Fonte do original: [docs/referencia-original/](referencia-original/README.md).
> Esta tabela é mantida pelos lotes; a versão final é consolidada na tarefa T31.

Incremento **enriquecimento BD** (ADR-0015): `dbt ls --select tag:incremento_enriquecimento_bd`.

Legenda: **original** = regra/artefato do MVP; **adaptado** = do MVP com mudança intencional documentada;
**adição** = novo neste port.

## Artefatos

| Artefato no port | Escopo | Origem no MVP / justificativa |
|---|---|---|
| Download dos zips RFB | adaptado | `baixar_dados_QSA-*.sh` (wget + unzip) → cliente WebDAV com retry/verificação (URL mudou, ADR-0003) |
| Conversão CSV (latin-1, `;`, escape `"`, multilinha) | original | notebook 1 (opções do `spark.read.csv`) |
| Raw em Parquet all-VARCHAR particionado por mês | adaptado | notebook 1 salvava tabela Spark com `inferSchema` (ADR-0002) |
| Tabelas BD `municipio`, `cnae_2` | original | notebook 1, seção 2 |
| Tabelas BD `populacao`, `pib`; RFB `simples`, `paises`, `qualificacoes` | adição | enriquecimento (densidade, MEI) |
| Manifesto, idempotência, limiar de rejeitos | adição | — |
| Upload para Tigris (`rfb sincronizar`) | adaptado | `subir_arquivos_tigris.py` |
| Fontes dbt com testes de unicidade/completude/integridade/domínio | original | notebooks 2.1.1, 2.1.2, 2.2, 2.3 |
| Freshness das fontes | adição | — |
| `relationships` das fontes (natureza/CNAE/município) avaliados por mês (`relacionamentos_fontes_por_mes`) | adaptado | original tinha um único mês; com meses retidos o `relationships` genérico cruzaria todos (R1-22) |
| Staging tipado | adição | original não tinha camada explícita |
| `bh_empresas` | original | notebook 3 |
| `bh_empresas.idade_atual` relativa a `data_referencia` | adaptado | notebook 3 usava `now()` (ADR-0004) |
| `agg_empresas` | original | notebook 3 |
| Teste de paridade com SQL original | adição | — |
| Star schema (`dim_*`, `fct_estabelecimentos`, bridge) | adição | "trabalhos futuros" do notebook 5 |
| `mart_concorrencia_municipio`, `mart_sobrevivencia_coorte`, `mart_dinamica_mercado`, `mart_fornecedores_proximos` | adição | aprofundam as perguntas do notebook 0/4 |
| Análises do estudo de caso Fundão/ES (`analyses/estudo_caso_q1..q3*`, `q4_fornecedores_secundarios_uf`) | original | notebook 4 (perguntas 1–4, parametrizadas por `caso_*`) |
| Análise `estudo_caso_q4_fornecedores_resumo` (buscas por micro e mesorregião com `upper()` dos dois lados) | adaptado | o notebook 4 comparava MAIÚSCULAS (`agg_empresas`) com a grafia mista da BD e por isso sempre retornava 0 nessas buscas; a comparação corrigida muda a resposta (R3-04) |
| Análises das adições no estudo de caso (`analyses/estudo_caso_adicao_*`, `estudo_caso_parametros`) | adição | usam os 4 marts novos |
| Relatório gerado do estudo de caso (`rfb relatorio`, `src/rfb_pipeline/relatorio.py`) | adição | — |
| Testes genéricos `cnpj_dv_valido` e `data_nao_futura`, `store_failures` nos testes warn, guarda de escopo (`test_escopo_meta.py`) | adição | — |
| Histórico de testes (`dq_historico_testes`, `dq_resumo_execucao`) e catálogo `docs/QUALIDADE_DADOS.md` | adição | — |
| Atualização mensal (`rfb atualizar`, completude do mês, retenção, estado) | adição (pedido do usuário) | original era carga estática única (notebook 0, "Observações") — ADR-0012 |
| Série histórica `fct_resumo_mensal` particionada por mês | adição (pedido do usuário) | ADR-0012/0013 |
| Modelo estrela otimizado para Power BI (`sk_*` inteiras, `dim_data`, hierarquias, fato agregada, guia + exposure) | adição (pedido do usuário) | "modelo estrela/snowflake para self-service" citado como trabalho futuro no notebook 5 — ADR-0013 |
| Grafia dos municípios: `bh_empresas`/`agg_empresas` em MAIÚSCULAS (herdada do SQL original); `dim_municipio` e os marts de analytics na grafia da Base dos Dados ("Fundão"). Para cruzar use `upper(nome_municipio)` + `sigla_uf` (ou `sk_municipio`) | adaptado | P18: a paridade com o original exige as MAIÚSCULAS; a dimensão de BI mantém o texto acentuado da fonte |
| Download da Base dos Dados pela API atual (`downloadTable`); população até 2025 e PIB até 2023 | adição · **incremento: enriquecimento BD** | pedido do usuário 2026-10-01 — ADR-0015 |
| Censo 2022 por município, regiões metropolitanas e vizinhança (raw, staging, `dim_municipio`, vizinhança conformada) | adição · **incremento: enriquecimento BD** | ADR-0015 |
| `mart_concorrencia_area_mercado` e área de mercado no relatório do estudo de caso | adição · **incremento: enriquecimento BD** | ADR-0015 |
| Workaround Hive Metastore (`## Reconstruir tabelas Spark`) | removido | desnecessário: Parquet + DuckDB não têm metastore volátil |
| Script Pig `grep.pig` | removido | exploração manual; substituída por rejeitos do parser e fixtures com os quirks |

## Mapeamento de nomes de colunas (original → port)

| Original | Port |
|---|---|
| `CNAE_principal` | `cnae_principal` |
| `desc_CNAE_principal` | `desc_cnae_principal` |
| `grupo_CNAE_principal` | `grupo_cnae_principal` |
| `CNAEs_secundarios` | `cnaes_secundarios` |
| `UF` | `uf` |
| `CEP` | `cep` (só no staging) |
| demais | iguais |
