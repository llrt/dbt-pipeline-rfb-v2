-- Contatos (`email`, `ddd*`, `tel*`, `fax`) ficam de fora (ADR-0008). ~65 M linhas no real: só
-- funções escalares vetorizadas; a lista de CNAEs secundários usa `list_transform`.
with fonte as (
  select *
  from {{ source('rfb', 'estabelecimentos') }}
  where {{ filtro_mes_referencia(source('rfb', 'estabelecimentos')) }}
)

select
  {{ lpad_codigo('cnpj_raiz', 8) }} as cnpj_raiz,
  {{ lpad_codigo('cnpj_ordem', 4) }} as cnpj_ordem,
  {{ lpad_codigo('cnpj_dv', 2) }} as cnpj_dv,
  {{ lpad_codigo('cnpj_raiz', 8) }}
  || {{ lpad_codigo('cnpj_ordem', 4) }}
  || {{ lpad_codigo('cnpj_dv', 2) }} as cnpj_completo,
  try_cast({{ texto_ou_nulo('ind_matriz_filial') }} as integer) as matriz_filial_codigo,
  {{ texto_ou_nulo('nome_fantasia') }} as nome_fantasia,
  try_cast({{ texto_ou_nulo('situacao') }} as integer) as situacao_codigo,
  {{ data_rfb('dat_situacao') }} as dat_situacao,
  {{ lpad_codigo('mot_situacao', 2) }} as motivo_situacao_codigo,
  {{ texto_ou_nulo('cidade_exterior') }} as cidade_exterior,
  {{ lpad_codigo('pais', 3) }} as pais_codigo,
  {{ data_rfb('dat_inicio_atividade') }} as dat_inicio_atividade,
  {{ lpad_codigo('cnae_principal', 7) }} as cnae_principal,
  {{ texto_ou_nulo('cnaes_secundarios') }} as cnaes_secundarios,
  coalesce(
    list_transform(
      list_filter(string_split({{ texto_ou_nulo('cnaes_secundarios') }}, ','), c -> trim(c) != ''),
      c -> case when length(trim(c)) > 7 then trim(c) else lpad(trim(c), 7, '0') end
    ),
    []::varchar[]
  ) as cnaes_secundarios_lista,
  {{ texto_ou_nulo('tip_logradouro') }} as tipo_logradouro,
  {{ texto_ou_nulo('logradouro') }} as logradouro,
  {{ texto_ou_nulo('num_logradouro') }} as numero,
  {{ texto_ou_nulo('compl_logradouro') }} as complemento,
  {{ texto_ou_nulo('bairro') }} as bairro,
  {{ texto_ou_nulo('cep') }} as cep,
  {{ texto_ou_nulo('uf') }} as uf,
  {{ lpad_codigo('municipio', 4) }} as municipio_rfb_codigo,
  {{ texto_ou_nulo('sit_especial') }} as situacao_especial,
  {{ data_rfb('dat_sit_especial') }} as dat_situacao_especial,
  _mes_referencia,
  _data_referencia
from fonte
