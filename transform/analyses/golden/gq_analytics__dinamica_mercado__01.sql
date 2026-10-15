{# ---
id: gq_analytics__dinamica_mercado__01
conceito: dinamica_mercado
camada: analytics
perguntas:
  - "Quantas lojas de tintas abriram e fecharam em Fundão por ano?"
  - "O mercado de tintas em Fundão está crescendo ou encolhendo?"
intencao: "Aberturas, encerramentos e saldo por ano de um CNAE num município, com a regra pronta de mart_dinamica_mercado."
tabelas: [mart_dinamica_mercado]
colunas_chave: [ano, cnae_principal, municipio, uf, aberturas, encerramentos, saldo]
armadilhas:
  - "Encerramento = não ativo pela data da situação (inclui inapta e suspensa), não só baixa."
  - "Só anos com evento aparecem: ano sem linha é zero, não falta de dado."
  - "O último ano é parcial; lotes de inaptidão distorcem um ano."
  - "Filtre município E UF: `municipio` é o nome com acento, como em dim_municipio ('Fundão')."
variacoes:
  - "UF inteira: tire o filtro de `municipio` e some por ano."
  - "Por seção ou classe: use fct_estabelecimentos + dim_cnae (gq_core__dinamica_mercado__01)."
resposta_esperada_fixtures:
  colunas: [ano, aberturas, encerramentos, saldo]
  linhas:
    - [2010, 1, 0, 1]
    - [2015, 1, 0, 1]
    - [2018, 1, 0, 1]
    - [2019, 0, 1, -1]
    - [2020, 1, 0, 1]
    - [2021, 0, 1, -1]
    - [2022, 1, 0, 1]
    - [2023, 0, 1, -1]
    - [2024, 0, 1, -1]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  ano,
  aberturas,
  encerramentos,
  saldo
from {{ ref('mart_dinamica_mercado') }}
where cnae_principal = '4741500' and municipio = 'Fundão' and uf = 'ES'
order by ano
