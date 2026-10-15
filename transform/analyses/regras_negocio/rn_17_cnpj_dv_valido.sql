{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-17 (docs/referencia/regras-negocio.md): os dígitos verificadores do CNPJ conferem pelo módulo 11, nos
-- formatos numérico e alfanumérico (macro `cnpj_dv_invalidos`, a mesma do teste `cnpj_dv_valido`).
with invalidos as (
  {{ cnpj_dv_invalidos(ref('int_estabelecimentos__enriquecidos'), 'cnpj_completo') }}
),

cnpjs_invalidos as (
  select distinct cnpj
  from invalidos
),

base as (
  select
    est.situacao_codigo,
    inv.cnpj is not null as viola
  from {{ ref('int_estabelecimentos__enriquecidos') }} as est
  left join cnpjs_invalidos as inv
    on est.cnpj_completo = inv.cnpj
)

select
  'RN-17' as regra,
  coalesce(sit.rotulo, 'NÃO INFORMADO') as situacao,
  count(*) as avaliados,
  count(*) filter (where base.viola) as violacoes
from base
left join {{ ref('dominio_situacao_cadastral') }} as sit
  on base.situacao_codigo = sit.codigo
group by all
order by situacao
