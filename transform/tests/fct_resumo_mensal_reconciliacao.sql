{{ config(
    severity='error',
    tags=['escopo_adicao'],
    meta={'escopo': 'adicao'}
) }}

-- BI-02 / ADR-0013: a partição do mês processado em `fct_resumo_mensal` reconcilia com
-- `fct_estabelecimentos` (quantidade, ativos e capital social); soma errada ou partição ausente
-- retornam uma linha. A partição vem do disco, então vale também para o mês antigo reprocessado.
with resumo as (
  select
    count(*) as linhas,
    coalesce(sum(res.qtd_estabelecimentos), 0) as qtd,
    coalesce(sum(res.qtd_ativos), 0) as ativos,
    coalesce(sum(res.soma_capital_social), 0) as capital
  from {{ ref('fct_resumo_mensal') }} as res
  where res.mes_referencia = (select max(stg._mes_referencia) from {{ ref('stg_rfb__estabelecimentos') }} as stg)
),

fato as (
  select
    count(*) as qtd,
    count(*) filter (where eh_ativa) as ativos,
    coalesce(sum(capital_social), 0) as capital
  from {{ ref('fct_estabelecimentos') }}
)

select
  'partição do mês ausente em fct_resumo_mensal' as violacao,
  resumo.linhas as no_resumo,
  fato.qtd as esperado
from resumo
cross join fato
where resumo.linhas = 0

union all

select
  'soma de qtd_estabelecimentos != linhas de fct_estabelecimentos' as violacao,
  resumo.qtd as no_resumo,
  fato.qtd as esperado
from resumo
cross join fato
where resumo.linhas > 0 and resumo.qtd != fato.qtd

union all

select
  'soma de qtd_ativos != ativos de fct_estabelecimentos' as violacao,
  resumo.ativos as no_resumo,
  fato.ativos as esperado
from resumo
cross join fato
where resumo.linhas > 0 and resumo.ativos != fato.ativos

union all

select
  'soma_capital_social != capital de fct_estabelecimentos' as violacao,
  resumo.capital as no_resumo,
  fato.capital as esperado
from resumo
cross join fato
where resumo.linhas > 0 and resumo.capital != fato.capital
