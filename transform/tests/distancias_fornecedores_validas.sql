{{ config(
    severity='error',
    tags=['escopo_adicao'],
    meta={'escopo': 'adicao'}
) }}

-- ANA-04 AC 7: nenhuma distância negativa e distância 0 para fornecedor no próprio município do
-- caso (a distância de um ponto a si mesmo é nula). Retorna uma linha por violação.
select
  cnpj_completo,
  municipio,
  distancia_km
from {{ ref('mart_fornecedores_proximos') }}
where
  distancia_km < 0
  or (upper(municipio) = upper('{{ var("caso_municipio") }}') and uf = '{{ var("caso_uf") }}' and distancia_km != 0)
