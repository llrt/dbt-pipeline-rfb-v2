{{ config(tags=['escopo_original'], meta={'escopo': 'original'}) }}

-- Notebook 4, pergunta 1: quantas empresas concorrentes há no CNAE e na localidade do caso?
-- Parametrizada pelas vars `caso_cnae_alvo`, `caso_municipio` (maiúsculas, como em `agg_empresas`) e
-- `caso_uf`. Fixtures: 1 ATIVA (MICRO) e 4 INATIVAS.
select *
from {{ ref('agg_empresas') }}
where
  cnae_principal = '{{ var("caso_cnae_alvo") }}'
  and municipio = '{{ var("caso_municipio") }}'
  and uf = '{{ var("caso_uf") }}'
order by situacao, porte
