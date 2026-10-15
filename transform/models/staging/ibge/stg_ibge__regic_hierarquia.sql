-- incremento: enriquecimento_ibge
-- REGIC 2018: hierarquia urbana e região de influência de cada município.
select
  {{ texto_ou_nulo('codmun') }} as id_municipio,
  {{ texto_ou_nulo('municipio') }} as nome_municipio,
  {{ texto_ou_nulo('siguf') }} as sigla_uf,
  {{ texto_ou_nulo('codcid') }} as id_cidade_regic,
  coalesce(categoria = 'Arranjo Populacional', false) as integra_arranjo_populacional,
  {{ texto_ou_nulo('codap') }} as id_arranjo_populacional,
  {{ texto_ou_nulo('arranjo_populacional') }} as nome_arranjo_populacional,
  regexp_extract(hierarquia_3, '^([1-5][A-C]?)', 1) as codigo_hierarquia,
  trim(split_part(hierarquia_2, ' - ', 1)) as nome_hierarquia,
  {{ texto_ou_nulo('hierarquia') }} as descricao_hierarquia,
  multiplas_subordinacoes::int as quantidade_subordinacoes,
  {{ texto_ou_nulo('regiao_de_influencia_vinculacao_imediata_consolidada') }} as regiao_influencia,
  {{ texto_ou_nulo('regiao_de_influencia_1') }} as cidade_influencia_1,
  {{ texto_ou_nulo('regiao_de_influencia_2') }} as cidade_influencia_2,
  {{ texto_ou_nulo('regiao_de_influencia_3') }} as cidade_influencia_3,
  {{ texto_ou_nulo('regiao_de_influencia_4') }} as cidade_influencia_4
from {{ source('ibge', 'regic_2018_hierarquia') }}
