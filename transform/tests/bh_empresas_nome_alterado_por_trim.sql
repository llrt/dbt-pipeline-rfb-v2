{{ config(
    severity='warn',
    store_failures=true,
    tags=['escopo_adicao'],
    meta={'escopo': 'adicao'}
) }}

-- ADR-0005, emenda R2-01: `bh_empresas.nome` sai com `trim` (staging); o original, não. Mede a
-- adaptação: linhas de `bh_empresas` cujo nome literal do original (`coalesce(nome_fantasia,
-- razao_social)` sobre o raw) tem espaço nas bordas — em geral razão social com espaço à esquerda e
-- nome fantasia vazio (fev/2025: ~752; fixtures: 1, linha G). Warn: a diferença é declarada, não erro.
with estabelecimentos as (
  select
    {{ lpad_codigo('cnpj_raiz', 8) }} as cnpj_raiz,
    {{ lpad_codigo('cnpj_raiz', 8) }}
    || {{ lpad_codigo('cnpj_ordem', 4) }}
    || {{ lpad_codigo('cnpj_dv', 2) }} as cnpj_completo,
    nome_fantasia
  from {{ source('rfb', 'estabelecimentos') }}
  where {{ filtro_mes_referencia(source('rfb', 'estabelecimentos')) }}
),

empresas as (
  select
    {{ lpad_codigo('cnpj_raiz', 8) }} as cnpj_raiz,
    razao_social
  from {{ source('rfb', 'empresas') }}
  where {{ filtro_mes_referencia(source('rfb', 'empresas')) }}
),

nome_literal as (
  select
    est.cnpj_completo,
    coalesce(est.nome_fantasia, emp.razao_social) as nome_original
  from estabelecimentos as est
  inner join empresas as emp on est.cnpj_raiz = emp.cnpj_raiz
)

select
  bh.cnpj_completo,
  {{ mascarar_cpf_no_nome('lit.nome_original') }} as nome_original,  -- store_failures sem CPF (R4-01)
  bh.nome
from {{ ref('bh_empresas') }} as bh
inner join nome_literal as lit on bh.cnpj_completo = lit.cnpj_completo
where lit.nome_original != trim(lit.nome_original)
