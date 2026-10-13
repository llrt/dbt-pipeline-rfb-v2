{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-02 (docs/REGRAS_NEGOCIO.md): cada CNAE secundário existe no domínio de CNAEs da RFB. O
-- universo são as ocorrências de CNAE secundário (um estabelecimento pode ter várias).
with secundarios as (
  select
    situacao_codigo,
    unnest(cnaes_secundarios_lista) as cnae_secundario
  from {{ ref('int_estabelecimentos__enriquecidos') }}
),

base as (
  select
    sec.situacao_codigo,
    cnae.codigo is null as viola
  from secundarios as sec
  left join {{ ref('stg_rfb__cnaes') }} as cnae
    on sec.cnae_secundario = cnae.codigo
)

select
  'RN-02' as regra,
  coalesce(sit.rotulo, 'NÃO INFORMADO') as situacao,
  count(*) as avaliados,
  count(*) filter (where base.viola) as violacoes
from base
left join {{ ref('dominio_situacao_cadastral') }} as sit
  on base.situacao_codigo = sit.codigo
group by all
order by situacao
