-- Dimensão de município para BI (ADR-0013): chave substituta inteira = código IBGE; hierarquias em
-- colunas (região → UF → mesorregião → microrregião → município; região intermediária → imediata);
-- membro -1 "NÃO INFORMADO" para estabelecimentos sem município na Base dos Dados (ex.: exterior).
-- incremento: enriquecimento_bd (ADR-0015): atributos do Censo 2022 e região metropolitana
-- (`NÃO PERTENCE` quando o município não está em nenhuma; densidade NULL sem Censo ou sem área).
select
  mun.sk_municipio,
  mun.id_municipio_ibge,
  mun.codigo_rfb,
  mun.nome_municipio,
  mun.sigla_uf,
  mun.nome_uf,
  mun.nome_regiao,
  mun.id_mesorregiao,
  mun.nome_mesorregiao,
  mun.id_microrregiao,
  mun.nome_microrregiao,
  mun.id_regiao_intermediaria,
  mun.nome_regiao_intermediaria,
  mun.id_regiao_imediata,
  mun.nome_regiao_imediata,
  mun.latitude,
  mun.longitude,
  mun.ano_populacao,
  mun.populacao,
  mun.ano_pib,
  mun.pib,
  cen.populacao as populacao_censo_2022,
  cen.domicilios as domicilios_2022,
  cen.area_km2,
  round(cen.populacao / nullif(cen.area_km2, 0), 2) as densidade_hab_km2,
  cen.taxa_alfabetizacao,
  cen.idade_mediana,
  cen.indice_envelhecimento,
  cen.razao_sexo,
  coalesce(rm.nome_regiao_metropolitana, 'NÃO PERTENCE') as nome_regiao_metropolitana
from {{ ref('int_municipios__conformados') }} as mun
left join {{ ref('stg_bd__censo_2022_municipio') }} as cen
  on mun.id_municipio_ibge = cen.id_municipio
left join {{ ref('stg_bd__regioes_metropolitanas') }} as rm
  on mun.id_municipio_ibge = rm.id_municipio

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
  null::double as pib,
  null::bigint as populacao_censo_2022,
  null::bigint as domicilios_2022,
  null::double as area_km2,
  null::double as densidade_hab_km2,
  null::double as taxa_alfabetizacao,
  null::double as idade_mediana,
  null::double as indice_envelhecimento,
  null::double as razao_sexo,
  'NÃO INFORMADO' as nome_regiao_metropolitana
