select
  {{ lpad_codigo('cnpj_raiz', 8) }} as cnpj_raiz,
  {{ texto_ou_nulo('razao_social') }} as razao_social,
  {{ lpad_codigo('natureza_jur', 4) }} as natureza_juridica_codigo,
  {{ lpad_codigo('qualificacao_resp', 2) }} as qualificacao_responsavel_codigo,
  {{ decimal_rfb('capital_soc') }} as capital_social,
  try_cast({{ texto_ou_nulo('porte') }} as integer) as porte_codigo,
  {{ texto_ou_nulo('ente_fed_resp') }} as ente_federativo_responsavel,
  _mes_referencia,
  _data_referencia
from {{ source('rfb', 'empresas') }}
where {{ filtro_mes_referencia(source('rfb', 'empresas')) }}
-- adaptado (B8): raiz duplicada no extrato real vira uma linha (ver `empresa_preferida_por_raiz`)
qualify {{ empresa_preferida_por_raiz() }}
