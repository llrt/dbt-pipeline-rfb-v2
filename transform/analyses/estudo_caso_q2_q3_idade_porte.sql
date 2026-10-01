{{ config(tags=['escopo_original'], meta={'escopo': 'original'}) }}

-- Notebook 4, perguntas 2 e 3 (respondidas juntas no original): idade média e distribuição por porte
-- das empresas ATIVAS do CNAE na localidade do caso. Fixtures: 1 MICRO, 3,9 anos.
select
  porte,
  avg(media_idade) as media_idade,
  sum(qtd_empresas) as qtd_empresas
from {{ ref('agg_empresas') }}
where
  cnae_principal = '{{ var("caso_cnae_alvo") }}'
  and municipio = '{{ var("caso_municipio") }}'
  and uf = '{{ var("caso_uf") }}'
  and situacao = 'ATIVA'
group by porte
order by porte
