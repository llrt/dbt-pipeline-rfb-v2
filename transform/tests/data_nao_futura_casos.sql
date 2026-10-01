{{ config(
    severity='error',
    tags=['escopo_adicao'],
    meta={'escopo': 'adicao'}
) }}

-- DQ-01 / R3-09: casos conhecidos do teste `data_nao_futura`. Só a data posterior a `data_referencia`
-- (por 1 dia ou por 5 anos) é acusada; a própria data, uma data passada e NULL não. Retorna uma linha
-- por divergência entre o esperado (2 acusadas) e o resultado.
with entrada as (
  select
    unnest([
      ({{ data_referencia() }} + interval 1 day)::date,
      ({{ data_referencia() }} + interval 5 year)::date,
      {{ data_referencia() }}::date,
      ({{ data_referencia() }} - interval 1 day)::date,
      null::date
    ]) as dat
),

acusadas as (
  {{ datas_futuras('entrada', 'dat') }}
)

select
  count(*) as acusadas,
  count(*) filter (where valor = ({{ data_referencia() }} + interval 1 day)::date) as acusadas_amanha,
  count(*) filter (where valor = ({{ data_referencia() }} + interval 5 year)::date) as acusadas_em_5_anos
from acusadas
having
  count(*) != 2
  or count(*) filter (where valor = ({{ data_referencia() }} + interval 1 day)::date) != 1
  or count(*) filter (where valor = ({{ data_referencia() }} + interval 5 year)::date) != 1
