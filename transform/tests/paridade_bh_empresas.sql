{{ config(
    severity='error',
    tags=['escopo_adicao'],
    meta={'escopo': 'adicao'}
) }}

-- Original AC 10 (ADR-0005): `bh_empresas` não pode diferir, linha a linha (com multiplicidade),
-- da tradução literal do SQL do notebook 3 sobre os mesmos dados raw. Diferença zero nos dois
-- sentidos.
-- Compara `(cnpj_completo, hash da linha)` com EXCEPT ALL em vez das 15 colunas: mesmo resultado,
-- ~3,4x mais rápido em dados reais (R2-12). As duas relações têm as mesmas colunas na mesma ordem
-- (contrato de `bh_empresas`), então `hash(*columns(*))` cobre todas. Cada falha traz o lado e o
-- `cnpj_completo`; para ver as colunas, consulte as duas relações por esse CNPJ.
with bh as (
  select
    cnpj_completo,
    hash(*columns(*)) as hash_linha
  from {{ ref('bh_empresas') }}
),

original as (
  select
    cnpj_completo,
    hash(*columns(*)) as hash_linha
  from {{ ref('audit__bh_empresas_sql_original') }}
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
  cnpj_completo,
  hash_linha
from somente_bh
union all
select
  'somente_sql_original' as lado,
  cnpj_completo,
  hash_linha
from somente_original
