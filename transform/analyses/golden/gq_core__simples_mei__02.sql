{# ---
id: gq_core__simples_mei__02
conceito: simples_mei
camada: core
perguntas:
  - "Quantas pequenas empresas ativas existem?"
  - "Quantas micro e pequenas empresas são do Simples?"
intencao: "Ativos por porte × regime (MEI, Simples sem MEI, fora do Simples): 'pequena empresa' pode ser porte ou regime."
tabelas: [fct_estabelecimentos, dim_porte]
colunas_chave: [sk_porte, rotulo_porte, opcao_mei, opcao_simples]
armadilhas:
  - "'Pequena empresa' é ambíguo: porte PEQUENA (EPP), porte MICRO+PEQUENA (ME/EPP), optante do Simples ou MEI. Mostre a quebra ou pergunte."
  - "Porte é declarado; Simples e MEI são opções de tributação da empresa."
variacoes:
  - "Só empresas: `and fct.eh_matriz`."
resposta_esperada_fixtures:
  colunas: [rotulo_porte, regime, ativos]
  linhas:
    - [DEMAIS, Simples sem MEI, 2]
    - [MICRO, MEI, 2]
    - [MICRO, Simples sem MEI, 2]
    - [N/A, Simples sem MEI, 2]
    - [PEQUENA, Simples sem MEI, 3]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  por.rotulo_porte,
  case
    when fct.opcao_mei then 'MEI'
    when fct.opcao_simples then 'Simples sem MEI'
    else 'fora do Simples'
  end as regime,
  count(*) as ativos
from {{ ref('fct_estabelecimentos') }} as fct
inner join {{ ref('dim_porte') }} as por
  on fct.sk_porte = por.sk_porte
where fct.eh_ativa
group by all
order by por.rotulo_porte, regime
