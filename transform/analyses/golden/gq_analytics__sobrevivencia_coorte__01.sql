{# ---
id: gq_analytics__sobrevivencia_coorte__01
conceito: sobrevivencia_coorte
camada: analytics
perguntas:
  - "Qual a taxa de sobrevivência de lojas de tintas no ES em 1, 3 e 5 anos?"
  - "Quantas lojas de tinta sobrevivem 3 anos no Espírito Santo?"
  - "Loja de tinta costuma fechar rápido?"
intencao: "Taxas de sobrevivência a 1, 3 e 5 anos de um CNAE numa UF, somando os estratos antes de dividir."
tabelas: [mart_sobrevivencia_coorte]
colunas_chave: [ano_coorte, cnae_principal, uf, elegiveis_3a, sobreviventes_3a]
armadilhas:
  - "Taxa = soma dos sobreviventes ÷ soma dos elegíveis; nunca a média das colunas `taxa_*` dos estratos."
  - "Sobrevivente a N anos = ativo hoje OU encerrado depois do aniversário de N anos (não é 'ainda ativo')."
  - "Só coortes elegíveis entram (o ano + N terminou antes da data de referência); a taxa sai NULL sem elegíveis."
  - "O mart é por UF, não por município."
variacoes:
  - "Por coorte: agrupe por `ano_coorte`."
  - "Brasil: tire o filtro de `uf`."
resposta_esperada_fixtures:
  colunas: [elegiveis_1a, taxa_1a, elegiveis_3a, taxa_3a, elegiveis_5a, taxa_5a]
  linhas:
    - [6, 1.0, 5, 0.8, 4, 0.5]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  sum(elegiveis_1a) as elegiveis_1a,
  round(sum(sobreviventes_1a) / nullif(sum(elegiveis_1a), 0), 4) as taxa_1a,
  sum(elegiveis_3a) as elegiveis_3a,
  round(sum(sobreviventes_3a) / nullif(sum(elegiveis_3a), 0), 4) as taxa_3a,
  sum(elegiveis_5a) as elegiveis_5a,
  round(sum(sobreviventes_5a) / nullif(sum(elegiveis_5a), 0), 4) as taxa_5a
from {{ ref('mart_sobrevivencia_coorte') }}
where cnae_principal = '4741500' and uf = 'ES'
order by elegiveis_1a
