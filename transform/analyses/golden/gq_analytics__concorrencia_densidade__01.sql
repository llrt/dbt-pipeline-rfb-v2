{# ---
id: gq_analytics__concorrencia_densidade__01
conceito: concorrencia_densidade
camada: analytics
perguntas:
  - "Fundão tem muita concorrência de loja de tintas?"
  - "Quantas lojas de tintas há por 10 mil habitantes em Fundão?"
intencao: "Ativos, inativos, densidade por 10 mil habitantes e ranking na UF de um CNAE num município (mart_concorrencia_municipio)."
tabelas: [mart_concorrencia_municipio]
colunas_chave: [cnae_principal, municipio, uf, ativos, inativos, ativos_por_10k_hab, ranking_uf]
armadilhas:
  - "Inativo segue a regra do original: toda situação diferente de ATIVA."
  - "Densidade NULL = sem população, nunca zero; o ranking 1 é o MAIS concorrido (maior densidade) da UF."
  - "Município sem nenhum estabelecimento do CNAE não aparece neste mart; os vazios estão em mart_concorrencia_area_mercado."
  - "'Muita' é juízo: compare com a UF (ranking) ou com os vizinhos, e diga o critério."
variacoes:
  - "Outro CNAE ou município: troque os filtros."
  - "Todos da UF: tire o filtro de município e ordene por `ranking_uf` (gq_analytics__concorrencia_densidade__02)."
resposta_esperada_fixtures:
  colunas: [municipio, uf, ativos, inativos, populacao, ativos_por_10k_hab, ranking_uf]
  linhas:
    - [Fundão, ES, 1, 4, 20000, 0.5, 1]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  municipio,
  uf,
  ativos,
  inativos,
  populacao,
  ativos_por_10k_hab,
  ranking_uf
from {{ ref('mart_concorrencia_municipio') }}
where cnae_principal = '4741500' and municipio = 'Fundão' and uf = 'ES'
order by municipio
