{# ---
id: gq_core__regic_polo_compras__01
conceito: regic_polo_compras
camada: core
perguntas:
  - "Onde o pessoal de Fundão vai comprar?"
  - "Para onde os moradores de Fundão vão comprar móveis e roupas?"
  - "Qual o polo de compras de Fundão?"
intencao: "Destinos de compra de um município na REGIC 2018 (bridge_municipio_destino_compras), por tema, com o percentual e o destino 'Outros'."
tabelas: [bridge_municipio_destino_compras, dim_municipio]
colunas_chave: [sk_municipio_origem, sk_municipio_destino, tema, pct, posto, eh_outros]
armadilhas:
  - "O % divide os deslocamentos ENTRE OS DESTINOS DE FORA: '45 % em Serra' não é 45 % de toda a compra de Fundão."
  - "O destino 'Outros' (lugares não listados) tem `sk_municipio_destino` = -1 e `eh_outros`; nunca é polo."
  - "REGIC é de 2018, malha de 2018; os 67 municípios mais centrais (Vitória, Vila Velha, Serra no ES) não têm destinos nem polo."
  - "Temas: `moveis_eletro` (Q2, base do polo) e `vestuario_calcados` (Q1)."
variacoes:
  - "Só o polo: `dim_municipio.nome_municipio_polo_compras` e `pct_compras_no_polo`."
  - "Outro município: troque nome e UF da origem."
resposta_esperada_fixtures:
  colunas: [tema, posto, destino, pct]
  linhas:
    - [moveis_eletro, 1, Serra, 45.0]
    - [moveis_eletro, 2, Vitória, 38.333333]
    - [moveis_eletro, 3, Aracruz, 16.666667]
    - [vestuario_calcados, 1, Serra, 46.666667]
    - [vestuario_calcados, 2, Vitória, 30.0]
    - [vestuario_calcados, 3, Aracruz, 16.666667]
    - [vestuario_calcados, null, Outros, 6.666667]
--- #}
{{ config(
    tags=['escopo_adicao', 'golden_query', 'incremento_enriquecimento_ibge'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_ibge'}
) }}

select
  bri.tema,
  bri.posto,
  case when bri.eh_outros then 'Outros' else des.nome_municipio end as destino,
  bri.pct
from {{ ref('bridge_municipio_destino_compras') }} as bri
inner join {{ ref('dim_municipio') }} as ori
  on bri.sk_municipio_origem = ori.sk_municipio
inner join {{ ref('dim_municipio') }} as des
  on bri.sk_municipio_destino = des.sk_municipio
where ori.nome_municipio = 'Fundão' and ori.sigla_uf = 'ES'
order by bri.tema, bri.posto nulls last, destino
