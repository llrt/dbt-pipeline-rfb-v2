{# ---
id: gq_raw__cempre_setor__01
conceito: cempre_setor
camada: raw
perguntas:
  - "O que o IBGE publicou do CEMPRE para lojas de tintas no ES?"
  - "Confira no raw onde o CEMPRE veio com sigilo (X)."
intencao: "Auditoria do raw: os valores publicados pela API SIDRA (tabela 9528) para a classe 47.41-5, inclusive o símbolo X de sigilo."
tabelas: [ibge.cempre_municipio_cnae, ibge.cempre_categorias_cnae]
colunas_chave: [d1c, d2c, d3c, d4c, v]
armadilhas:
  - "Camada de auditoria: os valores tratados (NULL e `tem_sigilo` no lugar do X) estão em gq_analytics__cempre_setor__01."
  - "Formato longo da SIDRA: d1c município IBGE, d2c variável (706 unidades locais, 707 pessoal ocupado, 708 assalariados, 662 salários), d3c ano, d4c categoria CNAE."
  - "X é sigilo: nunca imputar (nem zero, nem média)."
variacoes:
  - "Outra classe: troque o prefixo do `d4n` ('47.41-5')."
  - "Outro município: filtre `d1c` pelo código IBGE (7 dígitos)."
resposta_esperada_fixtures:
  colunas: [id_municipio, variavel, ano, valor_publicado]
  linhas:
    - ['2200202', '706', '2024', '-']
    - ['2200202', '707', '2024', '-']
    - ['2500106', '706', '2024', '-']
    - ['2500106', '707', '2024', '-']
    - ['2700102', '706', '2024', '-']
    - ['2700102', '707', '2024', '-']
    - ['3200607', '706', '2024', '3']
    - ['3200607', '707', '2024', X]
    - ['3202207', '706', '2024', '-']
    - ['3202207', '707', '2024', '-']
    - ['3203205', '706', '2024', '12']
    - ['3203205', '707', '2024', X]
    - ['3205002', '706', '2024', '33']
    - ['3205002', '707', '2024', '196']
    - ['3205309', '706', '2024', '25']
    - ['3205309', '707', '2024', '164']
--- #}
{{ config(
    tags=['escopo_adicao', 'golden_query', 'incremento_enriquecimento_ibge'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_ibge'}
) }}

select
  val.d1c as id_municipio,
  val.d2c as variavel,
  val.d3c as ano,
  val.v as valor_publicado
from {{ source('ibge', 'cempre_municipio_cnae') }} as val
inner join {{ source('ibge', 'cempre_categorias_cnae') }} as cat
  on val.d4c = cat.d4c
where cat.d4n like '47.41-5 %' and val.d2c in ('706', '707')
order by val.d1c, val.d2c, val.d3c
