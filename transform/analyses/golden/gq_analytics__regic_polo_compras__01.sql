{# ---
id: gq_analytics__regic_polo_compras__01
conceito: regic_polo_compras
camada: analytics
perguntas:
  - "O pessoal de Fundão compra em Serra; quantas lojas de tintas tem lá?"
  - "Quanta concorrência há no polo de compras de cada município do ES?"
intencao: "Para cada município da UF, o polo de compras (REGIC 2018), o % dos deslocamentos que vão a ele e os ativos do CNAE no município e no polo."
tabelas: [mart_concorrencia_area_mercado]
colunas_chave: [municipio, nome_municipio_polo_compras, pct_compras_no_polo, ativos, ativos_no_polo]
armadilhas:
  - "% no polo = parte dos deslocamentos entre os destinos de FORA, não a fração da demanda que sai."
  - "`ativos_no_polo` NULL = município sem polo (os 67 mais centrais); 0 = o polo não tem o CNAE."
variacoes:
  - "Outro CNAE ou UF: troque os filtros."
resposta_esperada_fixtures:
  colunas: [municipio, nome_municipio_polo_compras, pct_compras_no_polo, ativos, ativos_no_polo]
  linhas:
    - [Aracruz, Vitória, 58.333333, 0, 0]
    - [Fundão, Serra, 45.0, 1, 1]
    - [Serra, null, null, 1, null]
    - [Vitória, null, null, 0, null]
--- #}
{{ config(
    tags=['escopo_adicao', 'golden_query', 'incremento_enriquecimento_ibge'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_ibge'}
) }}

select
  municipio,
  nome_municipio_polo_compras,
  pct_compras_no_polo,
  ativos,
  ativos_no_polo
from {{ ref('mart_concorrencia_area_mercado') }}
where cnae_principal = '4741500' and uf = 'ES'
order by municipio
