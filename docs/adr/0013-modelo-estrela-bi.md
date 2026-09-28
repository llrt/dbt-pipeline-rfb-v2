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
