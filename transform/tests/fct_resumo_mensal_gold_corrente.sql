{{ config(
    severity='warn',
    store_failures=true,
    tags=['escopo_adicao'],
    meta={'escopo': 'adicao'}
) }}

-- P22 (R3): o gold "corrente" (dimensões, `fct_estabelecimentos`, marts) é sempre o do mês mais novo da
-- série. Se `fct_resumo_mensal` já tem um mês mais novo que o deste build, um mês antigo foi construído
-- por cima do corrente sem o backfill do `rfb pipeline` (que usa `external_root` temporário): reprocesse
-- o mês mais novo. Fora do seletor `backfill_resumo_mensal_testes`, onde a diferença é esperada.
with serie as (
  select max(mes_referencia) as mes_mais_novo_da_serie
  from {{ ref('fct_resumo_mensal') }}
),

build as (
  select max(_mes_referencia) as mes_do_gold_corrente
  from {{ ref('stg_rfb__estabelecimentos') }}
)

select
  serie.mes_mais_novo_da_serie,
  build.mes_do_gold_corrente
from serie
cross join build
where serie.mes_mais_novo_da_serie != build.mes_do_gold_corrente
