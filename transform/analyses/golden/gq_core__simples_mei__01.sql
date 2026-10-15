{# ---
id: gq_core__simples_mei__01
conceito: simples_mei
camada: core
perguntas:
  - "Quantos MEI ativos há em cada UF?"
  - "Que parte dos ativos é MEI?"
  - "Quantos ativos são optantes do Simples?"
intencao: "Ativos por UF com MEI, optantes do Simples e a participação do MEI, no mês do gold."
tabelas: [fct_estabelecimentos, dim_municipio]
colunas_chave: [opcao_mei, opcao_simples, eh_ativa, sigla_uf]
armadilhas:
  - "MEI se conta por `opcao_mei`, nunca pela natureza 2135 nem pelo porte MICRO."
  - "Conta estabelecimentos: há MEI com filial no dado real (RN-05); para empresas MEI filtre `eh_matriz`."
  - "A flag é a situação no extrato; todo MEI é optante do Simples, o contrário não."
  - "Empresa sem linha no arquivo Simples vira `false` nas duas flags."
variacoes:
  - "Um CNAE ou município: junte a dimensão e filtre."
  - "Série mensal: use fct_resumo_mensal (`opcao_mei`, `qtd_ativos`) ou a métrica `qtd_ativos_mei`."
resposta_esperada_fixtures:
  colunas: [sigla_uf, ativos, ativos_mei, ativos_simples, pct_mei]
  linhas:
    - [AL, 1, 0, 1, 0.0]
    - [ES, 8, 2, 8, 25.0]
    - [NI, 2, 0, 2, 0.0]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  mun.sigla_uf,
  count(*) as ativos,
  count(*) filter (where fct.opcao_mei) as ativos_mei,
  count(*) filter (where fct.opcao_simples) as ativos_simples,
  round(count(*) filter (where fct.opcao_mei) * 100.0 / count(*), 1) as pct_mei
from {{ ref('fct_estabelecimentos') }} as fct
inner join {{ ref('dim_municipio') }} as mun
  on fct.sk_municipio = mun.sk_municipio
where fct.eh_ativa
group by mun.sigla_uf
order by mun.sigla_uf
