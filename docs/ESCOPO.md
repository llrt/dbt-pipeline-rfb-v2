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
| Freshness das fontes (`dbt source freshness` no `make ci`) e teste `extrato_desatualizado` (idade do extrato, `warn` fora do target `ci`) | adição | — |
| `relationships` das fontes (natureza/CNAE/município) avaliados por mês (`relacionamentos_fontes_por_mes`) | adaptado | original tinha um único mês; com meses retidos o `relationships` genérico cruzaria todos (R1-22) |
| Staging tipado | adição | original não tinha camada explícita |
| `bh_empresas` | original | notebook 3 |
| `bh_empresas.idade_atual` relativa a `data_referencia` | adaptado | notebook 3 usava `now()` (ADR-0004) |
| CPF mascarado nos nomes do gold (`bh_empresas.nome`, `mart_fornecedores_proximos.nome`): todo trecho de exatamente 11 dígitos vira `***.***.***-**` (`mascarar_cpf_no_nome`); a paridade aplica a mesma máscara no alinhamento final; teste `sem_cpf_no_nome` (error) | adaptado | a razão social do empresário individual/MEI termina com o CPF do titular (12,5 M nomes em 2026-09); o original o expunha. Decisão do usuário (ADR-0008, emenda R4-01) |
| Uma linha por `cnpj_raiz` nas Empresas (`empresa_preferida_por_raiz` no staging e na leitura da paridade) | adaptado | o extrato real de 2026-09 traz a raiz 08314885 duas vezes (uma linha "fantasma" sem razão social, natureza 0000); o SQL original duplicaria os 51 estabelecimentos dela. O teste de unicidade da fonte vira `warn` com `store_failures` (B8, `docs/EXECUCAO_REAL.md`) |
| Conversão de CSV com bytes 0x80–0x9F (transcodificação latin-1 → UTF-8 em Python antes do DuckDB) | adaptado | o leitor latin-1 do DuckDB recusa esses bytes, que o extrato real 2026-09 traz em 5 campos; o Spark do original os lia como latin-1 (B8) |
| `agg_empresas` | original | notebook 3 |
| Teste de paridade com SQL original | adição | — |
| Star schema (`dim_*`, `fct_estabelecimentos`, bridge) | adição | "trabalhos futuros" do notebook 5 |
| `mart_concorrencia_municipio`, `mart_sobrevivencia_coorte`, `mart_dinamica_mercado`, `mart_fornecedores_proximos` | adição | aprofundam as perguntas do notebook 0/4 |
| Análises do estudo de caso Fundão/ES (`analyses/estudo_caso_q1..q3*`, `q4_fornecedores_secundarios_uf`) | original | notebook 4 (perguntas 1–4, parametrizadas por `caso_*`) |
| Análise `estudo_caso_q4_fornecedores_resumo` (buscas por micro e mesorregião com `upper()` dos dois lados) | adaptado | o notebook 4 comparava MAIÚSCULAS (`agg_empresas`) com a grafia mista da BD e por isso sempre retornava 0 nessas buscas; a comparação corrigida muda a resposta (R3-04) |
| Análises das adições no estudo de caso (`analyses/estudo_caso_adicao_*`, `estudo_caso_parametros`) | adição | usam os 4 marts novos |
| Relatório gerado do estudo de caso (`rfb relatorio`, `src/rfb_pipeline/relatorio.py`) | adição | — |
| Testes genéricos `cnpj_dv_valido` e `data_nao_futura`, `store_failures` nos testes warn, guarda de escopo (`test_escopo_meta.py`) | adição | — |
| Endurecimento da revisão RBP: teste genérico `taxa_conversao_tipada`, checks de volume (`dbt_expectations`), contratos nos marts de analytics, `selectors.yml`, guardas de cobertura de descrições, `make ci` com unit + lint e workflow `.github/workflows/ci.yml` (não executado até o repositório ser publicado) | adição | docs/revisoes/RBP-triagem.md |
| Histórico de testes (`dq_historico_testes`, `dq_resumo_execucao`) e catálogo `docs/QUALIDADE_DADOS.md` | adição | — |
| Atualização mensal (`rfb atualizar`, completude do mês, retenção, estado) | adição (pedido do usuário) | original era carga estática única (notebook 0, "Observações") — ADR-0012 |
| Pipeline ponta a ponta (`rfb pipeline`/`make pipeline`), backfill de mês antigo só do resumo (P22), teste `fct_resumo_mensal_gold_corrente`, publicação no fim quando o MotherDuck está configurado, `docs/OPERACAO.md` | adição (pedido do usuário) | ADR-0012/0016; original rodava os notebooks à mão |
| Histórico de DQ exportado para `gold/dq_historico_testes/` (Parquet por execução) | adição | RBP-12: sobrevive ao descarte do `warehouse.duckdb` |
| Série histórica `fct_resumo_mensal` particionada por mês | adição (pedido do usuário) | ADR-0012/0013 |
| Modelo estrela otimizado para Power BI (`sk_*` inteiras, `dim_data`, hierarquias, fato agregada, guia + exposure) | adição (pedido do usuário) | "modelo estrela/snowflake para self-service" citado como trabalho futuro no notebook 5 — ADR-0013 |
| Grafia dos municípios: `bh_empresas`/`agg_empresas` em MAIÚSCULAS (herdada do SQL original); `dim_municipio` e os marts de analytics na grafia da Base dos Dados ("Fundão"). Para cruzar use `upper(nome_municipio)` + `sigla_uf` (ou `sk_municipio`) | adaptado | P18: a paridade com o original exige as MAIÚSCULAS; a dimensão de BI mantém o texto acentuado da fonte |
| Download da Base dos Dados pela API atual (`downloadTable`); população até 2025 e PIB até 2023 | adição · **incremento: enriquecimento BD** | pedido do usuário 2026-10-01 — ADR-0015 |
| Censo 2022 por município, regiões metropolitanas e vizinhança (raw, staging, `dim_municipio`, vizinhança conformada) | adição · **incremento: enriquecimento BD** | ADR-0015 |
| `mart_concorrencia_area_mercado` e área de mercado no relatório do estudo de caso | adição · **incremento: enriquecimento BD** | ADR-0015 |
| Publicação opcional do gold no MotherDuck (`rfb publicar`) | adição (pedido do usuário 2026-10-01) | ADR-0016 |
| Guia de acesso do Power BI aos dados (Parquet, DuckDB local, MotherDuck) | adição (pedido do usuário) | ADR-0016 |
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
