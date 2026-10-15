{# ---
id: gq_core__situacao_cadastral__02
conceito: situacao_cadastral
camada: core
perguntas:
  - "Quantas empresas fecharam por ano? Foram baixas ou inaptidões?"
  - "Quantos estabelecimentos foram baixados em cada ano?"
  - "Quantas lojas fecharam de vez?"
intencao: "Estabelecimentos não ativos pelo ano da data da situação, separando baixada (fechou de vez) de inapta, suspensa e nula."
tabelas: [fct_estabelecimentos, dim_situacao_cadastral, dim_data]
colunas_chave: [eh_ativa, sk_data_situacao, rotulo_situacao_cadastral, ano]
armadilhas:
  - "'Fechou' é ambíguo: baixa (definitiva) × inaptidão/suspensão (reversíveis). Pergunte ou mostre a quebra."
  - "Inaptidões chegam em lote numa data só (ADE): um ano com lote parece de mercado em queda."
  - "Data ausente (-1) ou anterior a 1900 (-2) tem `ano` NULL na dim_data e fica fora; o ano do extrato é parcial."
  - "Só o extrato corrente: um inapto reativado deixa de aparecer; quem sumiu do cadastro não entra."
variacoes:
  - "Só baixas: `and sit.rotulo_situacao_cadastral = 'BAIXADA'`."
  - "Por CNAE ou município: junte a dimensão e filtre."
  - "Por mês: troque `dat.ano` por `dat.ano_mes`."
resposta_esperada_fixtures:
  colunas: [ano, rotulo_situacao_cadastral, estabelecimentos]
  linhas:
    - [2019, BAIXADA, 1]
    - [2020, BAIXADA, 1]
    - [2021, BAIXADA, 1]
    - [2023, INAPTA, 1]
    - [2024, BAIXADA, 1]
    - [2026, BAIXADA, 1]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  dat.ano,
  sit.rotulo_situacao_cadastral,
  count(*) as estabelecimentos
from {{ ref('fct_estabelecimentos') }} as fct
inner join {{ ref('dim_situacao_cadastral') }} as sit
  on fct.sk_situacao_cadastral = sit.sk_situacao_cadastral
inner join {{ ref('dim_data') }} as dat
  on fct.sk_data_situacao = dat.sk_data
where not fct.eh_ativa and dat.ano is not null
group by dat.ano, sit.rotulo_situacao_cadastral
order by dat.ano, sit.rotulo_situacao_cadastral
