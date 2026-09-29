{{ config(
    materialized='ephemeral',
    meta={'escopo': 'adicao'},
    tags=['escopo_adicao']
) }}

-- SQL do notebook 3 (`bh_empresas`) traduzido literalmente para DuckDB, lendo as fontes RAW (não o
-- staging), para o teste `paridade_bh_empresas` (ADR-0005). Emula a leitura do original
-- (`spark.read.csv(..., inferSchema=True)`): os códigos que o Spark inferiu como inteiro entram
-- com `try_cast(... as bigint)` antes dos joins e dos `case`; o resto fica texto como veio.
-- Traduções: `nvl` -> `coalesce`; `lpad(x, n, 0)` sobre inteiro -> `lpad(x::varchar, n, '0')`;
-- `datediff(fim, ini)` -> `datediff('day', ini, fim)`; `to_date(x, 'yyyyMMdd')` -> `try_strptime`;
-- `now()` -> `data_referencia()` (ADR-0004).
with empresas as (
  select
    try_cast(cnpj_raiz as bigint) as cnpj_raiz,
    razao_social,
    try_cast(natureza_jur as bigint) as natureza_jur,
    try_cast(porte as bigint) as porte
  from {{ source('rfb', 'empresas') }}
  where {{ filtro_mes_referencia(source('rfb', 'empresas')) }}
),

estabelecimentos as (
  select
    try_cast(cnpj_raiz as bigint) as cnpj_raiz,
    try_cast(cnpj_ordem as bigint) as cnpj_ordem,
    try_cast(cnpj_dv as bigint) as cnpj_dv,
    nome_fantasia,
    try_cast(situacao as bigint) as situacao,
    dat_inicio_atividade,
    try_cast(cnae_principal as bigint) as cnae_principal,
    cnaes_secundarios,
    try_cast(municipio as bigint) as municipio
  from {{ source('rfb', 'estabelecimentos') }}
  where {{ filtro_mes_referencia(source('rfb', 'estabelecimentos')) }}
),

natureza_juridica as (
  select
    try_cast(codigo as bigint) as codigo,
    descricao
  from {{ source('rfb', 'naturezas') }}
  where {{ filtro_mes_referencia(source('rfb', 'naturezas')) }}
),

cnae_bd as (
  select
    try_cast(subclasse as bigint) as subclasse,
    descricao_subclasse,
    descricao_grupo
  from {{ source('basedosdados', 'cnae_2') }}
),

municipio_bd as (
  select
    try_cast(id_municipio_rf as bigint) as id_municipio_rf,
    nome,
    nome_microrregiao,
    nome_mesorregiao,
    sigla_uf
  from {{ source('basedosdados', 'municipio') }}
),

sql_original as (
  select
    lpad(est.cnpj_raiz::varchar, 8, '0') as cnpj_raiz,
    concat(
      lpad(est.cnpj_raiz::varchar, 8, '0'),
      lpad(est.cnpj_ordem::varchar, 4, '0'),
      lpad(est.cnpj_dv::varchar, 2, '0')
    ) as cnpj_completo,
    upper(coalesce(est.nome_fantasia, emp.razao_social)) as nome,
    upper(nat_jur.descricao) as natureza_juridica,
    case emp.porte
      when 0 then 'N/A'
      when 1 then 'MICRO'
      when 3 then 'PEQUENA'
      when 5 then 'DEMAIS'
    end as porte,
    est.cnae_principal,
    upper(cnae_princ.descricao_subclasse) as desc_cnae_principal,
    upper(cnae_princ.descricao_grupo) as grupo_cnae_principal,
    est.cnaes_secundarios,
    upper(mun.nome) as municipio,
    upper(mun.nome_microrregiao) as microrregiao_municipio,
    upper(mun.nome_mesorregiao) as mesorregiao_municipio,
    upper(mun.sigla_uf) as uf,
    case est.situacao
      when 2 then 'ATIVA'
      else 'INATIVA'
    end as situacao,
    case est.situacao
      when 2
        then round(
          datediff(
            'day', try_strptime(est.dat_inicio_atividade, '%Y%m%d')::date, {{ data_referencia() }}
          ) / 365.25,
          1
        )
    end as idade_atual
  from empresas as emp
  inner join estabelecimentos as est on emp.cnpj_raiz = est.cnpj_raiz
  inner join natureza_juridica as nat_jur on nat_jur.codigo = emp.natureza_jur  -- noqa: ST09
  inner join cnae_bd as cnae_princ on cnae_princ.subclasse = est.cnae_principal
  inner join municipio_bd as mun on mun.id_municipio_rf = est.municipio
)

-- Alinhamento de tipo, não de regra: o Spark inferiu `CNAE_principal` como inteiro (`0111301`
-- saía `111301`), mas o catálogo do notebook 3 o declara texto de 7 dígitos, que é o contrato de
-- `bh_empresas`. Todas as outras colunas saem exatamente como no SQL original.
select
  cnpj_raiz,
  cnpj_completo,
  nome,
  natureza_juridica,
  porte,
  lpad(cnae_principal::varchar, 7, '0') as cnae_principal,
  desc_cnae_principal,
  grupo_cnae_principal,
  cnaes_secundarios,
  municipio,
  microrregiao_municipio,
  mesorregiao_municipio,
  uf,
  situacao,
  idade_atual
from sql_original
