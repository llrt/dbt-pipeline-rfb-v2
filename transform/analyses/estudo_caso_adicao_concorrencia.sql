{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- Adição (ANA-01): densidade de concorrência do CNAE do caso nos municípios da UF, do mais denso
-- ao menos denso; o município do caso aparece com seu ranking.
select
  municipio,
  populacao,
  ativos,
  inativos,
  ativos_por_10k_hab,
  ranking_uf
from {{ ref('mart_concorrencia_municipio') }}
where cnae_principal = '{{ var("caso_cnae_alvo") }}' and uf = '{{ var("caso_uf") }}'
order by ranking_uf nulls last, municipio
