{# ---
id: gq_core__dinamica_mercado__01
conceito: dinamica_mercado
camada: core
perguntas:
  - "Quantas empresas abriram e quantas fecharam por ano?"
  - "Qual o saldo de aberturas e fechamentos em cada ano?"
intencao: "Aberturas (data de início), encerramentos (não ativos pela data da situação) e baixas por ano, com o saldo, como na regra de mart_dinamica_mercado."
tabelas: [fct_estabelecimentos, dim_data]
colunas_chave: [sk_data_inicio_atividade, sk_data_situacao, eh_ativa, sk_situacao_cadastral]
armadilhas:
  - "Empresa × estabelecimento: conta estabelecimentos (CNPJ completo), não empresas. Se o usuário quer empresas (CNPJ básico), filtre `fct.eh_matriz` (uma matriz por empresa) ou conte `distinct left(cnpj_completo, 8)`; se não está claro, declare a escolha na resposta."
  - "Encerramento no projeto = todo não ativo (nula, suspensa, inapta, baixada); 'fechou de vez' = só baixa (código 8)."
  - "Eventos são derivados do extrato corrente: um inapto reativado deixa de contar; quem sumiu do cadastro não entra."
  - "O último ano é parcial e lotes de inaptidão distorcem um ano: compare períodos completos."
variacoes:
  - "Por CNAE e município com a regra pronta: use mart_dinamica_mercado (gq_analytics__dinamica_mercado__01)."
  - "Por mês: troque `ano` por `ano_mes`."
resposta_esperada_fixtures:
  colunas: [ano, aberturas, encerramentos, baixas, saldo]
  linhas:
    - [2000, 2, 0, 0, 2]
    - [2005, 1, 0, 0, 1]
    - [2008, 1, 0, 0, 1]
    - [2010, 1, 0, 0, 1]
    - [2012, 1, 0, 0, 1]
    - [2015, 1, 0, 0, 1]
    - [2016, 1, 0, 0, 1]
    - [2018, 2, 0, 0, 2]
    - [2019, 2, 1, 1, 1]
    - [2020, 1, 1, 1, 0]
    - [2021, 1, 1, 1, 0]
    - [2022, 1, 0, 0, 1]
    - [2023, 1, 1, 0, 0]
    - [2024, 1, 1, 1, 0]
    - [2026, 0, 1, 1, -1]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

with eventos as (
  select
    ini.ano,
    1 as abertura,
    0 as encerramento,
    0 as baixa
  from {{ ref('fct_estabelecimentos') }} as fct
  inner join {{ ref('dim_data') }} as ini
    on fct.sk_data_inicio_atividade = ini.sk_data
  where ini.ano is not null
  union all
  select
    sit.ano,
    0 as abertura,
    1 as encerramento,
    case when fct.sk_situacao_cadastral = 8 then 1 else 0 end as baixa
  from {{ ref('fct_estabelecimentos') }} as fct
  inner join {{ ref('dim_data') }} as sit
    on fct.sk_data_situacao = sit.sk_data
  where not fct.eh_ativa and sit.ano is not null
)

select
  ano,
  sum(abertura) as aberturas,
  sum(encerramento) as encerramentos,
  sum(baixa) as baixas,
  sum(abertura) - sum(encerramento) as saldo
from eventos
group by ano
order by ano
