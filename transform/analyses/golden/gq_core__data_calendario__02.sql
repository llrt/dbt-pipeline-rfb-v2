{# ---
id: gq_core__data_calendario__02
conceito: data_calendario
camada: core
perguntas:
  - "Quantos estabelecimentos abriram em cada mês desde 2022?"
  - "Em que dia da semana mais se abre empresa?"
intencao: "Aberturas por mês do ano corrente do extrato, usando dim_data no papel de data de início de atividade."
tabelas: [fct_estabelecimentos, dim_data]
colunas_chave: [sk_data_inicio_atividade, sk_data, ano, mes, ano_mes]
armadilhas:
  - "Empresa × estabelecimento: conta estabelecimentos (CNPJ completo), não empresas. Se o usuário quer empresas (CNPJ básico), filtre `fct.eh_matriz` (uma matriz por empresa) ou conte `distinct left(cnpj_completo, 8)`; se não está claro, declare a escolha na resposta."
  - "dim_data tem papel duplo: junte por `sk_data_inicio_atividade` (abertura) ou por `sk_data_situacao` (evento da situação)."
  - "Os membros -1 (sem data) e -2 (antes de 1900) têm `ano` NULL: filtre `ano is not null`."
  - "O mês do extrato é parcial (vai até a data de referência)."
variacoes:
  - "Dia da semana: agrupe por `dia_semana`."
  - "Outro ano: troque o filtro de `ano`."
resposta_esperada_fixtures:
  colunas: [ano_mes, aberturas]
  linhas:
    - [2022-10, 1]
    - [2023-12, 1]
    - [2024-01, 1]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  dat.ano_mes,
  count(*) as aberturas
from {{ ref('fct_estabelecimentos') }} as fct
inner join {{ ref('dim_data') }} as dat
  on fct.sk_data_inicio_atividade = dat.sk_data
where dat.ano >= 2022
group by dat.ano_mes
order by dat.ano_mes
