{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-04 (docs/referencia/regras-negocio.md): a lista de CNAEs secundários de um estabelecimento não repete
-- código. O universo são os estabelecimentos com ao menos um CNAE secundário.
with base as (
  select
    situacao_codigo,
    len(cnaes_secundarios_lista) != len(list_distinct(cnaes_secundarios_lista)) as viola
  from {{ ref('int_estabelecimentos__enriquecidos') }}
  where len(cnaes_secundarios_lista) > 0
)

select
  'RN-04' as regra,
  coalesce(sit.rotulo, 'NÃO INFORMADO') as situacao,
  count(*) as avaliados,
  count(*) filter (where base.viola) as violacoes
from base
left join {{ ref('dominio_situacao_cadastral') }} as sit
  on base.situacao_codigo = sit.codigo
group by all
order by situacao
