{# ---
id: gq_raw__natureza_juridica__01
conceito: natureza_juridica
camada: raw
perguntas:
  - "O que a RFB publicou como descrição da natureza jurídica 2135?"
  - "Qual o nome oficial do código de natureza jurídica 2062 no domínio da Receita?"
intencao: "Auditoria do raw: a descrição publicada no domínio Naturezas para um código, no mês mais recente."
tabelas: [rfb.naturezas]
colunas_chave: [_mes_referencia, codigo, descricao]
armadilhas:
  - "Para recortar estabelecimentos por natureza use dim_natureza_juridica (gq_core__natureza_juridica__01)."
  - "MEI não é natureza jurídica: quase todo MEI é 2135, mas o filtro de MEI é `opcao_mei`."
  - "O código é texto de 4 dígitos ('2135'); no gold `sk_natureza_juridica` é inteiro."
variacoes:
  - "Outro código: troque a lista do `in`."
  - "Busca por texto: `where descricao ilike '%limitada%'`."
resposta_esperada_fixtures:
  colunas: [codigo, descricao]
  linhas:
    - ['2062', Sociedade Empresária Limitada]
    - ['2135', Empresário (Individual)]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  fon.codigo,
  fon.descricao
from {{ source('rfb', 'naturezas') }} as fon
where
  fon._mes_referencia = (select max(ult._mes_referencia) from {{ source('rfb', 'naturezas') }} as ult)
  and fon.codigo in ('2062', '2135')
order by fon.codigo
