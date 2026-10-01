{{ config(
    severity='error',
    tags=['escopo_adicao', 'incremento_enriquecimento_bd'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_bd'}
) }}
-- incremento: enriquecimento_bd. Falha se um município com ativo do CNAE nos vizinhos ou na região
-- metropolitana ficar sem linha (P23: grão com vazios de mercado, conferido contra as fontes), se
-- `tem_estabelecimento_local` for false com ativos/inativos > 0 ou com CNAE/município -1 (vazio de
-- desconhecido não existe), se a região metropolitana tiver menos ativos/inativos que o
-- próprio município (ela o inclui) ou se um indicador por mil domicílios vier com ativos > 0 e valor 0.
with esperados as (
  select
    bas.sk_cnae,
    bri.sk_municipio
  from {{ ref('mart_concorrencia_municipio') }} as bas
  inner join {{ ref('bridge_municipio_vizinho') }} as bri
    on bas.sk_municipio = bri.sk_municipio_vizinho
  where bas.ativos > 0 and bas.sk_cnae <> -1 and bri.sk_municipio <> -1
  union
  select
    bas.sk_cnae,
    mun.sk_municipio
  from {{ ref('mart_concorrencia_municipio') }} as bas
  inner join {{ ref('dim_municipio') }} as mun_bas
    on bas.sk_municipio = mun_bas.sk_municipio
  inner join {{ ref('dim_municipio') }} as mun
    on mun_bas.nome_regiao_metropolitana = mun.nome_regiao_metropolitana
  where
    bas.ativos > 0
    and bas.sk_cnae <> -1
    and mun.sk_municipio <> -1
    and mun_bas.nome_regiao_metropolitana not in ('NÃO PERTENCE', 'NÃO INFORMADO')
  union
  select
    sk_cnae,
    sk_municipio
  from {{ ref('mart_concorrencia_municipio') }}
)

select
  esp.sk_cnae,
  esp.sk_municipio
from esperados as esp
left join {{ ref('mart_concorrencia_area_mercado') }} as mart
  on esp.sk_cnae = mart.sk_cnae and esp.sk_municipio = mart.sk_municipio
where mart.sk_cnae is null

union all

select
  sk_cnae,
  sk_municipio
from {{ ref('mart_concorrencia_area_mercado') }}
where
  (not tem_estabelecimento_local and (ativos > 0 or inativos > 0 or sk_cnae = -1 or sk_municipio = -1))
  or ativos_regiao_metropolitana < ativos
  or inativos_regiao_metropolitana < inativos
  or (ativos > 0 and ativos_por_mil_domicilios = 0)
