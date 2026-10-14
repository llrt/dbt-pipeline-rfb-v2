{{ config(
    tags=['escopo_adicao', 'incremento_enriquecimento_ibge'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_ibge'}
) }}

-- Cenário 1 (docs/CENARIOS_DE_USO.md), incremento enriquecimento_ibge: renda × concorrência. Municípios da
-- UF do caso com renda per capita média (Censo 2022) acima da mediana dos municípios da UF, do menos ao mais
-- concorrido no CNAE do caso (ativos por 10 mil habitantes; 0 sem ativo). `abaixo_da_mediana_densidade`
-- marca os que têm densidade abaixo ou igual à mediana da UF: candidatos a mercado subatendido. Só
-- agregados por município (ADR-0008). Renda nominal de 2022; ativos do mês do gold.
with municipios as (
  select
    mun.sk_municipio,
    mun.nome_municipio,
    mun.populacao,
    mun.renda_per_capita_media_2022,
    coalesce(con.ativos, 0) as ativos,
    round(coalesce(con.ativos, 0) * 10000.0 / nullif(mun.populacao, 0), 2) as ativos_por_10k_hab
  from {{ ref('dim_municipio') }} as mun
  left join {{ ref('mart_concorrencia_municipio') }} as con
    on mun.sk_municipio = con.sk_municipio and con.cnae_principal = '{{ var("caso_cnae_alvo") }}'
  where mun.sigla_uf = '{{ var("caso_uf") }}'
),

medianas as (
  select
    median(renda_per_capita_media_2022) as mediana_renda_uf,
    median(ativos_por_10k_hab) as mediana_densidade_uf
  from municipios
)

select
  mun.nome_municipio as municipio,
  mun.renda_per_capita_media_2022,
  med.mediana_renda_uf,
  mun.populacao,
  mun.ativos,
  mun.ativos_por_10k_hab,
  med.mediana_densidade_uf,
  mun.ativos_por_10k_hab <= med.mediana_densidade_uf as abaixo_da_mediana_densidade
from municipios as mun
cross join medianas as med
where mun.renda_per_capita_media_2022 > med.mediana_renda_uf
order by mun.ativos_por_10k_hab asc nulls last, mun.renda_per_capita_media_2022 desc, municipio asc
