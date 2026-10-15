{# ---
id: gq_analytics__area_mercado_vizinhanca__01
conceito: area_mercado_vizinhanca
camada: analytics
perguntas:
  - "Quantas lojas de tintas há em Fundão e nos municípios vizinhos?"
  - "Qual a concorrência na área de mercado de Fundão, por mil domicílios?"
intencao: "Concorrência na área de mercado (município + vizinhos + região metropolitana) de um CNAE, com densidades por mil domicílios e por km²."
tabelas: [mart_concorrencia_area_mercado]
colunas_chave: [cnae_principal, municipio, uf, ativos, ativos_vizinhos, ativos_regiao_metropolitana, ativos_area_por_mil_domicilios]
armadilhas:
  - "Área de mercado = município + vizinhos de fronteira; a região metropolitana é coluna à parte (inclui o próprio município)."
  - "Densidade da área NULL quando falta Censo no município ou em qualquer vizinho (nunca parcial)."
  - "Domicílios e área são do Censo 2022; os ativos do mês do gold."
variacoes:
  - "Outro município ou CNAE: troque os filtros."
resposta_esperada_fixtures:
  colunas: [municipio, uf, ativos, qtd_vizinhos, ativos_vizinhos, ativos_regiao_metropolitana, ativos_por_mil_domicilios, ativos_area_por_mil_domicilios]
  linhas:
    - [Fundão, ES, 1, 2, 1, 2, 0.14892, 0.009675]
--- #}
{{ config(
    tags=['escopo_adicao', 'golden_query', 'incremento_enriquecimento_bd'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_bd'}
) }}

select
  municipio,
  uf,
  ativos,
  qtd_vizinhos,
  ativos_vizinhos,
  ativos_regiao_metropolitana,
  ativos_por_mil_domicilios,
  ativos_area_por_mil_domicilios
from {{ ref('mart_concorrencia_area_mercado') }}
where cnae_principal = '4741500' and municipio = 'Fundão' and uf = 'ES'
order by municipio
