{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-18 (docs/REGRAS_NEGOCIO.md): todo estabelecimento tem a empresa (o mesmo CNPJ básico) no
-- arquivo Empresas do mês.
select
  'RN-18' as regra,
  coalesce(sit.rotulo, 'NÃO INFORMADO') as situacao,
  count(*) as avaliados,
  count(*) filter (where not est.tem_empresa) as violacoes
from {{ ref('int_estabelecimentos__enriquecidos') }} as est
left join {{ ref('dominio_situacao_cadastral') }} as sit
  on est.situacao_codigo = sit.codigo
group by all
order by situacao
