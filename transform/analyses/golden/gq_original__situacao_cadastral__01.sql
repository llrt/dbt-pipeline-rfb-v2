{# ---
id: gq_original__situacao_cadastral__01
conceito: situacao_cadastral
camada: original
perguntas:
  - "Quantas empresas ATIVA e INATIVA o agg_empresas mostra no Brasil?"
  - "Paridade: ativos × inativos como no notebook do MVP."
intencao: "Paridade com o MVP: a situação reduzida a ATIVA × INATIVA (regra do original) em agg_empresas."
tabelas: [agg_empresas]
colunas_chave: [situacao, qtd_empresas]
armadilhas:
  - "Empresa × estabelecimento: `qtd_empresas` conta estabelecimentos, apesar do nome."
  - "INATIVA junta nula, suspensa, inapta e baixada."
  - "Só para paridade; para pergunta nova use gq_core__situacao_cadastral__01."
variacoes:
  - "Um CNAE e município: filtre `cnae_principal` e `municipio` (em MAIÚSCULAS, sem acento: 'FUNDAO')."
resposta_esperada_fixtures:
  colunas: [situacao, qtd_empresas]
  linhas:
    - [ATIVA, 8]
    - [INATIVA, 7]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  situacao,
  sum(qtd_empresas) as qtd_empresas
from {{ ref('agg_empresas') }}
group by situacao
order by situacao
