{# ---
id: gq_staging__simples_mei__01
conceito: simples_mei
camada: staging
perguntas:
  - "Em que anos as empresas optaram pelo MEI?"
  - "Quantas empresas entraram e saíram do MEI, pela data de opção e de exclusão?"
intencao: "Auditoria do staging: empresas por ano da data de opção pelo MEI, com quantas já têm data de exclusão (as datas não chegam ao gold)."
tabelas: [stg_rfb__simples]
colunas_chave: [cnpj_raiz, dat_opcao_mei, dat_exclusao_mei]
armadilhas:
  - "Empresa × estabelecimento: `stg_rfb__simples` tem uma linha por empresa (CNPJ básico); aqui se contam empresas, não estabelecimentos."
  - "As datas de opção e exclusão só existem no staging; o gold tem a flag do extrato (`opcao_mei`)."
  - "É por EMPRESA, não por estabelecimento; a data de opção pelo Simples pode ser a data de efeito (1º/1 do ano seguinte)."
variacoes:
  - "Simples: troque por `dat_opcao_simples` e `dat_exclusao_simples`."
resposta_esperada_fixtures:
  colunas: [ano_opcao_mei, empresas, com_exclusao]
  linhas:
    - [2007, 2, 0]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  year(dat_opcao_mei) as ano_opcao_mei,
  count(*) as empresas,
  count(dat_exclusao_mei) as com_exclusao
from {{ ref('stg_rfb__simples') }}
where dat_opcao_mei is not null
group by year(dat_opcao_mei)
order by ano_opcao_mei
