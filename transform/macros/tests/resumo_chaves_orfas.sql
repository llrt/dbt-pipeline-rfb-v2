{#- R3-18: chaves de `fct_resumo_mensal` sem par nas dimensões, uma linha por (mês, chave).
    `somente_mes_processado`: só a partição do mês do staging (teste `error`); sem ele, todas as
    partições em disco (teste `warn`). `relationships` genérico não aceita `ref` no `where`. -#}
{% macro resumo_chaves_orfas(somente_mes_processado) %}
{%- set chaves = [
    ('sk_municipio', 'dim_municipio', 'sk_municipio'),
    ('sk_cnae', 'dim_cnae', 'sk_cnae'),
    ('sk_porte', 'dim_porte', 'sk_porte'),
    ('sk_situacao_cadastral', 'dim_situacao_cadastral', 'sk_situacao_cadastral'),
    ('sk_mes_referencia', 'dim_data', 'sk_data'),
] -%}
with resumo as (
  select *
  from {{ ref('fct_resumo_mensal') }}
  {% if somente_mes_processado -%}
  where mes_referencia = (select max(_mes_referencia) from {{ ref('stg_rfb__estabelecimentos') }})
  {%- endif %}
)

{% for chave, dimensao, coluna in chaves %}
select res.mes_referencia, '{{ chave }}' as chave, count(*) as linhas
from resumo as res
left join {{ ref(dimensao) }} as dim on res.{{ chave }} = dim.{{ coluna }}
where dim.{{ coluna }} is null
group by all
{% if not loop.last %}union all{% endif %}
{% endfor %}
{% endmacro %}
