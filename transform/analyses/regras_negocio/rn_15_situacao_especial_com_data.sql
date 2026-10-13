{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-15 (docs/REGRAS_NEGOCIO.md): situação especial e data da situação especial andam juntas: as
-- duas preenchidas ou as duas vazias. Universo: todos os estabelecimentos.
with base as (
  select
    situacao_codigo,
    (situacao_especial is null) != (dat_situacao_especial is null) as viola
  from {{ ref('stg_rfb__estabelecimentos') }}
)

select
  'RN-15' as regra,
  coalesce(sit.rotulo, 'NÃO INFORMADO') as situacao,
  count(*) as avaliados,
  count(*) filter (where base.viola) as violacoes
from base
left join {{ ref('dominio_situacao_cadastral') }} as sit
  on base.situacao_codigo = sit.codigo
group by all
order by situacao
