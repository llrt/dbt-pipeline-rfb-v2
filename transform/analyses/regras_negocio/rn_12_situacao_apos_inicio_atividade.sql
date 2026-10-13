{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-12 (docs/REGRAS_NEGOCIO.md): a data da situação cadastral não é anterior à data de início de
-- atividade. Universo: estabelecimentos com as duas datas.
select
  'RN-12' as regra,
  coalesce(sit.rotulo, 'NÃO INFORMADO') as situacao,
  count(*) as avaliados,
  count(*) filter (where est.dat_situacao < est.dat_inicio_atividade) as violacoes
from {{ ref('int_estabelecimentos__enriquecidos') }} as est
left join {{ ref('dominio_situacao_cadastral') }} as sit
  on est.situacao_codigo = sit.codigo
where est.dat_situacao is not null and est.dat_inicio_atividade is not null
group by all
order by situacao
