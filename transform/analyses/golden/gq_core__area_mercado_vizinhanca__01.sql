{# ---
id: gq_core__area_mercado_vizinhanca__01
conceito: area_mercado_vizinhanca
camada: core
perguntas:
  - "Quais são os municípios vizinhos de Fundão?"
  - "Quantas lojas de tintas ativas há nos vizinhos de Fundão?"
intencao: "Vizinhos de um município (bridge_municipio_vizinho) e os ativos de um CNAE em cada vizinho."
tabelas: [bridge_municipio_vizinho, dim_municipio, fct_estabelecimentos, dim_cnae]
colunas_chave: [sk_municipio, sk_municipio_vizinho, nome_municipio, sk_cnae]
armadilhas:
  - "A ponte é simétrica e de um ano só (o mais recente da Base dos Dados): não duplique os pares."
  - "Vizinho é fronteira geográfica, não distância nem fluxo de compra (para fluxo, REGIC: gq_core__regic_polo_compras__01)."
  - "A conta pronta (município + vizinhos + região metropolitana, por domicílio e km²) está em mart_concorrencia_area_mercado."
variacoes:
  - "Outro município: troque nome e UF."
  - "Outro CNAE: troque `codigo_subclasse`."
resposta_esperada_fixtures:
  colunas: [nome_municipio_vizinho, sigla_uf, ativos_4741500]
  linhas:
    - [Aracruz, ES, 0]
    - [Serra, ES, 1]
--- #}
{{ config(
    tags=['escopo_adicao', 'golden_query', 'incremento_enriquecimento_bd'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_bd'}
) }}

with ativos as (
  select
    fct.sk_municipio,
    count(*) as ativos
  from {{ ref('fct_estabelecimentos') }} as fct
  inner join {{ ref('dim_cnae') }} as cnae
    on fct.sk_cnae = cnae.sk_cnae
  where fct.eh_ativa and cnae.codigo_subclasse = '4741500'
  group by fct.sk_municipio
)

select
  viz.nome_municipio as nome_municipio_vizinho,
  viz.sigla_uf,
  coalesce(ati.ativos, 0) as ativos_4741500
from {{ ref('bridge_municipio_vizinho') }} as bri
inner join {{ ref('dim_municipio') }} as ori
  on bri.sk_municipio = ori.sk_municipio
inner join {{ ref('dim_municipio') }} as viz
  on bri.sk_municipio_vizinho = viz.sk_municipio
left join ativos as ati
  on bri.sk_municipio_vizinho = ati.sk_municipio
where ori.nome_municipio = 'Fundão' and ori.sigla_uf = 'ES'
order by viz.nome_municipio
