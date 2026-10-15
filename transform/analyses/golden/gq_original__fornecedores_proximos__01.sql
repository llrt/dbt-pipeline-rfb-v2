{# ---
id: gq_original__fornecedores_proximos__01
conceito: fornecedores_proximos
camada: original
perguntas:
  - "Quantos fabricantes de tinta há na microrregião de Fundão, como o MVP buscava?"
  - "Paridade da pergunta 4 do notebook 4 (fornecedores na micro e mesorregião)."
intencao: "Paridade com o MVP (notebook 4, Q4): fornecedores ativos (CNAE principal) do caso por microrregião e mesorregião em bh_empresas."
tabelas: [bh_empresas]
colunas_chave: [cnae_principal, situacao, microrregiao_municipio, mesorregiao_municipio]
armadilhas:
  - "Compare a microrregião em maiúsculas dos dois lados (R3-04): 'LINHARES' × 'Linhares' nunca casa."
  - "Só o CNAE principal; o original não via secundários. Para pergunta nova use mart_fornecedores_proximos (raio em km)."
  - "Nunca selecione `nome` nem `cnpj_completo` aqui."
variacoes:
  - "Mesorregião: agrupe por `mesorregiao_municipio`."
resposta_esperada_fixtures:
  colunas: [microrregiao_municipio, mesorregiao_municipio, cnae_principal, fornecedores_ativos]
  linhas:
    - [LINHARES, LITORAL NORTE ESPÍRITO-SANTENSE, '2071100', 1]
    - [VITÓRIA, CENTRAL ESPÍRITO-SANTENSE, '2071100', 1]
    - [VITÓRIA, CENTRAL ESPÍRITO-SANTENSE, '4679601', 1]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  microrregiao_municipio,
  mesorregiao_municipio,
  cnae_principal,
  count(*) as fornecedores_ativos
from {{ ref('bh_empresas') }}
where situacao = 'ATIVA' and cnae_principal in ('2071100', '4679601', '4679699') and uf = 'ES'
group by microrregiao_municipio, mesorregiao_municipio, cnae_principal
order by microrregiao_municipio, mesorregiao_municipio, cnae_principal
