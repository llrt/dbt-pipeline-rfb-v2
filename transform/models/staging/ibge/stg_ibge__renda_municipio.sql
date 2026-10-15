-- incremento: enriquecimento_ibge
-- Censo 2022 (SIDRA 10295): moradores e rendimento domiciliar per capita médio e mediano, por município,
-- nos totais de sexo (6794), cor ou raça (95251) e grupo de idade (95253).
with

valores as (
  select
    d2c as variavel,
    v as valor,
    {{ texto_ou_nulo('d1c') }} as id_municipio,
    d3c::int as ano
  from {{ source('ibge', 'renda_censo_2022_municipio') }}
  where d4c = '6794' and d5c = '95251' and d6c = '95253'
)

select
  id_municipio,
  ano,
  max(case when variavel = '13604' then {{ valor_ibge('valor', 'bigint') }} end) as moradores,
  max(case when variavel = '13431' then {{ valor_ibge('valor', 'decimal(12, 2)') }} end)
    as renda_per_capita_media,
  max(case when variavel = '13534' then {{ valor_ibge('valor', 'decimal(12, 2)') }} end)
    as renda_per_capita_mediana
from valores
group by id_municipio, ano
