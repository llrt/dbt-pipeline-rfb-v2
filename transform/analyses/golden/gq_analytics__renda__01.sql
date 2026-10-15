{# ---
id: gq_analytics__renda__01
conceito: renda
camada: analytics
perguntas:
  - "Onde há renda alta e pouca concorrência de lojas de tintas no ES?"
  - "Qual município rico tem poucas lojas de tinta?"
intencao: "Renda per capita (Censo 2022) ao lado da densidade de concorrência de um CNAE, por município da UF."
tabelas: [mart_concorrencia_municipio, dim_municipio]
colunas_chave: [sk_municipio, renda_per_capita_media_2022, ativos_por_10k_hab]
armadilhas:
  - "Renda de 2022 (nominal) × ativos do mês do gold: compare ordens de grandeza, não anos."
  - "Só municípios com algum estabelecimento do CNAE; os vazios estão em mart_concorrencia_area_mercado."
  - "Sinal para investigar, não conclusão (o morador pode comprar no polo)."
variacoes:
  - "Mediana em vez de média: `renda_per_capita_mediana_2022`."
resposta_esperada_fixtures:
  colunas: [municipio, renda_per_capita_media_2022, ativos, ativos_por_10k_hab]
  linhas:
    - [Serra, 1720.1, 1, 0.02]
    - [Fundão, 1406.78, 1, 0.5]
--- #}
{{ config(
    tags=['escopo_adicao', 'golden_query', 'incremento_enriquecimento_ibge'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_ibge'}
) }}

select
  con.municipio,
  mun.renda_per_capita_media_2022,
  con.ativos,
  con.ativos_por_10k_hab
from {{ ref('mart_concorrencia_municipio') }} as con
inner join {{ ref('dim_municipio') }} as mun
  on con.sk_municipio = mun.sk_municipio
where con.cnae_principal = '4741500' and con.uf = 'ES'
order by mun.renda_per_capita_media_2022 desc, con.municipio asc
