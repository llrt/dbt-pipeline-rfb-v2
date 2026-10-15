{# ---
id: gq_staging__perfil_municipio__01
conceito: perfil_municipio
camada: staging
perguntas:
  - "A população de Fundão cresceu nos últimos anos?"
  - "Qual a série de população estimada de um município?"
intencao: "Auditoria: a série anual da estimativa de população de um município na Base dos Dados (o gold guarda só o `ano_populacao`)."
tabelas: [stg_bd__populacao]
colunas_chave: [id_municipio, sigla_uf, ano, populacao]
armadilhas:
  - "Só auditoria e série: o gold (`dim_municipio.populacao`) guarda um ano só; use-o para pergunta de negócio."
  - "O município é o código IBGE de 7 dígitos (`id_municipio`), sem nome: ache o código em `dim_municipio.id_municipio_ibge` pelo nome E pela UF."
  - "Estimativa ≠ Censo: a série não inclui a contagem do Censo 2022 (`dim_municipio.populacao_censo_2022`)."
variacoes:
  - "Outro município: troque o código IBGE."
  - "PIB por ano: `stg_bd__pib` (`id_municipio`, `ano`, `pib`), na mesma forma."
resposta_esperada_fixtures:
  colunas: [id_municipio, sigla_uf, ano, populacao]
  linhas:
    - ['3202207', ES, 2023, 19000]
    - ['3202207', ES, 2024, 20000]
--- #}
{{ config(
    tags=['escopo_adicao', 'golden_query', 'incremento_enriquecimento_bd'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_bd'}
) }}

select
  id_municipio,
  sigla_uf,
  ano,
  populacao
from {{ ref('stg_bd__populacao') }}
where id_municipio = '3202207'
order by ano
