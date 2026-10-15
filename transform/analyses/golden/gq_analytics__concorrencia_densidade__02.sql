{# ---
id: gq_analytics__concorrencia_densidade__02
conceito: concorrencia_densidade
camada: analytics
perguntas:
  - "Quais municípios do ES têm mais lojas de tintas por habitante?"
  - "Onde a concorrência de tintas é menor no Espírito Santo?"
intencao: "Ranking de densidade de um CNAE entre os municípios de uma UF."
tabelas: [mart_concorrencia_municipio]
colunas_chave: [cnae_principal, uf, ativos_por_10k_hab, ranking_uf]
armadilhas:
  - "Só aparecem municípios com ao menos um estabelecimento do CNAE (ativo ou não)."
  - "Densidade alta com população pequena é instável: mostre ativos e população."
variacoes:
  - "Menos concorridos: inverta a ordem; inclua vazios via mart_concorrencia_area_mercado."
resposta_esperada_fixtures:
  colunas: [ranking_uf, municipio, ativos, populacao, ativos_por_10k_hab]
  linhas:
    - [1, Fundão, 1, 20000, 0.5]
    - [2, Serra, 1, 520000, 0.02]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  ranking_uf,
  municipio,
  ativos,
  populacao,
  ativos_por_10k_hab
from {{ ref('mart_concorrencia_municipio') }}
where cnae_principal = '4741500' and uf = 'ES'
order by ranking_uf nulls last, municipio
