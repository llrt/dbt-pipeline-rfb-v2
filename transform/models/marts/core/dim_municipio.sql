-- Dimensão de município para BI (ADR-0013): chave substituta inteira = código IBGE; hierarquias em
-- colunas (região → UF → mesorregião → microrregião → município; região intermediária → imediata);
-- membro -1 "NÃO INFORMADO" para estabelecimentos sem município na Base dos Dados (ex.: exterior).
select
  sk_municipio,
  id_municipio_ibge,
  codigo_rfb,
  nome_municipio,
  sigla_uf,
  nome_uf,
  nome_regiao,
  id_mesorregiao,
  nome_mesorregiao,
  id_microrregiao,
  nome_microrregiao,
  id_regiao_intermediaria,
  nome_regiao_intermediaria,
  id_regiao_imediata,
  nome_regiao_imediata,
  latitude,
  longitude,
  ano_populacao,
  populacao,
  ano_pib,
  pib
from {{ ref('int_municipios__conformados') }}

union all

select
  -1 as sk_municipio,
  '-1' as id_municipio_ibge,
  '-1' as codigo_rfb,
  'NÃO INFORMADO' as nome_municipio,
  'NI' as sigla_uf,
  'NÃO INFORMADO' as nome_uf,
  'NÃO INFORMADO' as nome_regiao,
  '-1' as id_mesorregiao,
  'NÃO INFORMADO' as nome_mesorregiao,
  '-1' as id_microrregiao,
  'NÃO INFORMADO' as nome_microrregiao,
  '-1' as id_regiao_intermediaria,
  'NÃO INFORMADO' as nome_regiao_intermediaria,
  '-1' as id_regiao_imediata,
  'NÃO INFORMADO' as nome_regiao_imediata,
  null::double as latitude,
  null::double as longitude,
  null::integer as ano_populacao,
  null::bigint as populacao,
  null::integer as ano_pib,
  null::double as pib
