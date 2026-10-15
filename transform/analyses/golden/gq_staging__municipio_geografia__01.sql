{# ---
id: gq_staging__municipio_geografia__01
conceito: municipio_geografia
camada: staging
perguntas:
  - "Qual o código IBGE de Fundão e o código RFB correspondente?"
  - "Quantas Água Branca existem e em que UF?"
intencao: "Linhagem: o diretório de municípios da Base dos Dados, que liga o código RFB (4 dígitos) ao código IBGE (7 dígitos)."
tabelas: [stg_bd__municipios]
colunas_chave: [id_municipio, id_municipio_rf, sigla_uf]
armadilhas:
  - "Nomes de município se repetem entre UFs: sempre filtre a UF junto com o nome."
  - "No gold, `sk_municipio` = código IBGE como inteiro; o código RFB fica em `dim_municipio.codigo_rfb`."
variacoes:
  - "Outro município: troque o nome no `where`."
resposta_esperada_fixtures:
  colunas: [id_municipio, id_municipio_rf, nome_municipio, sigla_uf]
  linhas:
    - ['2700102', '2701', Água Branca, AL]
    - ['3202207', '5643', Fundão, ES]
    - ['2500106', '1901', Água Branca, PB]
    - ['2200202', '1003', Água Branca, PI]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  id_municipio,
  id_municipio_rf,
  nome as nome_municipio,
  sigla_uf
from {{ ref('stg_bd__municipios') }}
where nome in ('Fundão', 'Água Branca')
order by sigla_uf, nome
