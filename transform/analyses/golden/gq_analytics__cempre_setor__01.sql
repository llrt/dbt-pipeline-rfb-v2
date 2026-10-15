{# ---
id: gq_analytics__cempre_setor__01
conceito: cempre_setor
camada: analytics
perguntas:
  - "Quantas pessoas trabalham em lojas de tintas no ES, por município?"
  - "Qual o tamanho real do setor de tintas comparado aos CNPJs ativos?"
  - "Quanto gente trabalha no comércio de tintas em Serra?"
intencao: "CEMPRE (unidades locais, pessoal ocupado, sigilo) ao lado dos ativos da RFB com e sem MEI, para uma classe CNAE numa UF."
tabelas: [mart_emprego_setor_municipio]
colunas_chave: [municipio, uf, classe_cnae, ano_cempre, unidades_locais_cempre, pessoal_ocupado_cempre, tem_sigilo, ativos_rfb_sem_mei]
armadilhas:
  - "CEMPRE é por CLASSE (5 dígitos, '47415'), não subclasse."
  - "Compare unidades locais com `ativos_rfb_sem_mei`: o CEMPRE não conta MEI (RN-30)."
  - "Sigilo: pessoal NULL com `tem_sigilo`; nunca impute; somas subestimam."
  - "CEMPRE de 31/12 do `ano_cempre`; RFB do `mes_referencia_rfb`."
variacoes:
  - "Outra classe: troque `classe_cnae` (5 dígitos, sem pontuação)."
  - "Salário médio mensal aproximado: `salarios_mil_reais * 1000 / pessoal_assalariado_cempre / 13`."
resposta_esperada_fixtures:
  colunas: [municipio, ano_cempre, unidades_locais_cempre, pessoal_ocupado_cempre, tem_sigilo, ativos_rfb, ativos_rfb_sem_mei, mes_referencia_rfb]
  linhas:
    - [Aracruz, 2024, 3, null, true, 0, 0, 2026-09]
    - [Fundão, 2024, 0, 0, false, 1, 0, 2026-09]
    - [Linhares, 2024, 12, null, true, 0, 0, 2026-09]
    - [Serra, 2024, 33, 196, false, 1, 0, 2026-09]
    - [Vitória, 2024, 25, 164, false, 0, 0, 2026-09]
--- #}
{{ config(
    tags=['escopo_adicao', 'golden_query', 'incremento_enriquecimento_ibge'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_ibge'}
) }}

select
  municipio,
  ano_cempre,
  unidades_locais_cempre,
  pessoal_ocupado_cempre,
  tem_sigilo,
  ativos_rfb,
  ativos_rfb_sem_mei,
  mes_referencia_rfb
from {{ ref('mart_emprego_setor_municipio') }}
where uf = 'ES' and classe_cnae = '47415'
order by municipio
