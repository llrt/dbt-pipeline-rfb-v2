{{ config(
    severity='error',
    tags=['escopo_adicao'],
    meta={'escopo': 'adicao'}
) }}

-- DQ-01 / R3-09: casos conhecidos do teste `data_nao_futura`. Só a data posterior a `data_referencia`
-- (por 1 dia ou por 5 anos) é acusada; a própria data, uma data passada e NULL não. Retorna uma linha
-- por divergência entre o esperado (2 acusadas) e o resultado.
with entrada as (
  select dat
  from (
    values
      ({{ data_referencia() }} + interval 1 day),
      ({{ data_referencia() }} + interval 5 year),
      ({{ data_referencia() }}),
      ({{ data_referencia() }} - interval 1 day),
      (null::date)
  ) as t (dat)
),

acusadas as (
  {{ datas_futuras('entrada', 'dat') }}
)

select
  count(*) as acusadas,
  count(*) filter (where valor = {{ data_referencia() }} + interval 1 day) as acusadas_amanha,
  count(*) filter (where valor = {{ data_referencia() }} + interval 5 year) as acusadas_em_5_anos
from acusadas
having
  count(*) != 2
  or count(*) filter (where valor = {{ data_referencia() }} + interval 1 day) != 1
  or count(*) filter (where valor = {{ data_referencia() }} + interval 5 year) != 1
