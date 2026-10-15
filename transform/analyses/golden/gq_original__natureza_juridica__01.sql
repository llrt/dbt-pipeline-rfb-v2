{# ---
id: gq_original__natureza_juridica__01
conceito: natureza_juridica
camada: original
perguntas:
  - "Quantos estabelecimentos por natureza jurídica há no agg_empresas?"
  - "Paridade: natureza jurídica como o MVP agregava."
intencao: "Paridade com o MVP: estabelecimentos por natureza jurídica (descrição em maiúsculas) em agg_empresas."
tabelas: [agg_empresas]
colunas_chave: [natureza_juridica, qtd_empresas]
armadilhas:
  - "Descrição em MAIÚSCULAS; quem não tem natureza no domínio foi descartado (inner join)."
  - "Só para paridade; para pergunta nova use gq_core__natureza_juridica__01."
variacoes:
  - "Só ativos: `where situacao = 'ATIVA'`."
resposta_esperada_fixtures:
  colunas: [natureza_juridica, qtd_empresas]
  linhas:
    - [EMPRESA INDIVIDUAL DE RESPONSABILIDADE LIMITADA (DE NATUREZA EMPRESÁRIA), 1]
    - [EMPRESÁRIO (INDIVIDUAL), 4]
    - [SOCIEDADE EMPRESÁRIA LIMITADA, 10]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  natureza_juridica,
  sum(qtd_empresas) as qtd_empresas
from {{ ref('agg_empresas') }}
group by natureza_juridica
order by natureza_juridica
