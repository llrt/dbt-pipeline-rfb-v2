{{ config(
    severity='error',
    tags=['escopo_adicao'],
    meta={'escopo': 'adicao'}
) }}

-- BI-01 / R3-03: o calendário começa em 1900-01-01, contém o dia de `data_referencia`, não tem lacunas
-- (uma linha por dia) e os membros -1/-2 ficam contíguos (1899-12-31 e 1899-12-30), com data, para
-- que a tabela possa ser marcada como tabela de datas no Power BI. Retorna uma linha por violação.
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
  where sk_data > 0
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

union all

select
  'calendário não começa em primeiro_dia_calendario' as violacao,
  dias
from calendario
where primeiro_dia != date '{{ var("primeiro_dia_calendario") }}'

union all

select
  'membros -1/-2 ausentes ou sem data contígua ao calendário' as violacao,
  count(*) as dias
from {{ ref('dim_data') }}
cross join (select min(data) as primeiro_dia from {{ ref('dim_data') }} where sk_data > 0)
where sk_data < 0
having count(*) != 2
  or count(*) filter (
    where (sk_data = -1 and data = primeiro_dia - 1) or (sk_data = -2 and data = primeiro_dia - 2)
  ) != 2

union all

select
  'datas nulas em dim_data' as violacao,
  count(*) as dias
from {{ ref('dim_data') }}
where data is null
having count(*) > 0
