{# ---
id: gq_raw__cnae_principal__01
conceito: cnae_principal
camada: raw
perguntas:
  - "Como a RFB descreve o CNAE 4741500?"
  - "Que nome a Receita dá à atividade de loja de tintas?"
intencao: "Auditoria do raw: a descrição de uma subclasse no domínio CNAEs da RFB, no mês mais recente."
tabelas: [rfb.cnaes]
colunas_chave: [_mes_referencia, codigo, descricao]
armadilhas:
  - "A hierarquia (seção, divisão, grupo, classe) não está no domínio da RFB: está em dim_cnae (Base dos Dados); use gq_core__cnae_principal__02."
  - "O código tem 7 dígitos (subclasse); a classe do IBGE/CEMPRE tem 5."
variacoes:
  - "Busca por texto: `where descricao ilike '%tinta%'`."
resposta_esperada_fixtures:
  colunas: [codigo, descricao]
  linhas:
    - ['4741500', 'Comercio varejista de tintas, vernizes e materiais para pintura']
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  fon.codigo,
  fon.descricao
from {{ source('rfb', 'cnaes') }} as fon
where
  fon._mes_referencia = (select max(ult._mes_referencia) from {{ source('rfb', 'cnaes') }} as ult)
  and fon.codigo = '4741500'
order by fon.codigo
