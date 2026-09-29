{{ config(
    severity='warn',
    store_failures=true,
    tags=['escopo_adicao'],
    meta={'escopo': 'adicao'}
) }}

-- Original AC 11: estabelecimentos do mês que os inner joins do notebook 3 descartam de
-- `bh_empresas` (fixtures: 3 — K exterior, L CNAE sem par no BD, M município sem par no BD).
-- Um por linha, com o motivo; warn porque o descarte é a regra do original, não um erro.
with est as (
  select * from {{ ref('stg_rfb__estabelecimentos') }}
),

bh as (
  select cnpj_completo from {{ ref('bh_empresas') }}
)

select
  est.cnpj_completo,
  emp.cnpj_raiz is null as sem_empresa,
  nat.codigo is null as sem_natureza,
  cnae.subclasse is null as sem_cnae_bd,
  mun.id_municipio_rf is null as sem_municipio_bd
from est
left join {{ ref('stg_rfb__empresas') }} as emp
  on est.cnpj_raiz = emp.cnpj_raiz
left join {{ ref('stg_rfb__naturezas') }} as nat
  on emp.natureza_juridica_codigo = nat.codigo
left join {{ ref('stg_bd__cnaes') }} as cnae
  on est.cnae_principal = cnae.subclasse
left join {{ ref('stg_bd__municipios') }} as mun
  on est.municipio_rfb_codigo = lpad(mun.id_municipio_rf, 4, '0')
where not exists (
  select 1 from bh
  where bh.cnpj_completo = est.cnpj_completo
)
