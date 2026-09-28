select
  {{ lpad_codigo('cnpj_raiz', 8) }} as cnpj_raiz,
  case opcao_simples when 'S' then true when 'N' then false end as opcao_simples,
  case
    when dat_opcao_simples = '00000000' then null
    else strptime(dat_opcao_simples, '%Y%m%d')::date
  end as dat_opcao_simples,
  case
    when dat_exclusao_simples = '00000000' then null
    else strptime(dat_exclusao_simples, '%Y%m%d')::date
  end as dat_exclusao_simples,
  case opcao_mei when 'S' then true when 'N' then false end as opcao_mei,
  case
    when dat_opcao_mei = '00000000' then null
    else strptime(dat_opcao_mei, '%Y%m%d')::date
  end as dat_opcao_mei,
  case
    when dat_exclusao_mei = '00000000' then null
    else strptime(dat_exclusao_mei, '%Y%m%d')::date
  end as dat_exclusao_mei
from {{ source('rfb', 'simples') }}
where {{ filtro_mes_referencia(source('rfb', 'simples')) }}
