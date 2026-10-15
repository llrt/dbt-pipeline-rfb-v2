{# ---
id: gq_original__modelos_originais__02
conceito: modelos_originais
camada: original
perguntas:
  - "Quantos estabelecimentos ativos há por microrregião no agg_empresas?"
  - "Paridade: o agregado do notebook 3 por micro e mesorregião."
intencao: "Paridade com o MVP: agg_empresas somado por UF, mesorregião e microrregião, só ATIVA."
tabelas: [agg_empresas]
colunas_chave: [uf, mesorregiao_municipio, microrregiao_municipio, situacao, qtd_empresas]
armadilhas:
  - "agg_empresas não tem mês: é o mês do gold corrente."
  - "Para pergunta nova use dim_municipio (`nome_microrregiao`) com fct_estabelecimentos."
variacoes:
  - "Só uma UF: `and uf = 'ES'`."
resposta_esperada_fixtures:
  colunas: [uf, mesorregiao_municipio, microrregiao_municipio, ativos]
  linhas:
    - [AL, SERTÃO ALAGOANO, SERRANA DO SERTÃO ALAGOANO, 1]
    - [ES, CENTRAL ESPÍRITO-SANTENSE, VITÓRIA, 3]
    - [ES, LITORAL NORTE ESPÍRITO-SANTENSE, LINHARES, 4]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  uf,
  mesorregiao_municipio,
  microrregiao_municipio,
  sum(qtd_empresas) as ativos
from {{ ref('agg_empresas') }}
where situacao = 'ATIVA'
group by uf, mesorregiao_municipio, microrregiao_municipio
order by uf, mesorregiao_municipio, microrregiao_municipio
