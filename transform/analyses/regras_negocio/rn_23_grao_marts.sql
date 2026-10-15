{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-23 (docs/referencia/regras-negocio.md): grãos declarados e sem teste (RDIC-09) nos marts do gold. Por
-- tabela: avaliados = linhas; violações = linhas excedentes (linhas − combinações distintas do grão).
with agg_empresas as (
  select
    municipio,
    microrregiao_municipio,
    mesorregiao_municipio,
    uf,
    cnae_principal,
    desc_cnae_principal,
    grupo_cnae_principal,
    natureza_juridica,
    porte,
    situacao,
    count(*) as linhas
  from {{ ref('agg_empresas') }}
  group by all
),

dinamica as (
  select
    ano,
    sk_cnae,
    sk_municipio,
    count(*) as linhas
  from {{ ref('mart_dinamica_mercado') }}
  group by all
),

sobrevivencia as (
  select
    ano_coorte,
    sk_cnae,
    sk_porte,
    uf,
    count(*) as linhas
  from {{ ref('mart_sobrevivencia_coorte') }}
  group by all
)

select
  'RN-23' as regra,
  'agg_empresas' as tabela,
  coalesce(sum(linhas), 0) as avaliados,
  coalesce(sum(linhas - 1), 0) as violacoes
from agg_empresas

union all

select
  'RN-23' as regra,
  'mart_dinamica_mercado' as tabela,
  coalesce(sum(linhas), 0) as avaliados,
  coalesce(sum(linhas - 1), 0) as violacoes
from dinamica

union all

select
  'RN-23' as regra,
  'mart_sobrevivencia_coorte' as tabela,
  coalesce(sum(linhas), 0) as avaliados,
  coalesce(sum(linhas - 1), 0) as violacoes
from sobrevivencia
