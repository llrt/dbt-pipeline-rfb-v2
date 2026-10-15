{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-21 (docs/referencia/regras-negocio.md): o capital social da empresa não é negativo. Universo: empresas do
-- arquivo Empresas com capital preenchido, pelo porte declarado.
select
  'RN-21' as regra,
  coalesce(por.rotulo, 'NÃO INFORMADO') as porte,
  count(*) as avaliados,
  count(*) filter (where emp.capital_social < 0) as violacoes
from {{ ref('stg_rfb__empresas') }} as emp
left join {{ ref('dominio_porte') }} as por
  on emp.porte_codigo = por.codigo
where emp.capital_social is not null
group by all
order by porte
