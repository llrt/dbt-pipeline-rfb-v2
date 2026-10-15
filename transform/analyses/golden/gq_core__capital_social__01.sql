{# ---
id: gq_core__capital_social__01
conceito: capital_social
camada: core
perguntas:
  - "Qual o capital social total e médio das empresas de cada UF?"
  - "Quanto capital têm as empresas ativas do Espírito Santo?"
intencao: "Capital social somado só nas matrizes (uma por empresa), total e médio por empresa, por UF da matriz."
tabelas: [fct_estabelecimentos, dim_municipio]
colunas_chave: [capital_social, eh_matriz, sk_municipio, sigla_uf]
armadilhas:
  - "O capital é da EMPRESA e se repete em cada estabelecimento: somar todos os estabelecimentos conta a empresa várias vezes. Some só `eh_matriz`."
  - "É o capital declarado no registro, não faturamento nem patrimônio."
  - "Média por empresa = soma das matrizes ÷ número de matrizes."
variacoes:
  - "Só ativas: `and fct.eh_ativa`."
  - "Por CNAE ou porte: junte a dimensão."
resposta_esperada_fixtures:
  colunas: [sigla_uf, empresas, capital_social_total, capital_social_medio]
  linhas:
    - [AL, 1, 1000.0, 1000.0]
    - [ES, 12, 12000.5, 1000.04]
    - [NI, 2, 2000.0, 1000.0]
    - [PB, 1, 1000.0, 1000.0]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  mun.sigla_uf,
  count(*) as empresas,
  sum(fct.capital_social) as capital_social_total,
  round(avg(fct.capital_social), 2) as capital_social_medio
from {{ ref('fct_estabelecimentos') }} as fct
inner join {{ ref('dim_municipio') }} as mun
  on fct.sk_municipio = mun.sk_municipio
where fct.eh_matriz
group by mun.sigla_uf
order by mun.sigla_uf
