-- incremento: enriquecimento_ibge
-- CEMPRE por município, todas as atividades (categoria Total 117897 da classificação 12762). Fica à
-- parte das classes (stg_ibge__cempre_municipio_classe) para nunca somar em dobro.
with

valores as (
  select
    d2c as variavel,
    v as valor,
    {{ texto_ou_nulo('d1c') }} as id_municipio,
    d3c::int as ano
  from {{ source('ibge', 'cempre_municipio_cnae') }}
  where d4c = '117897'
)

select
  id_municipio,
  ano,
  max(case when variavel = '706' then {{ valor_ibge('valor', 'bigint') }} end) as unidades_locais,
  max(case when variavel = '707' then {{ valor_ibge('valor', 'bigint') }} end) as pessoal_ocupado,
  max(case when variavel = '708' then {{ valor_ibge('valor', 'bigint') }} end) as pessoal_assalariado,
  max(case when variavel = '662' then {{ valor_ibge('valor', 'decimal(18, 3)') }} end)
    as salarios_mil_reais,
  coalesce(bool_or(trim(valor) = 'X'), false) as tem_sigilo
from valores
group by id_municipio, ano
