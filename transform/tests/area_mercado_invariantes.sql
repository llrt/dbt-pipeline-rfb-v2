{{ config(
    severity='error',
    tags=['escopo_adicao', 'incremento_enriquecimento_bd'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_bd'}
) }}
-- incremento: enriquecimento_bd. Falha se a região metropolitana tiver menos ativos/inativos que o
-- próprio município (ela o inclui) ou se um indicador por mil domicílios vier com ativos > 0 e valor 0.
select
  sk_cnae,
  sk_municipio
from {{ ref('mart_concorrencia_area_mercado') }}
where
  ativos_regiao_metropolitana < ativos
  or inativos_regiao_metropolitana < inativos
  or (ativos > 0 and ativos_por_mil_domicilios = 0)
