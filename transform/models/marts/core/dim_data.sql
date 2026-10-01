-- Calendário para BI (ADR-0013, emenda R3-03): uma linha por dia de `primeiro_dia_calendario`
-- (1900-01-01) até o maior entre `data_referencia` e a maior data observada (início de atividade e situação), para que uma data
-- futura vinda da RFB não quebre o `relationships` da fato. `sk_data` = yyyymmdd (inteiro).
-- Dimensão de papel duplo na fato (início de atividade e data da situação) e base do mês de
-- referência.
-- Membros especiais com DATA PRÓPRIA e contígua ao calendário (sem lacuna nem NULL em `data`,
-- exigência da tabela de datas do Power BI): -1 "NÃO INFORMADO" (data nula) = 1899-12-31 e
-- -2 "DATA INVÁLIDA" (anterior a 1900; a RFB traz datas como 1194-08-15) = 1899-12-30. `ano`,
-- `mes` etc. ficam NULL neles, então não geram evento nas análises (`where ano is not null`).
-- A fato aponta para -2 quando a data é < 1900; `bh_empresas` mantém a data original (paridade).
with limites as (
  select
    greatest(
      max(dat_inicio_atividade),
      max(dat_situacao),
      {{ data_referencia(ref('stg_rfb__estabelecimentos')) }}
    ) as ultimo_dia
  from {{ ref('stg_rfb__estabelecimentos') }}
),

dias as (
  select unnest(generate_series(date '{{ var("primeiro_dia_calendario") }}', ultimo_dia, interval 1 day))::date as data  -- noqa: RF04
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
  (date '{{ var("primeiro_dia_calendario") }}' - 1)::date as data,  -- noqa: RF04
  null::integer as ano,
  null::integer as semestre,
  null::integer as trimestre,
  null::integer as mes,
  'NÃO INFORMADO' as nome_mes,
  'NÃO INFORMADO' as ano_mes,
  null::integer as dia,
  null::integer as dia_semana_numero,
  'NÃO INFORMADO' as dia_semana

union all

select
  -2 as sk_data,
  (date '{{ var("primeiro_dia_calendario") }}' - 2)::date as data,  -- noqa: RF04
  null::integer as ano,
  null::integer as semestre,
  null::integer as trimestre,
  null::integer as mes,
  'DATA INVÁLIDA' as nome_mes,
  'DATA INVÁLIDA' as ano_mes,
  null::integer as dia,
  null::integer as dia_semana_numero,
  'DATA INVÁLIDA' as dia_semana
