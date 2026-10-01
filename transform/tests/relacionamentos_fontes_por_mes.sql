{{ config(
    severity='error',
    tags=['escopo_original'],
    meta={'escopo': 'original'}
) }}

-- R1-22: os checks `relationships` do original (natureza, CNAE principal e município de
-- empresas/estabelecimentos -> domínios) comparados DENTRO de cada `_mes_referencia`. O
-- `relationships` genérico cruzaria todos os meses retidos no raw e deixaria passar um código
-- presente só no domínio de outro mês.
select
  'empresas.natureza_jur -> naturezas' as relacionamento,
  e._mes_referencia,
  e.natureza_jur as codigo
from {{ source('rfb', 'empresas') }} as e
left join {{ source('rfb', 'naturezas') }} as d
  on e.natureza_jur = d.codigo and e._mes_referencia = d._mes_referencia
where e.natureza_jur is not null and d.codigo is null

union all

select
  'estabelecimentos.cnae_principal -> cnaes' as relacionamento,
  e._mes_referencia,
  e.cnae_principal as codigo
from {{ source('rfb', 'estabelecimentos') }} as e
left join {{ source('rfb', 'cnaes') }} as d
  on e.cnae_principal = d.codigo and e._mes_referencia = d._mes_referencia
where e.cnae_principal is not null and d.codigo is null

union all

select
  'estabelecimentos.municipio -> municipios' as relacionamento,
  e._mes_referencia,
  e.municipio as codigo
from {{ source('rfb', 'estabelecimentos') }} as e
left join {{ source('rfb', 'municipios') }} as d
  on e.municipio = d.codigo and e._mes_referencia = d._mes_referencia
where e.municipio is not null and d.codigo is null
