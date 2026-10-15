{# ---
id: gq_raw__municipio_geografia__01
conceito: municipio_geografia
camada: raw
perguntas:
  - "Qual o código RFB do município de Fundão?"
  - "Como a Receita escreve o nome do município de código 5643?"
intencao: "Auditoria do raw: o domínio Municípios da RFB (código de 4 dígitos, nome em maiúsculas), que NÃO é o código IBGE."
tabelas: [rfb.municipios]
colunas_chave: [_mes_referencia, codigo, descricao]
armadilhas:
  - "O código da RFB (4 dígitos) não é o código IBGE (7 dígitos); o gold usa o IBGE em `sk_municipio`."
  - "Nomes repetem entre UFs (Água Branca existe em AL, PB e PI): sempre filtre também a UF no gold."
  - "Comparar nome exige maiúsculas dos dois lados (`upper`); o domínio da RFB é em maiúsculas e sem a UF."
variacoes:
  - "Outro município: troque o nome no `where`."
resposta_esperada_fixtures:
  colunas: [codigo, descricao]
  linhas:
    - ['1003', AGUA BRANCA]
    - ['1901', AGUA BRANCA]
    - ['2701', AGUA BRANCA]
    - ['5643', FUNDAO]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  fon.codigo,
  fon.descricao
from {{ source('rfb', 'municipios') }} as fon
where
  fon._mes_referencia = (select max(ult._mes_referencia) from {{ source('rfb', 'municipios') }} as ult)
  and upper(fon.descricao) in ('FUNDAO', 'FUNDÃO', 'AGUA BRANCA', 'ÁGUA BRANCA')
order by fon.codigo
