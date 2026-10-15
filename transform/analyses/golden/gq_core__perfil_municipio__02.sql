{# ---
id: gq_core__perfil_municipio__02
conceito: perfil_municipio
camada: core
perguntas:
  - "Quais os municípios mais populosos do Espírito Santo?"
  - "Qual cidade do ES tem mais gente, pelo Censo?"
  - "Compare a população, a alfabetização e a idade mediana dos municípios do ES."
intencao: "Municípios de uma UF ordenados pela população do Censo 2022, com a estimativa mais recente e indicadores do Censo."
tabelas: [dim_municipio]
colunas_chave: [sigla_uf, nome_municipio, populacao_censo_2022, populacao, ano_populacao, taxa_alfabetizacao, idade_mediana]
armadilhas:
  - "Duas populações (estimativa do `ano_populacao` × Censo 2022) podem trocar a ordem entre municípios próximos: diga qual usou."
  - "`taxa_alfabetizacao` é fração de 0 a 1: multiplique por 100 para falar em %."
  - "Município sem Censo (NULL) vai para o fim da ordem (`nulls last`), não é zero."
variacoes:
  - "Por estimativa: ordene por `populacao desc`."
  - "Outra UF: troque `sigla_uf`; Brasil: tire o filtro e use `limit`."
resposta_esperada_fixtures:
  colunas: [nome_municipio, populacao_censo_2022, populacao, ano_populacao, taxa_alfabetizacao, idade_mediana]
  linhas:
    - [Serra, 520653, 520000, 2024, 0.97, 34.0]
    - [Vitória, 322869, 330000, 2024, 0.98, 40.0]
    - [Linhares, 166786, 180000, 2024, 0.9391, 34.0]
    - [Aracruz, 94765, 100000, 2024, 0.94, 35.0]
    - [Fundão, 17951, 20000, 2024, 0.93371, 37.0]
--- #}
{{ config(
    tags=['escopo_adicao', 'golden_query', 'incremento_enriquecimento_bd'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_bd'}
) }}

select
  nome_municipio,
  populacao_censo_2022,
  populacao,
  ano_populacao,
  taxa_alfabetizacao,
  idade_mediana
from {{ ref('dim_municipio') }}
where sigla_uf = 'ES'
order by populacao_censo_2022 desc nulls last, nome_municipio asc
