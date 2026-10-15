{# ---
id: gq_staging__data_calendario__01
conceito: data_calendario
camada: staging
perguntas:
  - "De que mês é o gold atual e qual a data do extrato?"
  - "Qual a data de referência usada para calcular idades?"
intencao: "O mês selecionado no build (o do gold corrente) e a data de referência do extrato, usada no lugar de now() (ADR-0004)."
tabelas: [stg_rfb__estabelecimentos]
colunas_chave: [_mes_referencia, _data_referencia]
armadilhas:
  - "Toda idade, prazo e 'ano corrente' usa a data de referência, nunca `now()`/`current_date`: o extrato é uma fotografia."
  - "O último mês do extrato é parcial (o de 2026-09 vai até 12/09): não compare o mês corrente com meses completos."
  - "Responda sempre citando o mês de referência."
variacoes:
  - "No gold, o mesmo mês está em `max(mes_referencia)` de fct_resumo_mensal."
resposta_esperada_fixtures:
  colunas: [mes_referencia, data_referencia]
  linhas:
    - [2026-09, '2026-09-12']
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  max(_mes_referencia) as mes_referencia,
  max(_data_referencia) as data_referencia
from {{ ref('stg_rfb__estabelecimentos') }}
order by mes_referencia
