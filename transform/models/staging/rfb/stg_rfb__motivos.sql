select
  {{ lpad_codigo('codigo', 2) }} as codigo,
  {{ texto_ou_nulo('descricao') }} as descricao
from {{ source('rfb', 'motivos') }}
where {{ filtro_mes_referencia(source('rfb', 'motivos')) }}
