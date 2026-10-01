{{ config(
    severity='warn',
    store_failures=true,
    enabled=(target.name != 'ci'),
    tags=['escopo_adicao'],
    meta={'escopo': 'adicao'}
) }}

-- RBP-04 / spec STG AC 8 (emenda): o freshness de `_ingerido_em` mede QUANDO ingerimos; reingerir um
-- mês antigo hoje daria "fresco". Este teste mede a data do extrato (`_data_referencia`, ADR-0004): o
-- extrato mais recente de cada entidade não pode ser mais velho que `limite_dias_extrato` (65) dias.
-- Desligado no target `ci` (as fixtures têm data fixa e envelheceriam o build).
with extratos as (
  select 'empresas' as entidade, max(_data_referencia) as data_extrato
  from {{ source('rfb', 'empresas') }}
  union all
  select 'estabelecimentos', max(_data_referencia)
  from {{ source('rfb', 'estabelecimentos') }}
  union all
  select 'simples', max(_data_referencia)
  from {{ source('rfb', 'simples') }}
)

select
  entidade,
  data_extrato,
  current_date - data_extrato as dias_de_atraso
from extratos
where current_date - data_extrato > {{ var('limite_dias_extrato') }}
