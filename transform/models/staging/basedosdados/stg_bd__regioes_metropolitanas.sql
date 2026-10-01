-- incremento: enriquecimento_bd (ADR-0015)
-- Uma região por município. A fonte pode listar o mesmo município em mais de uma região (ex.: RM e
-- RIDE/aglomeração); fica a de tipo `RM` e, no empate, a de menor nome (determinístico). A
-- `geometria` (WKT grande) não é usada e é descartada aqui.
with tipada as (
  select
    {{ texto_ou_nulo('id_municipio') }} as id_municipio,
    {{ texto_ou_nulo('sigla_uf') }} as sigla_uf,
    {{ texto_ou_nulo('nome_regiao_metropolitana') }} as nome_regiao_metropolitana,
    {{ texto_ou_nulo('tipo') }} as tipo,
    {{ texto_ou_nulo('subcategoria_metropolitana') }} as subcategoria_metropolitana,
    {{ texto_ou_nulo('legislacao') }} as legislacao,
    try_cast({{ texto_ou_nulo('data_legislacao') }} as date) as data_legislacao
  from {{ source('basedosdados', 'regiao_metropolitana_2017') }}
)

select * exclude (ordem)
from (
  select
    *,
    row_number() over (
      partition by id_municipio
      order by (tipo = 'RM') desc nulls last, nome_regiao_metropolitana
    ) as ordem
  from tipada
) as ordenada
where ordem = 1
