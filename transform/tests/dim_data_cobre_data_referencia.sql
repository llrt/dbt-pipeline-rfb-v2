{{ config(
    severity='error',
    tags=['escopo_adicao'],
    meta={'escopo': 'adicao'}
) }}

-- BI-01: o calendário contém o dia de `data_referencia` e não tem lacunas entre o primeiro e o
-- último dia (uma linha por dia). Retorna uma linha por violação.
with calendario as (
  select
    count(*) as dias,
    min(data) as primeiro_dia,
    max(data) as ultimo_dia,
    count(*) filter (
      where sk_data = year({{ data_referencia(ref('stg_rfb__estabelecimentos')) }}) * 10000
      + month({{ data_referencia(ref('stg_rfb__estabelecimentos')) }}) * 100
      + day({{ data_referencia(ref('stg_rfb__estabelecimentos')) }})
    ) as dias_data_referencia
  from {{ ref('dim_data') }}
  where sk_data != -1
)

select
  'sem a data_referencia' as violacao,
  dias
from calendario
where dias_data_referencia != 1

union all

select
  'lacuna no calendário' as violacao,
  dias
from calendario
where dias != datediff('day', primeiro_dia, ultimo_dia) + 1
