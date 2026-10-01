-- DQ-02: resumo por execução dbt do histórico de testes. View, não tabela: o histórico só é
-- completado no `on-run-end`, depois do fim dos modelos, então a view sempre reflete a execução mais
-- recente. Uma linha por `invocation_id`, a mais recente primeiro.
{{ config(materialized='view') }}

select
  invocation_id,
  max(executado_em) as executado_em,
  count(*) as testes,
  count(*) filter (where status = 'pass') as aprovados,
  count(*) filter (where status = 'warn') as avisos,
  count(*) filter (where status in ('fail', 'error')) as falhos,
  count(*) filter (where status = 'skipped') as pulados,
  coalesce(sum(falhas), 0)::bigint as linhas_com_falha,
  count(*) filter (where escopo = 'original') as testes_original,
  count(*) filter (where escopo = 'adicao') as testes_adicao
from {{ source('observabilidade', 'dq_historico_testes') }}
group by invocation_id
order by executado_em desc
