-- incremento: enriquecimento_ibge
-- REGIC 2018: ligações origem -> destino dos questionários, com o % dos deslocamentos da origem que vão
-- ao destino para cada tema (Q1 a Q10). NULL quando ausente na planilha.
select
  {{ texto_ou_nulo('mun_origem') }} as id_municipio_origem,
  {{ texto_ou_nulo('mun_destino') }} as id_municipio_destino,
  q1::double as pct_vestuario_calcados,
  q2::double as pct_moveis_eletro,
  q3::double as pct_saude_baixa_media_complexidade,
  q4::double as pct_saude_alta_complexidade,
  q5::double as pct_ensino_superior,
  q6::double as pct_atividades_culturais,
  q7::double as pct_atividades_esportivas,
  q8::double as pct_aeroporto,
  q9::double as pct_jornais,
  q10::double as pct_transporte_coletivo,
  perc_lig::double as pct_bens_servicos,
  ia::double as indice_atracao
from {{ source('ibge', 'regic_2018_ligacoes') }}
