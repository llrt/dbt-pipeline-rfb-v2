# ADR-0013 — Modelo estrela otimizado para ferramentas de BI (Power BI)

**Contexto.** O core já previa dimensões + fato + bridge, mas sem convenções de BI. Pedido do usuário
(2026-09-28): modelo estrela otimizado para Power BI, marcado como melhoria.

**Decisão.**
- **Chaves substitutas inteiras** (`sk_*`, BIGINT/INTEGER) em todas as dimensões, geradas de forma
  determinística a partir do código natural; membro `-1` "NÃO INFORMADO" em todas; FKs da fato nunca nulas.
- **`dim_data`** (calendário) com `sk_data = yyyymmdd`, ano, semestre, trimestre, mês, nome do mês, `ano_mes`,
  dia da semana; usada como dimensão de papel duplo (início de atividade, data da situação, mês de referência).
- **Hierarquias explícitas**: `dim_municipio` (região → UF → mesorregião → microrregião → município, e
  região intermediária → imediata) e `dim_cnae` (seção → divisão → grupo → classe → subclasse), com código e
  descrição em colunas separadas.
- **Duas fatos**: `fct_estabelecimentos` (grão CNPJ, ~65 M linhas; para DuckDB/consultas detalhadas) e
  **`fct_resumo_mensal`** (grão mês × município × CNAE × porte × natureza × situação × ano de início × MEI;
  medidas aditivas `qtd_estabelecimentos`, `qtd_ativos`, `soma_idade_anos`, `soma_capital_social`),
  pequena o bastante para **modo Import** do Power BI e com histórico mensal (ADR-0012).
- Fatos só com chaves inteiras, flags booleanas e medidas; textos de alta cardinalidade ficam fora
  (exceto `cnpj_completo` como dimensão degenerada na fato detalhada).
- Relacionamentos 1:* com filtro em direção única; a bridge de CNAEs secundários é opcional (muitos-para-muitos).
- Tudo exportado como Parquet em `gold/`; `docs/POWER_BI.md` documenta conexão (conector Parquet do Power
  Query ou ODBC do DuckDB), relacionamentos, medidas DAX sugeridas e atualização incremental por mês;
  um `exposure` dbt do tipo dashboard declara a dependência.

**Consequências.** Melhoria sobre o original (escopo `adicao`). O Verifier/revisões checam unicidade das
chaves, integridade referencial e reconciliação `sum(qtd_estabelecimentos) = count(fct_estabelecimentos)`
no mês corrente.

## Emenda R3 (2026-10-01)

A revisão R3 ([R3.md](../revisoes/R3.md), decisões em [R3-triagem.md](../revisoes/R3-triagem.md), AD-020)
corrigiu três pontos da decisão acima. O restante segue valendo.

- **Grão do resumo mensal (R3-02).** `fct_resumo_mensal` **perde `ano_inicio_atividade` e
  `sk_natureza_juridica`**. Grão novo: mês × município × subclasse × porte × situação × MEI. Motivo: o
  grão original tinha 22,0 M linhas e 202 MB por mês, só 2,9× menor que a fato detalhada, e inviabilizava o
  Import de séries longas. A coorte por ano de início fica em `mart_sobrevivencia_coorte`; a natureza,
  em `fct_estabelecimentos`. **Tamanho real medido (fev/2025, 64,5 M estabelecimentos): 5,44 M linhas por mês e 55 MB de Parquet por partição** (5.571 municípios × 1.342 subclasses; `dbt build` de
  `+fct_resumo_mensal +dim_data` em 140 s, pico de RSS 13,9 GB com `DUCKDB_THREADS=4`). O guia recomenda
  Import dos últimos 24 meses.
- **Medida aditiva de capital (R3-01).** O capital social é atributo da **empresa**, repetido em cada
  estabelecimento; somá-lo por estabelecimento inflava o total em 15,6×. O resumo agora traz
  `soma_capital_social_matrizes` (só `eh_matriz`, uma por raiz) e `qtd_matrizes`; capital médio no BI =
  soma ÷ matrizes. `soma_capital_social` deixa de existir.
- **`dim_data` (R3-03, P16, P21).** O calendário vai de **1900-01-01** até o maior entre `data_referencia` e
  a maior data observada (antes: do menor dia observado, que chegava a 1194). Datas anteriores a 1900 vão
  para o membro **`-2` DATA INVÁLIDA** na fato (`bh_empresas` mantém a data original por causa da
  paridade). `-1` NÃO INFORMADO (data nula) e `-2` têm datas sentinela contíguas (`1899-12-31` e
  `1899-12-30`) e `ano`/`mes` nulos, então `dim_data` pode ser marcada como tabela de datas no Power BI.
  `accepted_range` do início de atividade passa a 1900 (warn).
- **Integridade do resumo (R3-18).** As chaves do resumo são checadas contra as dimensões só no mês
  processado (teste singular `error`); a integridade de todas as partições é um teste `warn`.
