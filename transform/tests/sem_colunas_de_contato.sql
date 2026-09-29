{{ config(
    severity='error',
    tags=['escopo_adicao'],
    meta={'escopo': 'adicao'}
) }}

-- Staging AC 14 / ADR-0008: nenhum modelo de staging, intermediate ou marts expõe dados de
-- contato. Lê o `information_schema` de todo o banco (qualquer schema do projeto, exceto o de
-- falhas de teste), então pega também modelos futuros. Os `depends_on` garantem que o teste
-- rode depois dos modelos que partem das colunas de contato da fonte; acrescente aqui todo
-- modelo novo que leia `source('rfb', 'estabelecimentos')` diretamente.
-- depends_on: {{ ref('stg_rfb__estabelecimentos') }}
-- depends_on: {{ ref('stg_rfb__empresas') }}
select
  table_schema,
  table_name,
  column_name
from information_schema.columns
where
  lower(column_name) in ('email', 'ddd1', 'tel1', 'ddd2', 'tel2', 'ddd_fax', 'fax')
  and table_schema not like '%dbt_test__audit'
