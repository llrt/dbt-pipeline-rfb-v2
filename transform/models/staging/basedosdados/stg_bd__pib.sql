select
  {{ texto_ou_nulo('id_municipio') }} as id_municipio,
  ano::int as ano,
  pib::double as pib,
  impostos_liquidos::double as impostos_liquidos,
  va::double as va,
  va_agropecuaria::double as va_agropecuaria,
  va_industria::double as va_industria,
  va_servicos::double as va_servicos,
  va_adespss::double as va_adespss
from {{ source('basedosdados', 'pib') }}
