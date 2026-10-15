{# ---
id: gq_core__data_calendario__01
conceito: data_calendario
camada: core
perguntas:
  - "Como evoluiu o número de estabelecimentos ativos mês a mês?"
  - "Quantos ativos havia em agosto e em setembro?"
  - "Quantos ativos tem hoje?"
intencao: "Série mensal da fotografia (fct_resumo_mensal): ativos e total por mês de referência, com a variação para o mês anterior."
tabelas: [fct_resumo_mensal]
colunas_chave: [mes_referencia, qtd_ativos, qtd_estabelecimentos]
armadilhas:
  - "Cada mês é uma fotografia do cadastro inteiro: NUNCA some meses; num ano vale o último mês."
  - "'Hoje' = o mês mais recente do gold, não a data atual; diga o mês de referência na resposta."
  - "fct_resumo_mensal guarda todos os meses (uma partição por mês); fct_estabelecimentos e os marts só o mês corrente."
  - "O resumo não tem natureza jurídica nem cnpj: para isso, a fato detalhada (só o mês corrente)."
variacoes:
  - "Um recorte: junte as dimensões por `sk_municipio`, `sk_cnae`, `sk_porte` e filtre antes de somar dentro do mês."
  - "Só o mês corrente: `where mes_referencia = (select max(mes_referencia) from ...)`."
resposta_esperada_fixtures:
  colunas: [mes_referencia, ativos, estabelecimentos, variacao_ativos]
  linhas:
    - [2026-08, 10, 17, null]
    - [2026-09, 11, 18, 1]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

with mensal as (
  select
    mes_referencia,
    sum(qtd_ativos) as ativos,
    sum(qtd_estabelecimentos) as estabelecimentos
  from {{ ref('fct_resumo_mensal') }}
  group by mes_referencia
)

select
  mes_referencia,
  ativos,
  estabelecimentos,
  ativos - lag(ativos) over (order by mes_referencia) as variacao_ativos
from mensal
order by mes_referencia
