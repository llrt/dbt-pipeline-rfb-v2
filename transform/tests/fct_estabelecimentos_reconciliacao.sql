{{ config(
    severity='error',
    tags=['escopo_adicao'],
    meta={'escopo': 'adicao'}
) }}

-- CORE-01: a fato não descarta nem duplica estabelecimentos (mesma contagem do staging do mês) e
-- usa a chave -1 exatamente onde falta par na dimensão (flags `tem_*` da camada intermediate).
-- Retorna uma linha por violação.
with fato as (
  select
    count(*) as linhas,
    count(*) filter (where sk_municipio = -1) as sem_municipio,
    count(*) filter (where sk_cnae = -1) as sem_cnae,
    count(*) filter (where sk_natureza_juridica = -1) as sem_natureza
  from {{ ref('fct_estabelecimentos') }}
),

staging as (
  select count(*) as linhas from {{ ref('stg_rfb__estabelecimentos') }}
),

flags as (
  select
    count(*) filter (where not tem_municipio_bd) as sem_municipio,
    count(*) filter (where not tem_cnae_bd) as sem_cnae,
    count(*) filter (where not tem_natureza) as sem_natureza
  from {{ ref('int_estabelecimentos__enriquecidos') }}
)

select
  'linhas da fato != linhas do staging' as violacao,
  fato.linhas as na_fato,
  staging.linhas as esperado
from fato
cross join staging
where fato.linhas != staging.linhas

union all

select
  'sk_municipio = -1 != estabelecimentos sem município no BD' as violacao,
  fato.sem_municipio as na_fato,
  flags.sem_municipio as esperado
from fato
cross join flags
where fato.sem_municipio != flags.sem_municipio

union all

select
  'sk_cnae = -1 != estabelecimentos sem CNAE no BD' as violacao,
  fato.sem_cnae as na_fato,
  flags.sem_cnae as esperado
from fato
cross join flags
where fato.sem_cnae != flags.sem_cnae

union all

select
  'sk_natureza_juridica = -1 != estabelecimentos sem natureza' as violacao,
  fato.sem_natureza as na_fato,
  flags.sem_natureza as esperado
from fato
cross join flags
where fato.sem_natureza != flags.sem_natureza
