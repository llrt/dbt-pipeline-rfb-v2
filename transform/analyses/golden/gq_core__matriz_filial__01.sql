{# ---
id: gq_core__matriz_filial__01
conceito: matriz_filial
camada: core
perguntas:
  - "Quantas matrizes e quantas filiais ativas há em cada UF?"
  - "Quantas filiais existem no Espírito Santo?"
intencao: "Estabelecimentos ativos por UF separados em matriz e filial."
tabelas: [fct_estabelecimentos, dim_municipio]
colunas_chave: [eh_matriz, eh_ativa, sk_municipio, sigla_uf]
armadilhas:
  - "A filial pode estar em UF diferente da matriz: contar empresas por UF pelas matrizes põe a empresa na UF da sede."
  - "Use `eh_matriz`, nunca a ordem '0001' do CNPJ (CNPJ alfanumérico)."
  - "A UF 'NI' é o membro -1 (estabelecimento sem município conhecido, ex.: exterior)."
variacoes:
  - "Todos, não só ativos: tire o `where`."
  - "Por município: agrupe também por `nome_municipio`."
resposta_esperada_fixtures:
  colunas: [sigla_uf, matrizes_ativas, filiais_ativas]
  linhas:
    - [AL, 1, 0]
    - [ES, 7, 1]
    - [NI, 2, 0]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  mun.sigla_uf,
  count(*) filter (where fct.eh_matriz) as matrizes_ativas,
  count(*) filter (where not fct.eh_matriz) as filiais_ativas
from {{ ref('fct_estabelecimentos') }} as fct
inner join {{ ref('dim_municipio') }} as mun
  on fct.sk_municipio = mun.sk_municipio
where fct.eh_ativa
group by mun.sigla_uf
order by mun.sigla_uf
