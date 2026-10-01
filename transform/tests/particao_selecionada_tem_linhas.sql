{{ config(
    severity='error',
    tags=['escopo_adicao'],
    meta={'escopo': 'adicao'}
) }}

-- R1-21: `--vars 'mes_referencia: 2026-10'` sem partição geraria staging vazio e todos os
-- testes passariam. Falha se o mês selecionado (`filtro_mes_referencia`) não tiver linhas em
-- alguma fonte RFB principal.
select
  fonte,
  linhas
from (
  select
    'empresas' as fonte,
    count(*) as linhas
  from {{ source('rfb', 'empresas') }}
  where {{ filtro_mes_referencia(source('rfb', 'empresas')) }}
  union all
  select
    'estabelecimentos' as fonte,
    count(*) as linhas
  from {{ source('rfb', 'estabelecimentos') }}
  where {{ filtro_mes_referencia(source('rfb', 'estabelecimentos')) }}
  union all
  select
    'simples' as fonte,
    count(*) as linhas
  from {{ source('rfb', 'simples') }}
  where {{ filtro_mes_referencia(source('rfb', 'simples')) }}
  union all
  select
    'cnaes' as fonte,
    count(*) as linhas
  from {{ source('rfb', 'cnaes') }}
  where {{ filtro_mes_referencia(source('rfb', 'cnaes')) }}
  union all
  select
    'municipios' as fonte,
    count(*) as linhas
  from {{ source('rfb', 'municipios') }}
  where {{ filtro_mes_referencia(source('rfb', 'municipios')) }}
  union all
  select
    'naturezas' as fonte,
    count(*) as linhas
  from {{ source('rfb', 'naturezas') }}
  where {{ filtro_mes_referencia(source('rfb', 'naturezas')) }}
)
where linhas = 0
