{{ config(
    severity='error',
    tags=['escopo_adicao'],
    meta={'escopo': 'adicao'}
) }}

-- DQ-01 / R3-09: casos conhecidos do teste `cnpj_dv_valido`. Retorna uma linha por divergência
-- entre os CNPJs acusados e os esperados. Exemplo oficial da RFB para o CNPJ alfanumérico:
-- `12ABC34501DE35` é válido e `12ABC34501DE36` não; minúsculas e tamanho errado são inválidos.
with entrada as (
  select unnest(['11222333000181', '11222333000182', '12ABC34501DE35', '12ABC34501DE36', '12abc34501de35', '1234']) as cnpj
),

acusados as (
  {{ cnpj_dv_invalidos('entrada', 'cnpj') }}
),

esperados as (
  select unnest(['11222333000182', '12ABC34501DE36', '12abc34501de35', '1234']) as cnpj
),

indevidos as (
  select cnpj from acusados
  except
  select cnpj from esperados
),

faltantes as (
  select cnpj from esperados
  except
  select cnpj from acusados
)

select
  cnpj,
  'acusado indevidamente' as divergencia
from indevidos

union all

select
  cnpj,
  'não acusado' as divergencia
from faltantes
