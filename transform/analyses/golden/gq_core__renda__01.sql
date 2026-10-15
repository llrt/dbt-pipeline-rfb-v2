{# ---
id: gq_core__renda__01
conceito: renda
camada: core
perguntas:
  - "Qual a renda per capita de Fundão?"
  - "Quais municípios do ES têm a maior renda?"
  - "O pessoal de Fundão ganha bem?"
intencao: "Rendimento domiciliar per capita médio e mediano do Censo 2022 por município de uma UF."
tabelas: [dim_municipio]
colunas_chave: [sk_municipio, renda_per_capita_media_2022, renda_per_capita_mediana_2022]
armadilhas:
  - "'Renda' é ambígua: média (puxada pelas rendas altas) × mediana (domicílio típico). Mostre as duas ou pergunte."
  - "Reais nominais de 2022 (Censo), sem correção; não compare com salário de hoje sem dizer isso."
  - "Renda de uma UF não é a média simples dos municípios: pondere pelos moradores (gq_core__renda__02)."
variacoes:
  - "Um município: `where nome_municipio = 'Fundão' and sigla_uf = 'ES'`."
  - "Top N: `order by renda_per_capita_media_2022 desc limit N`."
resposta_esperada_fixtures:
  colunas: [nome_municipio, renda_per_capita_media_2022, renda_per_capita_mediana_2022]
  linhas:
    - [Vitória, 3351.64, 1750.0]
    - [Serra, 1720.1, 1200.0]
    - [Linhares, 1650.2, 1100.0]
    - [Aracruz, 1580.35, 1050.0]
    - [Fundão, 1406.78, 1040.0]
--- #}
{{ config(
    tags=['escopo_adicao', 'golden_query', 'incremento_enriquecimento_ibge'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_ibge'}
) }}

select
  nome_municipio,
  renda_per_capita_media_2022,
  renda_per_capita_mediana_2022
from {{ ref('dim_municipio') }}
where sigla_uf = 'ES'
order by renda_per_capita_media_2022 desc, nome_municipio asc
