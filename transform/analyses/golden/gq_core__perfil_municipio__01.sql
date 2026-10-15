{# ---
id: gq_core__perfil_municipio__01
conceito: perfil_municipio
camada: core
perguntas:
  - "Qual a população e o PIB de Água Branca, em Alagoas?"
  - "Quantos habitantes tem Água Branca (AL), e qual o PIB per capita?"
  - "Me dá o perfil do município de Água Branca/AL."
intencao: "Perfil de um município (identificado por nome E UF): as duas populações, PIB, PIB per capita aproximado, domicílios, área e densidade, com o ano de cada fonte."
tabelas: [dim_municipio]
colunas_chave: [nome_municipio, sigla_uf, populacao, ano_populacao, populacao_censo_2022, pib, ano_pib, domicilios_2022, area_km2, densidade_hab_km2]
armadilhas:
  - "Duas populações: `populacao` é a estimativa do IBGE do `ano_populacao` (2024 no dado real); `populacao_censo_2022` é a contagem do Censo. Diga qual usou e o ano; a densidade (`densidade_hab_km2`) é do Censo."
  - "PIB per capita não é coluna: `pib / populacao` mistura o ano do PIB (`ano_pib`) com o da estimativa. O IBGE divide pela população do mesmo ano (a série está em gq_staging__perfil_municipio__01). Declare os anos ou chame de aproximado."
  - "Filtre o município pelo nome E pela UF: Água Branca existe em AL, PB e PI (gq_core__municipio_geografia__02). Sem UF, pergunte."
  - "`pib` está em reais (R$) nominais do `ano_pib`; NULL é sem dado, nunca zero."
variacoes:
  - "Outro município: troque `nome_municipio` e `sigla_uf`."
  - "Censo 2022: acrescente `taxa_alfabetizacao`, `idade_mediana`, `indice_envelhecimento`."
  - "Renda e REGIC: acrescente `renda_per_capita_media_2022` e `regic_hierarquia` (ver gq_core__renda__01 e gq_core__regic_polo_compras__01)."
resposta_esperada_fixtures:
  colunas: [nome_municipio, sigla_uf, populacao, ano_populacao, populacao_censo_2022, pib, ano_pib, pib_per_capita_aprox, domicilios_2022, area_km2, densidade_hab_km2]
  linhas:
    - [Água Branca, AL, 10000, 2024, 9873, 150000.0, 2021, 15.0, 3300, 454.0, 21.75]
--- #}
{{ config(
    tags=['escopo_adicao', 'golden_query', 'incremento_enriquecimento_bd'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_bd'}
) }}

select
  nome_municipio,
  sigla_uf,
  populacao,
  ano_populacao,
  populacao_censo_2022,
  pib,
  ano_pib,
  round(pib / nullif(populacao, 0), 2) as pib_per_capita_aprox,
  domicilios_2022,
  area_km2,
  densidade_hab_km2
from {{ ref('dim_municipio') }}
where nome_municipio = 'Água Branca' and sigla_uf = 'AL'
order by nome_municipio
