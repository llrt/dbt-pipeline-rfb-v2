{# ---
id: gq_original__porte__01
conceito: porte
camada: original
perguntas:
  - "Qual o porte e a idade média das lojas de tintas ativas em Fundão, como no notebook 4?"
  - "Paridade das perguntas 2 e 3 do MVP (idade e porte dos concorrentes)."
intencao: "Paridade com o MVP (notebook 4, Q2/Q3): estabelecimentos e idade média por porte e situação, para o caso, em agg_empresas."
tabelas: [agg_empresas]
colunas_chave: [cnae_principal, municipio, uf, porte, situacao, qtd_empresas, media_idade]
armadilhas:
  - "Município em MAIÚSCULAS como no original; `media_idade` é média simples e NULL para INATIVA."
  - "Porte vazio sai NULL (no gold é o membro -1 NÃO INFORMADO)."
variacoes:
  - "Outro caso: troque CNAE, município e UF."
resposta_esperada_fixtures:
  colunas: [porte, situacao, qtd_empresas, media_idade]
  linhas:
    - [MICRO, ATIVA, 1, 3.9]
    - [DEMAIS, INATIVA, 1, null]
    - [MICRO, INATIVA, 1, null]
    - [PEQUENA, INATIVA, 1, null]
    - [null, INATIVA, 1, null]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  porte,
  situacao,
  sum(qtd_empresas) as qtd_empresas,
  round(avg(media_idade), 1) as media_idade
from {{ ref('agg_empresas') }}
where cnae_principal = '4741500' and municipio = 'FUNDÃO' and uf = 'ES'
group by porte, situacao
order by situacao, porte
