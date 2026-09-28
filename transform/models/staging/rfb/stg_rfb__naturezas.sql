select
  {{ lpad_codigo('codigo', 4) }} as codigo,
  {{ texto_ou_nulo('descricao') }} as descricao
from {{ source('rfb', 'naturezas') }}
where {{ filtro_mes_referencia(source('rfb', 'naturezas')) }}
