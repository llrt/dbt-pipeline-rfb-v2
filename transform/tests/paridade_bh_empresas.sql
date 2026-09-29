{{ config(
    severity='error',
    tags=['escopo_adicao'],
    meta={'escopo': 'adicao'}
) }}

-- Original AC 10 (ADR-0005): `bh_empresas` não pode diferir, linha a linha (com multiplicidade),
-- da tradução literal do SQL do notebook 3 sobre os mesmos dados raw. Diferença zero nos dois
-- sentidos.
with bh as (
  select * from {{ ref('bh_empresas') }}
),

original as (
  select * from {{ ref('paridade__bh_empresas_sql_original') }}
),

somente_bh as (
  select * from bh
  except all
  select * from original
),

somente_original as (
  select * from original
  except all
  select * from bh
)

select
  'somente_bh_empresas' as lado,
  *
from somente_bh
union all
select
  'somente_sql_original' as lado,
  *
from somente_original
