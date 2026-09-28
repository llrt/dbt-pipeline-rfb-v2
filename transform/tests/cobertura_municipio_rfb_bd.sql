{{ config(
    severity='error',
    tags=['escopo_original'],
    meta={'escopo': 'original'}
) }}

-- Reproduz o check do notebook 2.1.2 (qualidade dos domínios): códigos de município RFB sem
-- par na Base dos Dados. Compara com lpad(4) dos dois lados porque `id_municipio_rf` pode vir
-- sem zeros à esquerda no BD, enquanto o domínio RFB sempre tem 4 dígitos. Exclui os casos
-- documentados no seed `excecoes_conhecidas_municipio` (EXTERIOR e municípios criados após a
-- base BD); qualquer outro código sem par é uma falha (severidade error).
select
  m.codigo,
  m.descricao
from {{ source('rfb', 'municipios') }} as m
left join {{ source('basedosdados', 'municipio') }} as bd
  on lpad(m.codigo, 4, '0') = lpad(bd.id_municipio_rf, 4, '0')
left join {{ ref('excecoes_conhecidas_municipio') }} as excecao
  on lpad(m.codigo, 4, '0') = lpad(excecao.codigo::varchar, 4, '0')
where
  bd.id_municipio_rf is null
  and excecao.codigo is null
