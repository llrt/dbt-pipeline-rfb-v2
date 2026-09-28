select
  {{ lpad_codigo('subclasse', 7) }} as subclasse,
  {{ texto_ou_nulo('descricao_subclasse') }} as descricao_subclasse,
  {{ lpad_codigo('classe', 5) }} as classe,
  {{ texto_ou_nulo('descricao_classe') }} as descricao_classe,
  {{ lpad_codigo('grupo', 3) }} as grupo,
  {{ texto_ou_nulo('descricao_grupo') }} as descricao_grupo,
  {{ lpad_codigo('divisao', 2) }} as divisao,
  {{ texto_ou_nulo('descricao_divisao') }} as descricao_divisao,
  {{ texto_ou_nulo('secao') }} as secao,
  {{ texto_ou_nulo('descricao_secao') }} as descricao_secao
from {{ source('basedosdados', 'cnae_2') }}
