{{ config(
    severity='warn',
    store_failures=true,
    tags=['escopo_original'],
    meta={'escopo': 'original'}
) }}

-- Staging AC 6 ("exatamente os listados no seed"): uma exceção do seed que passou a ter par na
-- Base dos Dados está obsoleta e deve sair de `excecoes_conhecidas_municipio`.
select
  excecao.codigo,
  excecao.descricao
from {{ ref('excecoes_conhecidas_municipio') }} as excecao
inner join {{ source('basedosdados', 'municipio') }} as bd
  on lpad(excecao.codigo::varchar, 4, '0') = lpad(bd.id_municipio_rf, 4, '0')
