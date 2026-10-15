{{ config(
    severity='error',
    tags=['escopo_adicao', 'incremento_enriquecimento_ibge'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_ibge'}
) }}

-- incremento: enriquecimento_ibge. Falha se, num município e ano, a soma das unidades locais das
-- classes CNAE passar do Total do CEMPRE: sinal de que o Total (ou um grupo/divisão) entrou junto com
-- as classes e somaria em dobro. Unidades locais não são sigilosas, então a soma é confiável.
with classes as (
  select
    id_municipio,
    ano,
    sum(unidades_locais) as unidades_classes
  from {{ ref('stg_ibge__cempre_municipio_classe') }}
  group by id_municipio, ano
)

select
  classes.id_municipio,
  classes.ano,
  classes.unidades_classes,
  total.unidades_locais as unidades_total
from classes
left join {{ ref('stg_ibge__cempre_municipio_total') }} as total
  on classes.id_municipio = total.id_municipio and classes.ano = total.ano
where total.unidades_locais is null or classes.unidades_classes > total.unidades_locais
