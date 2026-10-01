{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- Adição (ANA-03): aberturas, encerramentos e saldo por ano do CNAE do caso no município do caso.
select
  ano,
  aberturas,
  encerramentos,
  saldo
from {{ ref('mart_dinamica_mercado') }}
where
  cnae_principal = '{{ var("caso_cnae_alvo") }}'
  and upper(municipio) = '{{ var("caso_municipio") }}'
  and uf = '{{ var("caso_uf") }}'
order by ano
