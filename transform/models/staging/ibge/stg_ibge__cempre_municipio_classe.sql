-- incremento: enriquecimento_ibge
-- CEMPRE por município × classe CNAE (nível 4). O Total (117897) fica em stg_ibge__cempre_municipio_total:
-- só entram categorias cujo nome começa por um código de classe `NN.NN-N`.
with

classes as (
  select
    d4c as id_categoria_sidra,
    replace(replace(split_part(d4n, ' ', 1), '.', ''), '-', '') as classe_cnae,
    trim(substr(d4n, length(split_part(d4n, ' ', 1)) + 2)) as nome_classe_cnae
  from {{ source('ibge', 'cempre_categorias_cnae') }}
  where regexp_matches(d4n, '^\d{2}\.\d{2}-\d ')
),

valores as (
  select
    d4c as id_categoria_sidra,
    d2c as variavel,
    v as valor,
    {{ texto_ou_nulo('d1c') }} as id_municipio,
    d3c::int as ano
  from {{ source('ibge', 'cempre_municipio_cnae') }}
)

select
  valores.id_municipio,
  valores.ano,
  classes.classe_cnae,
  classes.nome_classe_cnae,
  valores.id_categoria_sidra,
  max(case when valores.variavel = '706' then {{ valor_ibge('valores.valor', 'bigint') }} end)
    as unidades_locais,
  max(case when valores.variavel = '707' then {{ valor_ibge('valores.valor', 'bigint') }} end)
    as pessoal_ocupado,
  max(case when valores.variavel = '708' then {{ valor_ibge('valores.valor', 'bigint') }} end)
    as pessoal_assalariado,
  max(
    case when valores.variavel = '662' then {{ valor_ibge('valores.valor', 'decimal(18, 3)') }} end
  ) as salarios_mil_reais,
  coalesce(bool_or(trim(valores.valor) = 'X'), false) as tem_sigilo
from valores
inner join classes on valores.id_categoria_sidra = classes.id_categoria_sidra
group by valores.id_municipio, valores.ano, classes.classe_cnae, classes.nome_classe_cnae, valores.id_categoria_sidra
