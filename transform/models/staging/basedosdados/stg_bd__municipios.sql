select
  {{ texto_ou_nulo('id_municipio') }} as id_municipio,
  {{ texto_ou_nulo('id_municipio_rf') }} as id_municipio_rf,
  {{ texto_ou_nulo('nome') }} as nome,
  {{ texto_ou_nulo('sigla_uf') }} as sigla_uf,
  {{ texto_ou_nulo('nome_uf') }} as nome_uf,
  {{ texto_ou_nulo('nome_regiao') }} as nome_regiao,
  {{ texto_ou_nulo('id_microrregiao') }} as id_microrregiao,
  {{ texto_ou_nulo('nome_microrregiao') }} as nome_microrregiao,
  {{ texto_ou_nulo('id_mesorregiao') }} as id_mesorregiao,
  {{ texto_ou_nulo('nome_mesorregiao') }} as nome_mesorregiao,
  {{ texto_ou_nulo('id_regiao_imediata') }} as id_regiao_imediata,
  {{ texto_ou_nulo('nome_regiao_imediata') }} as nome_regiao_imediata,
  {{ texto_ou_nulo('id_regiao_intermediaria') }} as id_regiao_intermediaria,
  {{ texto_ou_nulo('nome_regiao_intermediaria') }} as nome_regiao_intermediaria,
  regexp_extract(centroide, 'POINT\(([-0-9.]+) ([-0-9.]+)\)', 1)::double as longitude,
  regexp_extract(centroide, 'POINT\(([-0-9.]+) ([-0-9.]+)\)', 2)::double as latitude
from {{ source('basedosdados', 'municipio') }}
