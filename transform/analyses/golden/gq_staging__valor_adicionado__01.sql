{# ---
id: gq_staging__valor_adicionado__01
conceito: valor_adicionado
camada: staging
perguntas:
  - "Até que ano há PIB municipal e até que ano há valor adicionado por atividade?"
  - "Por que o VA é de 2021 se o PIB vai até 2023?"
intencao: "Linhagem: por ano do PIB dos Municípios, quantos municípios têm PIB e quantos têm as quatro aberturas do VA."
tabelas: [stg_bd__pib]
colunas_chave: [id_municipio, ano, pib, va_servicos]
armadilhas:
  - "As aberturas do VA saem depois do PIB total: `ano_va` (hoje 2021) é diferente de `ano_pib` (hoje 2023)."
  - "Para o perfil do município use dim_municipio (`pct_va_*`, `ano_va`), em gq_core__valor_adicionado__01."
variacoes:
  - "Um município: `where id_municipio = '3202207'`."
resposta_esperada_fixtures:
  colunas: [ano, municipios_com_pib, municipios_com_va_completo]
  linhas:
    - [2021, 8, 8]
--- #}
{{ config(
    tags=['escopo_adicao', 'golden_query', 'incremento_enriquecimento_ibge'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_ibge'}
) }}

select
  ano,
  count(pib) as municipios_com_pib,
  count(*) filter (
    where
    va_agropecuaria is not null
    and va_industria is not null
    and va_servicos is not null
    and va_adespss is not null
  ) as municipios_com_va_completo
from {{ ref('stg_bd__pib') }}
group by ano
order by ano
