{{ config(tags=['escopo_original'], meta={'escopo': 'original'}) }}

-- Notebook 4, pergunta 4 (última consulta): estabelecimentos ATIVOS da UF do caso que têm algum
-- dos `caso_cnaes_fornecedores` entre os CNAEs secundários, a partir da base granular `bh_empresas`.
{%- set cnaes = var('caso_cnaes_fornecedores') %}
select
  cnpj_completo,
  nome,
  municipio,
  uf,
  cnae_principal,
  cnaes_secundarios
from {{ ref('bh_empresas') }}
where
  situacao = 'ATIVA'
  and uf = '{{ var("caso_uf") }}'
  and ({% for c in cnaes %}cnaes_secundarios like '%{{ c }}%'{{ ' or ' if not loop.last }}{% endfor %})
order by municipio, cnpj_completo
