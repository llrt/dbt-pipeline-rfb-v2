-- incremento: enriquecimento_ibge
-- REGIC 2018: índice de atração de cada município que recebe deslocamentos, geral e por tema. A
-- pseudo-localidade `0` ("Outros / Não circula jornal") não é município e fica de fora.
select
  {{ texto_ou_nulo('codmun') }} as id_municipio,
  {{ texto_ou_nulo('nome_mun') }} as nome_municipio,
  pop2018::bigint as populacao_2018,
  ia::double as indice_atracao,
  ia_q1::double as indice_atracao_vestuario_calcados,
  ia_q2::double as indice_atracao_moveis_eletro,
  ia_q3::double as indice_atracao_saude_baixa_media_complexidade,
  ia_q4::double as indice_atracao_saude_alta_complexidade,
  ia_q5::double as indice_atracao_ensino_superior,
  ia_q6::double as indice_atracao_atividades_culturais,
  ia_q7::double as indice_atracao_atividades_esportivas,
  ia_q8::double as indice_atracao_aeroporto,
  ia_q9::double as indice_atracao_jornais,
  ia_q10::double as indice_atracao_transporte_coletivo
from {{ source('ibge', 'regic_2018_atracao') }}
where trim(codmun) <> '0'
