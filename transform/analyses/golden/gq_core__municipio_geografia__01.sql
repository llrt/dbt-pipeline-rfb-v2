{# ---
id: gq_core__municipio_geografia__01
conceito: municipio_geografia
camada: core
perguntas:
  - "Quantos estabelecimentos ativos há em cada região e UF?"
  - "Quantos CNPJs ativos tem a região metropolitana da Grande Vitória?"
intencao: "Ativos por região, UF e região metropolitana (atributos de dim_municipio)."
tabelas: [fct_estabelecimentos, dim_municipio]
colunas_chave: [sk_municipio, nome_regiao, sigla_uf, nome_regiao_metropolitana]
armadilhas:
  - "'Região' é ambíguo: grande região (Sudeste), região metropolitana, intermediária ou imediata (IBGE), meso ou microrregião. Pergunte ou diga qual usou."
  - "'NÃO PERTENCE' = fora de região metropolitana; 'NÃO INFORMADO'/'NI' = membro -1 (sem município)."
  - "`sk_municipio` é o código IBGE; o código RFB de 4 dígitos é outro."
variacoes:
  - "Microrregião: `nome_microrregiao`; região imediata: `nome_regiao_imediata`."
  - "Um CNAE: junte dim_cnae e filtre."
resposta_esperada_fixtures:
  colunas: [nome_regiao, sigla_uf, nome_regiao_metropolitana, ativos]
  linhas:
    - [Nordeste, AL, NÃO PERTENCE, 1]
    - [NÃO INFORMADO, NI, NÃO INFORMADO, 2]
    - [Sudeste, ES, NÃO PERTENCE, 2]
    - [Sudeste, ES, RM Grande Vitória, 6]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  mun.nome_regiao,
  mun.sigla_uf,
  mun.nome_regiao_metropolitana,
  count(*) as ativos
from {{ ref('fct_estabelecimentos') }} as fct
inner join {{ ref('dim_municipio') }} as mun
  on fct.sk_municipio = mun.sk_municipio
where fct.eh_ativa
group by mun.nome_regiao, mun.sigla_uf, mun.nome_regiao_metropolitana
order by mun.nome_regiao, mun.sigla_uf, mun.nome_regiao_metropolitana
