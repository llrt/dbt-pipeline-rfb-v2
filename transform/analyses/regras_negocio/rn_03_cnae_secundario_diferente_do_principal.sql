{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-03 (docs/referencia/regras-negocio.md): nenhum CNAE secundário repete o CNAE fiscal principal do mesmo
-- estabelecimento. O universo são as ocorrências de CNAE secundário.
with base as (
  select
    situacao_codigo,
    cnae_principal,
    unnest(cnaes_secundarios_lista) as cnae_secundario
  from {{ ref('int_estabelecimentos__enriquecidos') }}
)

select
  'RN-03' as regra,
  coalesce(sit.rotulo, 'NÃO INFORMADO') as situacao,
  count(*) as avaliados,
  count(*) filter (where base.cnae_secundario = base.cnae_principal) as violacoes
from base
left join {{ ref('dominio_situacao_cadastral') }} as sit
  on base.situacao_codigo = sit.codigo
group by all
order by situacao
