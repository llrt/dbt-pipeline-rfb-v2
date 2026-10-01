{{ config(
    options={'partition_by': 'mes_referencia', 'overwrite_or_ignore': true}
) }}
-- Fato agregada para BI (ADR-0012/0013). Grão = mês × município × CNAE × porte × natureza ×
-- situação × ano de início × MEI. Medidas aditivas: o Power BI divide soma por soma (idade média =
-- soma_idade_anos / qtd_ativos). Gravada como UMA partição Parquet por mês em
-- `gold/fct_resumo_mensal/mes_referencia=YYYY-MM/`: o build de um mês só reescreve a partição dele
-- (`overwrite_or_ignore`), então o histórico sobrevive ao `warehouse.duckdb`. O dbt-duckdb cria a
-- visão desta relação sobre TODAS as partições do disco; é ela que o BI e as análises consomem.
-- `sk_mes_referencia` = 1º dia do mês como `yyyymm01`, a mesma chave de `dim_data.sk_data`.
-- `ano_inicio_atividade` = -1 quando a data de início é nula (convenção NÃO INFORMADO).
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
  fct.sk_natureza_juridica,
  fct.sk_situacao_cadastral,
  coalesce(ini.ano, -1)::integer as ano_inicio_atividade,
  fct.opcao_mei,
  count(*)::bigint as qtd_estabelecimentos,
  count(*) filter (where fct.eh_ativa)::bigint as qtd_ativos,
  coalesce(sum(fct.idade_anos), 0)::double as soma_idade_anos,
  coalesce(sum(fct.capital_social), 0)::decimal(18, 2) as soma_capital_social
from {{ ref('fct_estabelecimentos') }} as fct
cross join mes
left join {{ ref('dim_data') }} as ini
  on fct.sk_data_inicio_atividade = ini.sk_data
group by all
