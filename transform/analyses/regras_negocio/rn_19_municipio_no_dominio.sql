{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-19 (docs/referencia/regras-negocio.md): o código de município do estabelecimento existe no domínio de
-- municípios publicado pela RFB (não no da Base dos Dados).
with base as (
  select
    est.situacao_codigo,
    mun.codigo is null as viola
  from {{ ref('int_estabelecimentos__enriquecidos') }} as est
  left join {{ ref('stg_rfb__municipios') }} as mun
    on est.municipio_rfb_codigo = mun.codigo
)

select
  'RN-19' as regra,
  coalesce(sit.rotulo, 'NÃO INFORMADO') as situacao,
  count(*) as avaliados,
  count(*) filter (where base.viola) as violacoes
from base
left join {{ ref('dominio_situacao_cadastral') }} as sit
  on base.situacao_codigo = sit.codigo
group by all
order by situacao
