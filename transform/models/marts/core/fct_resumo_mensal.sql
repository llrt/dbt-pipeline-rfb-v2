{{ config(
    location=raiz_gold() ~ '/fct_resumo_mensal',
    options={'partition_by': 'mes_referencia', 'overwrite_or_ignore': true}
) }}
-- Fato agregada para BI (ADR-0012/0013). Grão = mês × município × CNAE × porte × situação × MEI
-- (emenda R3-02 do ADR-0013: sem `ano_inicio_atividade` nem `natureza_juridica`, que explodiam o
-- resumo para ~22 M linhas/mês; coorte fica em `mart_sobrevivencia_coorte` e natureza na fato
-- detalhada). Medidas aditivas: o Power BI divide soma por soma (idade média = soma_idade_anos /
-- qtd_ativos; capital médio = soma_capital_social_matrizes / qtd_matrizes). O capital social é da
-- EMPRESA e se repete em cada estabelecimento, então só a matriz (uma por raiz) o soma (R3-01). Gravada como UMA partição Parquet por mês em
-- `gold/fct_resumo_mensal/mes_referencia=YYYY-MM/`: o build de um mês só reescreve a partição dele
-- (`overwrite_or_ignore`), então o histórico sobrevive ao `warehouse.duckdb`. O dbt-duckdb cria a
-- visão desta relação sobre TODAS as partições do disco; é ela que o BI e as análises consomem.
-- Localização fixa no gold real (`raiz_gold`), mesmo com `RFB_EXTERNAL_ROOT` temporário: é assim que o
-- backfill de mês antigo grava só esta partição no gold sem sobrescrever o resto (P22).
-- `sk_mes_referencia` = 1º dia do mês como `yyyymm01`, a mesma chave de `dim_data.sk_data`.
with mes as (
  select max(_mes_referencia) as mes_referencia
  from {{ ref('stg_rfb__estabelecimentos') }}
)

select
  mes.mes_referencia::varchar as mes_referencia,
  (replace(mes.mes_referencia, '-', '') || '01')::integer as sk_mes_referencia,
  fct.sk_municipio,
  fct.sk_cnae,
  fct.sk_porte,
  fct.sk_situacao_cadastral,
  fct.opcao_mei,
  count(*)::bigint as qtd_estabelecimentos,
  count(*) filter (where fct.eh_ativa)::bigint as qtd_ativos,
  coalesce(sum(fct.idade_anos), 0)::double as soma_idade_anos,
  count(*) filter (where fct.eh_matriz)::bigint as qtd_matrizes,
  coalesce(sum(fct.capital_social) filter (where fct.eh_matriz), 0)::decimal(18, 2)
    as soma_capital_social_matrizes
from {{ ref('fct_estabelecimentos') }} as fct
cross join mes
group by all
