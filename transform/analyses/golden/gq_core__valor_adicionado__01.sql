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
  - "Sem VA (as quatro participações NULL, ou alguma faltando), `predominante` é NULL: ausência de dado não é atividade. Nunca use `else '<atividade>'` no CASE; cada ramo testa a sua participação."
  - "Empate (participações iguais, já arredondadas a 2 casas) fica com a primeira na ordem serviços, indústria, agropecuária, administração pública; mostre as participações ao responder."
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

with va as (
  select
    nome_municipio,
    ano_va,
    pct_va_agropecuaria,
    pct_va_industria,
    pct_va_servicos,
    pct_va_adm_publica,
    -- A maior participação só existe com as quatro; sem VA (ou com uma faltando) fica NULL.
    case
      when
        pct_va_agropecuaria is not null and pct_va_industria is not null
        and pct_va_servicos is not null and pct_va_adm_publica is not null
        then greatest(pct_va_agropecuaria, pct_va_industria, pct_va_servicos, pct_va_adm_publica)
    end as maior_pct
  from {{ ref('dim_municipio') }}
  where sigla_uf = 'ES'
)

select
  nome_municipio,
  ano_va,
  pct_va_agropecuaria,
  pct_va_industria,
  pct_va_servicos,
  pct_va_adm_publica,
  -- Sem `else`: sem VA, nenhum ramo casa e a atividade sai NULL. Empate: vence o primeiro ramo.
  case
    when pct_va_servicos = maior_pct then 'serviços'
    when pct_va_industria = maior_pct then 'indústria'
    when pct_va_agropecuaria = maior_pct then 'agropecuária'
    when pct_va_adm_publica = maior_pct then 'administração pública'
  end as predominante
from va
order by nome_municipio
