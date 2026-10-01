{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- Adição (ANA-04): fornecedores ativos dentro de `raio_fornecedores_km` do município do caso, do
-- mais próximo ao mais distante (distância haversine entre centroides). Fixtures: F e H.
select
  cnpj_completo,
  nome,
  municipio,
  uf,
  cnae_fornecido,
  via,
  distancia_km
from {{ ref('mart_fornecedores_proximos') }}
order by distancia_km, cnpj_completo
