-- incremento: enriquecimento_bd (ADR-0015)
select
  {{ texto_ou_nulo('id_municipio') }} as id_municipio,
  {{ texto_ou_nulo('sigla_uf') }} as sigla_uf,
  domicilios::bigint as domicilios,
  populacao::bigint as populacao,
  area::double as area_km2,
  taxa_alfabetizacao::double as taxa_alfabetizacao,
  idade_mediana::double as idade_mediana,
  razao_sexo::double as razao_sexo,
  indice_envelhecimento::double as indice_envelhecimento,
  populacao_indigena::bigint as populacao_indigena,
  populacao_indigena_terra_indigena::bigint as populacao_indigena_terra_indigena,
  populacao_quilombola::bigint as populacao_quilombola,
  populacao_quilombola_territorio_quilombola::bigint as populacao_quilombola_territorio_quilombola
from {{ source('basedosdados', 'censo_2022_municipio') }}
