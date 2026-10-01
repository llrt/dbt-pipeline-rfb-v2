# Triagem da RBP (líder, 2026-10-01)

Veredito da RBP ([RBP.md](RBP.md)): **guia aprovado com ressalvas** (43 erros, 8 importantes; P2 reaberta,
P9 parcial) e **projeto aprovado com ressalvas** (0 bloqueantes, 4 importantes, 9 menores, 2 sugestões;
23 mutações, 5 sobreviventes). O líder conferiu no código RBP-01 (`temp_directory` no topo do profile, fora
de `settings`), RBP-03 (`make ci` sem `pytest tests/unit` nem lint) e RBP-10 (nenhum teste usa
`dbt_expectations`).

## Decisões do líder — projeto

| Achado | Decisão | Lote | Resolvido em |
|---|---|---|---|
| **RBP-01** `temp_directory` ignorado | mover para `settings.temp_directory` nos 3 targets; estender o teste de profile com `current_setting('temp_directory')` | FBPa | — |
| **RBP-02** perda de tipagem silenciosa | teste genérico novo "taxa de conversão": para cada coluna tipada do staging (datas, decimais, inteiros), proporção de valores raw não vazios que viraram NULL — `warn` acima de 0,1 %, `error` acima de 5 %; checks de volume nos marts de analytics e na fato (não vazios; `dbt_expectations.expect_table_row_count_to_be_between`); mutações D1 e D3 da RBP devem morrer | FBPa | — |
| **RBP-03** `make ci` sem unit/lint, sem CI remoto | `make ci` passa a rodar `pytest tests/unit` e `make lint`; workflow GitHub Actions (`.github/workflows/ci.yml`) com `make setup && make ci` — **adição**, não executado até o usuário publicar o repositório | FBPa | — |
| **RBP-04** freshness nunca executado | `dbt source freshness` no `make ci` (sobre `_ingerido_em`, sempre fresco nas fixtures); teste `warn` só fora do target `ci` para extrato com `_data_referencia` mais velho que 65 dias; spec STG AC 8 esclarecida | FBPa | — |
| **RBP-05** marts de analytics sem contrato | contratos nos 4 marts (N14 deve morrer no dbt, não só no pytest) | FBPa | — |
| **RBP-06** `stg_bd__pib`/`populacao` sem testes | testes de unicidade (município × ano), não nulos e invariante `pib ≈ va + impostos_liquidos` (tolerância); feito **depois** do B10, que troca o download dessas tabelas | FBPa | — |
| **RBP-07** validação de `mes_referencia` sem teste | teste que roda `dbt compile --vars '{mes_referencia: 202610}'` e espera erro (N09 deve morrer) | FBPa | — |
| **RBP-08** relatório esconde avisos | teste de integração da seção de DQ sobre o histórico real do `make ci`; `ler_qualidade` captura só o erro de tabela inexistente | FBPa | — |
| **RBP-09** colunas sem descrição (87,3 %) | descrever as colunas dos intermediários; guarda de cobertura (≥ 98 % das colunas reais com `description`) | FBPa | — |
| **RBP-10** `dbt_expectations` instalado e não usado | **usar** (decisão): é o pacote dos checks de volume/distribuição pedidos no RBP-02 e exemplo vivo para o guia | FBPa | — |
| **RBP-11** versões | `require-dbt-version: [">=1.10.5", "<2.0.0"]`; faixas de versão no `pyproject.toml` | FBPa | — |
| **RBP-12** histórico de DQ só no `.duckdb` | exportar o histórico também para `gold/dq_historico_testes/` (Parquet) no `on-run-end`, para sobreviver ao descarte do warehouse | B8 | — |
| **RBP-13** regras protegidas só por fixtures | invariantes `warn`: `dat_situacao >= dat_inicio_atividade`, MEI ⇒ Simples; unit tests de `mart_concorrencia_municipio` e `mart_dinamica_mercado` (N11, N19, N20 devem morrer no dbt) | FBPa | — |
| **RBP-14** seleção complexa no Makefile | adotar `selectors.yml` (seletores `ci_mes_antigo`, `original`, `adicao`, `incremento_enriquecimento_bd`) — **adição** | FBPa | — |
| **RBP-15** groups/access | não agora: projeto único, sem consumidores dbt externos; registrado como sugestão no guia | — | — |

## Decisões do líder — guia (RBP-G01..G43)

Todos os 43 itens são corrigidos no lote **FBPg**, com a lista exata da RBP. Regras: SQL "compilado real"
só copiado de `transform/target/compiled/` (G24); itens que dependem do B8 (P22, retenção, checks de gold)
marcados como "previsto no B8" (G29, G41); ferramentas não usadas marcadas como tal (G09, G31); contagens
regeneradas das fixtures (G22). P9 também no `README.md` (seção "primeira execução").

## Sugestões "adição" avaliadas

| Sugestão | Decisão |
|---|---|
| CI remoto (GitHub Actions) | adotar (RBP-03), sem publicar |
| `dbt-project-evaluator` em modo relatório | não agora; registrado no guia como opção (custo de dependência maior que o ganho num projeto deste tamanho) |
| `dbt_expectations` | usar (RBP-10) |
| `dbt-checkpoint`, `audit_helper` | não: guardas Python e paridade por hash já cobrem |
| Elementary | não agora |
| Snapshots | não: extrato mensal é foto completa; a série mensal particionada cumpre o papel |

## Execução

- **FBPg** (guia): agente novo **Gemini 3.8 Flash** (nível de origem do guia, AD-021), só `docs/guia-dbt/` e
  `README.md` (P9) — roda já, em paralelo ao B10.
- **FBPa** (projeto): agente novo **Claude Sonnet médio** (nível de origem dos lotes B4–B7b), **depois** do
  merge do B10 (RBP-06 e as guardas de escopo tocam os mesmos arquivos).
