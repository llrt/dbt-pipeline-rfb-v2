-- Município conformado: Base dos Dados (hierarquia IBGE, centroide) + população e PIB do ano de
-- referência. Uma linha por município IBGE (`id_municipio`), com o código RFB (4 dígitos) para
-- casar com os estabelecimentos. Base de `dim_municipio`.
--
-- Ano da população: var `ano_populacao`; senão o último ano disponível. O PIB usa sempre o último
-- ano disponível (a publicação do IBGE costuma ter defasagem maior que a da população).
{% set ano_var = var('ano_populacao', none) -%}
with municipios as (
  select * from {{ ref('stg_bd__municipios') }}
),

ano_populacao as (
  select coalesce({{ ano_var if ano_var is not none else 'null' }}::int, max(ano)) as ano
  from {{ ref('stg_bd__populacao') }}
),

populacao as (
  select
    pop.id_municipio,
    pop.ano,
    pop.populacao
  from {{ ref('stg_bd__populacao') }} as pop
  inner join ano_populacao on pop.ano = ano_populacao.ano
),

ano_pib as (
  select max(ano) as ano from {{ ref('stg_bd__pib') }}
),

pib as (
  select
    pib.id_municipio,
    pib.ano,
    pib.pib
  from {{ ref('stg_bd__pib') }} as pib
  inner join ano_pib on pib.ano = ano_pib.ano
)

select
  mun.id_municipio::integer as sk_municipio,
  mun.id_municipio as id_municipio_ibge,
  mun.id_municipio_rf as codigo_rfb,
  mun.nome as nome_municipio,
  mun.sigla_uf,
  mun.nome_uf,
  mun.nome_regiao,
  mun.id_mesorregiao,
  mun.nome_mesorregiao,
  mun.id_microrregiao,
  mun.nome_microrregiao,
  mun.id_regiao_intermediaria,
  mun.nome_regiao_intermediaria,
  mun.id_regiao_imediata,
  mun.nome_regiao_imediata,
  mun.latitude,
  mun.longitude,
  pop.ano as ano_populacao,
  pop.populacao,
  pib.ano as ano_pib,
  pib.pib
from municipios as mun
left join populacao as pop on mun.id_municipio = pop.id_municipio
left join pib on mun.id_municipio = pib.id_municipio
