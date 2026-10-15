{# ---
id: gq_core__valor_adicionado__01
conceito: valor_adicionado
camada: core
perguntas:
  - "Fundão vive de quê: serviços, indústria ou agro?"
  - "Qual o perfil econômico dos municípios do ES?"
intencao: "Participação do valor adicionado por atividade (agro, indústria, serviços, adm. pública) e a atividade predominante, com o ano do VA."
tabelas: [dim_municipio]
colunas_chave: [ano_va, pct_va_agropecuaria, pct_va_industria, pct_va_servicos, pct_va_adm_publica]
armadilhas:
  - "O VA vai até `ano_va` (hoje 2021), o PIB total até `ano_pib` (2023): cite o ano."
  - "VA negativo existe (indústria de Cachoeira Dourada/GO em 2021): aí as participações saem de 0–100."
variacoes:
  - "Um município: filtre nome e UF."
resposta_esperada_fixtures:
  colunas: [nome_municipio, ano_va, pct_va_agropecuaria, pct_va_industria, pct_va_servicos, pct_va_adm_publica, predominante]
  linhas:
    - [Aracruz, 2021, 5.23, 58.82, 29.41, 6.54, indústria]
    - [Fundão, 2021, 6.35, 47.62, 31.75, 14.29, indústria]
    - [Linhares, 2021, 15.87, 35.71, 39.68, 8.73, serviços]
    - [Serra, 2021, 0.58, 46.78, 44.44, 8.19, indústria]
    - [Vitória, 2021, 0.03, 18.52, 67.9, 13.55, serviços]
--- #}
{{ config(
    tags=['escopo_adicao', 'golden_query', 'incremento_enriquecimento_ibge'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_ibge'}
) }}

select
  nome_municipio,
  ano_va,
  pct_va_agropecuaria,
  pct_va_industria,
  pct_va_servicos,
  pct_va_adm_publica,
  case greatest(pct_va_agropecuaria, pct_va_industria, pct_va_servicos, pct_va_adm_publica)
    when pct_va_servicos then 'serviços'
    when pct_va_industria then 'indústria'
    when pct_va_agropecuaria then 'agropecuária'
    else 'administração pública'
  end as predominante
from {{ ref('dim_municipio') }}
where sigla_uf = 'ES'
order by nome_municipio
