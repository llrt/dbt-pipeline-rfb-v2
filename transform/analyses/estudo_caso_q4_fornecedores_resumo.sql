{{ config(tags=['escopo_original'], meta={'escopo': 'original'}) }}

-- Notebook 4, pergunta 4: empresas ATIVAS potencialmente fornecedoras, em buscas de abrangência
-- crescente. As três primeiras usam o primeiro CNAE de `caso_cnaes_fornecedores` (fabricante) como
-- CNAE principal em `agg_empresas`; a quarta, os demais (atacadistas) na mesorregião; as duas
-- últimas incluem os CNAEs secundários (`bh_empresas.cnaes_secundarios`) na mesorregião e na UF.
-- `ordem` preserva a sequência do notebook.
{%- set cnaes = var('caso_cnaes_fornecedores') %}
{%- set fabricante = cnaes[0] %}
{%- set atacadistas = cnaes[1:] %}
with caso as (
  select
    upper(nome_microrregiao) as microrregiao,
    upper(nome_mesorregiao) as mesorregiao
  from {{ ref('dim_municipio') }}
  where upper(nome_municipio) = '{{ var("caso_municipio") }}' and sigla_uf = '{{ var("caso_uf") }}'
),

secundarios as (
  select
    cnpj_completo,
    mesorregiao_municipio,
    uf
  from {{ ref('bh_empresas') }}
  where
    situacao = 'ATIVA'
    and ({% for c in cnaes %}cnaes_secundarios like '%{{ c }}%'{{ ' or ' if not loop.last }}{% endfor %})
)

select
  1 as ordem,
  'fabricante (CNAE principal) no município' as busca,
  coalesce(sum(qtd_empresas), 0)::bigint as qtd_empresas
from {{ ref('agg_empresas') }}
where
  cnae_principal = '{{ fabricante }}' and situacao = 'ATIVA'
  and municipio = '{{ var("caso_municipio") }}' and uf = '{{ var("caso_uf") }}'

union all

select
  2 as ordem,
  'fabricante (CNAE principal) na microrregião' as busca,
  coalesce(sum(qtd_empresas), 0)::bigint as qtd_empresas
from {{ ref('agg_empresas') }}
where
  cnae_principal = '{{ fabricante }}' and situacao = 'ATIVA'
  and microrregiao_municipio in (select caso.microrregiao from caso)

union all

select
  3 as ordem,
  'fabricante (CNAE principal) na mesorregião' as busca,
  coalesce(sum(qtd_empresas), 0)::bigint as qtd_empresas
from {{ ref('agg_empresas') }}
where
  cnae_principal = '{{ fabricante }}' and situacao = 'ATIVA'
  and mesorregiao_municipio in (select caso.mesorregiao from caso)

union all

select
  4 as ordem,
  'atacadistas (CNAE principal) na mesorregião' as busca,
  coalesce(sum(qtd_empresas), 0)::bigint as qtd_empresas
from {{ ref('agg_empresas') }}
where
  cnae_principal in ({% for c in atacadistas %}'{{ c }}'{{ ', ' if not loop.last }}{% endfor %}) and situacao = 'ATIVA'
  and mesorregiao_municipio in (select caso.mesorregiao from caso)

union all

select
  5 as ordem,
  'CNAE do caso como secundário na mesorregião' as busca,
  count(*) as qtd_empresas
from secundarios
where mesorregiao_municipio in (select caso.mesorregiao from caso)

union all

select
  6 as ordem,
  'CNAE do caso como secundário na UF' as busca,
  count(*) as qtd_empresas
from secundarios
where uf = '{{ var("caso_uf") }}'

order by ordem
