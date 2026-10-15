{# ---
id: gq_original__concorrencia_densidade__01
conceito: concorrencia_densidade
camada: original
perguntas:
  - "Quantos concorrentes de loja de tintas há em Fundão, pelo modelo original do MVP?"
  - "Paridade da pergunta 1 do notebook 4."
intencao: "Paridade com o MVP (notebook 4, Q1): concorrentes do CNAE do caso no município, ATIVA × INATIVA, em agg_empresas."
tabelas: [agg_empresas]
colunas_chave: [cnae_principal, municipio, uf, situacao, qtd_empresas]
armadilhas:
  - "Só paridade: para pergunta nova use mart_concorrencia_municipio (gq_analytics__concorrencia_densidade__01), que tem densidade e ranking."
  - "`municipio` em MAIÚSCULAS ('FUNDÃO')."
variacoes:
  - "Outro caso: troque CNAE, município e UF."
resposta_esperada_fixtures:
  colunas: [situacao, qtd_empresas]
  linhas:
    - [ATIVA, 1]
    - [INATIVA, 4]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  situacao,
  sum(qtd_empresas) as qtd_empresas
from {{ ref('agg_empresas') }}
where cnae_principal = '4741500' and municipio = 'FUNDÃO' and uf = 'ES'
group by situacao
order by situacao
