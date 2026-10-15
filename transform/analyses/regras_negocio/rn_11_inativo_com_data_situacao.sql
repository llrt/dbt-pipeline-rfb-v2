{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-11 (docs/referencia/regras-negocio.md): o estabelecimento NULO, SUSPENSO, INAPTO ou BAIXADO tem a data
-- do evento da situação cadastral. Universo: estabelecimentos não ativos.
select
  'RN-11' as regra,
  coalesce(sit.rotulo, 'NÃO INFORMADO') as situacao,
  count(*) as avaliados,
  count(*) filter (where est.dat_situacao is null) as violacoes
from {{ ref('int_estabelecimentos__enriquecidos') }} as est
left join {{ ref('dominio_situacao_cadastral') }} as sit
  on est.situacao_codigo = sit.codigo
where est.situacao_codigo is distinct from 2
group by all
order by situacao
