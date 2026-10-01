-- incremento: enriquecimento_bd (ADR-0015). Relação de vizinhança entre municípios por
-- `sk_municipio`: ano mais recente da Base dos Dados, simétrica (cada par aparece nos dois
-- sentidos mesmo quando a fonte traz um só), sem autopares, sem duplicatas e restrita aos
-- municípios de `dim_municipio` (integridade referencial).
with ano_recente as (
  select max(ano) as ano from {{ ref('stg_bd__vizinhanca') }}
),

pares as (
  select
    viz.id_municipio_1 as id_a,
    viz.id_municipio_2 as id_b
  from {{ ref('stg_bd__vizinhanca') }} as viz
  inner join ano_recente on viz.ano = ano_recente.ano
  union
  select
    viz.id_municipio_2 as id_a,
    viz.id_municipio_1 as id_b
  from {{ ref('stg_bd__vizinhanca') }} as viz
  inner join ano_recente on viz.ano = ano_recente.ano
)

select
  mun_a.sk_municipio,
  mun_b.sk_municipio as sk_municipio_vizinho
from pares
inner join {{ ref('dim_municipio') }} as mun_a
  on pares.id_a = mun_a.id_municipio_ibge
inner join {{ ref('dim_municipio') }} as mun_b
  on pares.id_b = mun_b.id_municipio_ibge
where mun_a.sk_municipio != mun_b.sk_municipio
