select
  {{ lpad_codigo('cnpj_raiz', 8) }} as cnpj_raiz,
  case opcao_simples when 'S' then true when 'N' then false end as opcao_simples,
  {{ data_rfb('dat_opcao_simples') }} as dat_opcao_simples,
  {{ data_rfb('dat_exclusao_simples') }} as dat_exclusao_simples,
  case opcao_mei when 'S' then true when 'N' then false end as opcao_mei,
  {{ data_rfb('dat_opcao_mei') }} as dat_opcao_mei,
  {{ data_rfb('dat_exclusao_mei') }} as dat_exclusao_mei
from {{ source('rfb', 'simples') }}
where {{ filtro_mes_referencia(source('rfb', 'simples')) }}
