{{ config(
    severity='warn',
    store_failures=true,
    tags=['escopo_adicao', 'incremento_enriquecimento_ibge'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_ibge'}
) }}

-- incremento: enriquecimento_ibge. Avisa cada origem × tema cuja soma de `pct` (destinos listados
-- mais "Outros") sai de 100 ± 1 em `bridge_municipio_destino_compras`: sinal de ligação perdida
-- (destino ou origem fora de `dim_municipio`). warn: a REGIC é uma pesquisa por amostra de
-- informantes, arredondada, e não deve parar o build; sem `ibge/` a ponte é vazia e nada avisa.
select
  sk_municipio_origem,
  tema,
  sum(pct) as soma_pct
from {{ ref('bridge_municipio_destino_compras') }}
group by sk_municipio_origem, tema
having abs(sum(pct) - 100) > 1
