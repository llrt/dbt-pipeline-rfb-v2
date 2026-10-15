{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-01 (docs/referencia/regras-negocio.md): todo estabelecimento tem um CNAE fiscal principal, e ele existe
-- no domínio de CNAEs publicado pela RFB. Só contagens, por situação cadastral (ADR-0008).
with base as (
  select
    est.situacao_codigo,
    cnae.codigo is null as viola
  from {{ ref('int_estabelecimentos__enriquecidos') }} as est
  left join {{ ref('stg_rfb__cnaes') }} as cnae
    on est.cnae_principal = cnae.codigo
)

select
  'RN-01' as regra,
  coalesce(sit.rotulo, 'NÃO INFORMADO') as situacao,
  count(*) as avaliados,
  count(*) filter (where base.viola) as violacoes
from base
left join {{ ref('dominio_situacao_cadastral') }} as sit
  on base.situacao_codigo = sit.codigo
group by all
order by situacao
