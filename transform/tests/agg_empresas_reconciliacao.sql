{{ config(
    severity='error',
    tags=['escopo_original'],
    meta={'escopo': 'original'}
) }}

-- Original AC 9: a soma de `qtd_empresas` precisa ser igual à contagem de `bh_empresas`; o
-- `group by` não pode perder nem duplicar estabelecimentos.
with agg as (
  select coalesce(sum(qtd_empresas), 0) as total_agg from {{ ref('agg_empresas') }}
),

bh as (
  select count(*) as total_bh from {{ ref('bh_empresas') }}
)

select
  agg.total_agg,
  bh.total_bh
from agg
cross join bh
where agg.total_agg != bh.total_bh
