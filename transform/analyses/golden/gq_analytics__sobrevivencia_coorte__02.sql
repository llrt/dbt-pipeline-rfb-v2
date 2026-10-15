{# ---
id: gq_analytics__sobrevivencia_coorte__02
conceito: sobrevivencia_coorte
camada: analytics
perguntas:
  - "Empresa maior sobrevive mais? Taxa de sobrevivência em 3 anos por porte."
  - "Microempresa fecha mais que empresa de pequeno porte?"
intencao: "Taxa de sobrevivência a 3 anos por porte, no Brasil (todos os CNAEs), somando os estratos."
tabelas: [mart_sobrevivencia_coorte]
colunas_chave: [porte, elegiveis_3a, sobreviventes_3a]
armadilhas:
  - "Empresa × estabelecimento: a coorte é de estabelecimentos (filiais incluídas), não de empresas; o porte é da empresa, repetido em cada estabelecimento dela."
  - "O porte é o do extrato atual, não o da abertura."
  - "Estrato pequeno dá taxa instável: mostre os elegíveis junto da taxa."
variacoes:
  - "Um CNAE ou UF: acrescente o filtro."
resposta_esperada_fixtures:
  colunas: [porte, elegiveis_3a, sobreviventes_3a, taxa_3a]
  linhas:
    - [DEMAIS, 3, 3, 1.0]
    - [MICRO, 5, 4, 0.8]
    - [N/A, 2, 2, 1.0]
    - [NÃO INFORMADO, 1, 1, 1.0]
    - [PEQUENA, 4, 4, 1.0]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  porte,
  sum(elegiveis_3a) as elegiveis_3a,
  sum(sobreviventes_3a) as sobreviventes_3a,
  round(sum(sobreviventes_3a) / nullif(sum(elegiveis_3a), 0), 4) as taxa_3a
from {{ ref('mart_sobrevivencia_coorte') }}
group by porte
order by porte
