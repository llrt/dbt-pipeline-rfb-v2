-- Calendário para BI (ADR-0013): uma linha por dia do menor dia referenciado pelas datas dos
-- estabelecimentos (início de atividade e situação) até `data_referencia`; `sk_data` = yyyymmdd
-- (inteiro). Dimensão de papel duplo na fato (início de atividade e data da situação) e base do
-- mês de referência. O fim do calendário é o maior entre `data_referencia` e a maior data
-- observada, para que uma data futura vinda da RFB não quebre o `relationships` da fato.
-- Membro -1 "NÃO INFORMADO" para datas nulas (ex.: `00000000`).
with limites as (
  select
    least(min(dat_inicio_atividade), min(dat_situacao)) as primeiro_dia,
    greatest(
      max(dat_inicio_atividade),
      max(dat_situacao),
      {{ data_referencia(ref('stg_rfb__estabelecimentos')) }}
    ) as ultimo_dia
  from {{ ref('stg_rfb__estabelecimentos') }}
),

dias as (
  select unnest(generate_series(primeiro_dia, ultimo_dia, interval 1 day))::date as data  -- noqa: RF04
  from limites
)

select
  (year(data) * 10000 + month(data) * 100 + day(data))::integer as sk_data,
  data,
  year(data)::integer as ano,
  case when month(data) <= 6 then 1 else 2 end::integer as semestre,
  quarter(data)::integer as trimestre,
  month(data)::integer as mes,
  list_extract(
    [
      'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
      'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'
    ],
    month(data)
  ) as nome_mes,
  strftime(data, '%Y-%m') as ano_mes,
  day(data)::integer as dia,
  isodow(data)::integer as dia_semana_numero,
  list_extract(
    [
      'segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira',
      'sexta-feira', 'sábado', 'domingo'
    ],
    isodow(data)
  ) as dia_semana
from dias

union all

select
  -1 as sk_data,
  null::date as data,  -- noqa: RF04
  null::integer as ano,
  null::integer as semestre,
  null::integer as trimestre,
  null::integer as mes,
  'NÃO INFORMADO' as nome_mes,
  'NÃO INFORMADO' as ano_mes,
  null::integer as dia,
  null::integer as dia_semana_numero,
  'NÃO INFORMADO' as dia_semana
