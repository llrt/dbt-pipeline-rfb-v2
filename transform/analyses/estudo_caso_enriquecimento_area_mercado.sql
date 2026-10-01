{{ config(
    tags=['escopo_adicao', 'incremento_enriquecimento_bd'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_bd'}
) }}

-- Incremento enriquecimento_bd (ENR-03): área de mercado do CNAE do caso no município do caso
-- (município, vizinhos e região metropolitana), com os indicadores por mil domicílios e por km².
select
  municipio,
  nome_regiao_metropolitana,
  domicilios_2022,
  area_km2,
  ativos,
  inativos,
  qtd_vizinhos,
  ativos_vizinhos,
  inativos_vizinhos,
  ativos_regiao_metropolitana,
  inativos_regiao_metropolitana,
  ativos_por_mil_domicilios,
  ativos_por_km2,
  ativos_area_por_mil_domicilios,
  ativos_area_por_km2
from {{ ref('mart_concorrencia_area_mercado') }}
where
  cnae_principal = '{{ var("caso_cnae_alvo") }}'
  and upper(municipio) = '{{ var("caso_municipio") }}'
  and uf = '{{ var("caso_uf") }}'
