{{ config(
    severity='error',
    tags=['escopo_adicao', 'incremento_enriquecimento_bd'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_bd'}
) }}
-- incremento: enriquecimento_bd. Falha para cada par sem o par inverso na vizinhança conformada.
select
  a.sk_municipio,
  a.sk_municipio_vizinho
from {{ ref('bridge_municipio_vizinho') }} as a
where not exists (
  select 1
  from {{ ref('bridge_municipio_vizinho') }} as b
  where
    b.sk_municipio = a.sk_municipio_vizinho
    and b.sk_municipio_vizinho = a.sk_municipio
)
