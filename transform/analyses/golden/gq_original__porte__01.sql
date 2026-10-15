{# ---
id: gq_original__porte__01
conceito: porte
camada: original
perguntas:
  - "Qual o porte e a idade média das lojas de tintas ativas em Fundão, como no notebook 4?"
  - "Paridade das perguntas 2 e 3 do MVP (idade e porte dos concorrentes)."
intencao: "Paridade com o MVP (notebook 4, Q2/Q3): estabelecimentos e idade média por porte e situação, para o caso, em agg_empresas (média ponderada por `qtd_empresas`)."
tabelas: [agg_empresas]
colunas_chave: [cnae_principal, municipio, uf, porte, situacao, qtd_empresas, media_idade]
armadilhas:
  - "Município em MAIÚSCULAS como no original; `media_idade` é NULL para INATIVA (a idade só existe para ATIVA)."
  - "`agg_empresas` traz médias por estrato (as 10 dimensões); agregar exige ponderar por `qtd_empresas`: `sum(media_idade * qtd_empresas) / sum(qtd_empresas) filter (where media_idade is not null)`. `avg(media_idade)` dá o mesmo peso a um estrato de 1 e a um de 1000 estabelecimentos."
  - "A ponderação supõe que todo estabelecimento de um estrato com média tem `idade_atual` (vale hoje: no gold real toda ATIVA tem data de início). Na dúvida, a média direto de `bh_empresas` (`avg(idade_atual)`) é exata e dá o mesmo número."
  - "O notebook 4 do MVP (e `estudo_caso_q2_q3_idade_porte`, que o reproduz) usa `avg(media_idade)`, a média de médias: no dado real a idade daqui pode diferir da do relatório do MVP, e a certa é esta."
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
  round(
    sum(media_idade * qtd_empresas)
    / nullif(sum(qtd_empresas) filter (where media_idade is not null), 0),
    1
  ) as media_idade
from {{ ref('agg_empresas') }}
where cnae_principal = '4741500' and municipio = 'FUNDÃO' and uf = 'ES'
group by porte, situacao
order by situacao, porte
