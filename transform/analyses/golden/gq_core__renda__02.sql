{# ---
id: gq_core__renda__02
conceito: renda
camada: core
perguntas:
  - "Qual a renda média do Espírito Santo?"
  - "Qual a renda per capita de cada UF?"
intencao: "Renda média per capita da UF ponderada pelos moradores (a média simples dos municípios estaria errada)."
tabelas: [dim_municipio]
colunas_chave: [sigla_uf, renda_per_capita_media_2022, moradores_renda_2022]
armadilhas:
  - "Média de médias erra: pondere a renda média do município pelos `moradores_renda_2022`."
  - "Não há mediana da UF: medianas não se agregam."
  - "Municípios sem renda (NULL) ficam fora do numerador e do denominador."
variacoes:
  - "Por região: agrupe por `nome_regiao`."
resposta_esperada_fixtures:
  colunas: [sigla_uf, renda_per_capita_media_ponderada, municipios_com_renda]
  linhas:
    - [AL, 520.4, 1]
    - [ES, 2162.57, 5]
    - [PB, 540.9, 1]
    - [PI, 610.15, 1]
--- #}
{{ config(
    tags=['escopo_adicao', 'golden_query', 'incremento_enriquecimento_ibge'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_ibge'}
) }}

select
  sigla_uf,
  round(
    sum(renda_per_capita_media_2022 * moradores_renda_2022) / sum(moradores_renda_2022), 2
  ) as renda_per_capita_media_ponderada,
  count(renda_per_capita_media_2022) as municipios_com_renda
from {{ ref('dim_municipio') }}
where renda_per_capita_media_2022 is not null
group by sigla_uf
order by sigla_uf
