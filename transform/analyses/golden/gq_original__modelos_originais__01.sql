{# ---
id: gq_original__modelos_originais__01
conceito: modelos_originais
camada: original
perguntas:
  - "O resultado do estudo de caso bate com o notebook do MVP?"
  - "Quantas lojas de tintas ativas e qual a idade média em Fundão no bh_empresas?"
intencao: "Paridade com o MVP: o estudo de caso (CNAE 4741500 em Fundão/ES) lido de bh_empresas, ATIVA × INATIVA, com idade média e grupo CNAE."
tabelas: [bh_empresas]
colunas_chave: [cnae_principal, municipio, uf, situacao, idade_atual, grupo_cnae_principal]
armadilhas:
  - "Os originais existem para paridade com o MVP: nunca os use para pergunta nova."
  - "`idade_atual` é relativa à data de referência (ADR-0004), não a `now()` como no MVP."
  - "Textos em MAIÚSCULAS; município 'FUNDÃO'."
variacoes:
  - "Outro caso: troque CNAE, município e UF."
resposta_esperada_fixtures:
  colunas: [grupo_cnae_principal, situacao, estabelecimentos, idade_media]
  linhas:
    - [COMERCIO VAREJISTA DE MATERIAL DE CONSTRUCAO, ATIVA, 1, 3.9]
    - [COMERCIO VAREJISTA DE MATERIAL DE CONSTRUCAO, INATIVA, 4, null]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  grupo_cnae_principal,
  situacao,
  count(*) as estabelecimentos,
  round(avg(idade_atual), 1) as idade_media
from {{ ref('bh_empresas') }}
where cnae_principal = '4741500' and municipio = 'FUNDÃO' and uf = 'ES'
group by grupo_cnae_principal, situacao
order by situacao
