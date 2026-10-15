{# ---
id: gq_analytics__cempre_setor__03
conceito: cempre_setor
camada: analytics
perguntas:
  - "Quanto se paga de salário no comércio de tintas no ES?"
  - "Qual o salário médio de cada setor no Espírito Santo?"
  - "Quanto ganha em média um empregado de loja de tinta na Serra?"
intencao: "Salário médio mensal aproximado (CEMPRE) por classe CNAE numa UF, somando só as células com salário e assalariados publicados, e quantas ficaram fora."
tabelas: [mart_emprego_setor_municipio]
colunas_chave: [uf, classe_cnae, ano_cempre, salarios_mil_reais, pessoal_assalariado_cempre, tem_sigilo]
armadilhas:
  - "Salário médio mensal ≈ `salarios_mil_reais * 1000 / pessoal_assalariado_cempre / 13` (o ano do CEMPRE tem 13 salários). É do assalariado, não do pessoal ocupado (que inclui sócios e donos), em reais nominais do `ano_cempre`."
  - "Na agregação, numerador e denominador vêm das MESMAS células: some salário e assalariados só onde os dois foram publicados. `sum(salarios) / sum(assalariados)` em todas as células infla o denominador com as que têm salário NULL e subestima o salário."
  - "Salário NULL nem sempre vem com `tem_sigilo` (nas fixtures, Linhares na classe 01113 tem 8 assalariados e salário NULL sem sigilo): filtre pelos campos, não por `tem_sigilo`. Declare quantas células ficaram fora."
  - "É o salário das unidades formais do CEMPRE (sem MEI), não a renda do morador (`renda_per_capita_*`, Censo 2022)."
variacoes:
  - "Um município: acrescente `and municipio = 'Serra'` ao filtro da CTE (a UF já está nele); com uma célula, a fórmula é a da própria célula."
  - "Uma classe: `and classe_cnae = '47415'` (5 dígitos)."
  - "Brasil por UF: troque o filtro de `uf` por um agrupamento por `uf`."
resposta_esperada_fixtures:
  colunas: [classe_cnae, ano_cempre, celulas, celulas_com_salario, assalariados_com_salario, salario_medio_mensal]
  linhas:
    - ['01113', 2024, 2, 0, null, null]
    - ['20517', 2024, 1, 1, 15, 2051.28]
    - ['20711', 2024, 2, 0, null, null]
    - ['35115', 2024, 1, 0, null, null]
    - ['46796', 2024, 2, 2, 115, 2876.25]
    - ['47113', 2024, 2, 1, 55, 2097.9]
    - ['47415', 2024, 5, 2, 311, 3029.93]
    - ['47440', 2024, 1, 1, 60, 2179.49]
--- #}
{{ config(
    tags=['escopo_adicao', 'golden_query', 'incremento_enriquecimento_ibge'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_ibge'}
) }}

with celulas as (
  select
    classe_cnae,
    ano_cempre,
    salarios_mil_reais,
    pessoal_assalariado_cempre,
    coalesce(salarios_mil_reais is not null and pessoal_assalariado_cempre > 0, false) as tem_salario
  from {{ ref('mart_emprego_setor_municipio') }}
  where uf = 'ES'
)

select
  classe_cnae,
  ano_cempre,
  count(*) as celulas,
  count(*) filter (where tem_salario) as celulas_com_salario,
  sum(pessoal_assalariado_cempre) filter (where tem_salario) as assalariados_com_salario,
  round(
    sum(salarios_mil_reais) filter (where tem_salario) * 1000
    / nullif(sum(pessoal_assalariado_cempre) filter (where tem_salario), 0) / 13,
    2
  ) as salario_medio_mensal
from celulas
group by classe_cnae, ano_cempre
order by classe_cnae
