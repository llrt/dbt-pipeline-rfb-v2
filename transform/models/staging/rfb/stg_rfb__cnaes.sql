select
  {{ lpad_codigo('codigo', 7) }} as codigo,
  {{ texto_ou_nulo('descricao') }} as descricao
from {{ source('rfb', 'cnaes') }}
where {{ filtro_mes_referencia(source('rfb', 'cnaes')) }}
