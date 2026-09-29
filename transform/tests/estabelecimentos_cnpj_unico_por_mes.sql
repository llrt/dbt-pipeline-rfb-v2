{{ config(
    severity='error',
    tags=['escopo_original'],
    meta={'escopo': 'original'}
) }}

-- Staging AC 3: CNPJ completo (raiz + ordem + DV, com lpad) único por mês de referência. A
-- unicidade sobre as partes cruas deixaria passar '1' e '0001' na ordem, que colidem depois do
-- lpad. `not_null` das três partes está na fonte.
select
  _mes_referencia,
  {{ lpad_codigo('cnpj_raiz', 8) }}
  || {{ lpad_codigo('cnpj_ordem', 4) }}
  || {{ lpad_codigo('cnpj_dv', 2) }} as cnpj_completo,
  count(*) as ocorrencias
from {{ source('rfb', 'estabelecimentos') }}
group by 1, 2
having count(*) > 1
