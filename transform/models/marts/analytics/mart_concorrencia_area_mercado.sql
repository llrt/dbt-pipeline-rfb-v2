-- incremento: enriquecimento_bd (ADR-0015, ENR-03). Concorrência na área de mercado. Grão = CNAE
-- principal × município (os mesmos pares de `mart_concorrencia_municipio`: município sem o CNAE não
-- aparece). Para cada par: ativos/inativos no município, nos vizinhos (`bridge_municipio_vizinho`) e
-- na região metropolitana (município incluído; NULL fora de região metropolitana). Indicadores por
-- mil domicílios e por km² (Censo 2022) do município e da área de mercado (município + vizinhos);
-- NULL quando falta o denominador no município ou em qualquer vizinho (nunca zero, nunca parcial).
with base as (
  select * from {{ ref('mart_concorrencia_municipio') }}
),

municipios as (
  select
    sk_municipio,
    nome_regiao_metropolitana,
    domicilios_2022,
    area_km2
  from {{ ref('dim_municipio') }}
),

vizinhos as (
  select
    base.sk_cnae,
    base.sk_municipio,
    count(*) as qtd_vizinhos,
    count(viz.domicilios_2022) as vizinhos_com_censo,
    sum(coalesce(vizb.ativos, 0))::bigint as ativos_vizinhos,
    sum(coalesce(vizb.inativos, 0))::bigint as inativos_vizinhos,
    sum(viz.domicilios_2022) as domicilios_vizinhos,
    sum(viz.area_km2) as area_km2_vizinhos
  from base
  inner join {{ ref('bridge_municipio_vizinho') }} as bri
    on base.sk_municipio = bri.sk_municipio
  inner join municipios as viz
    on bri.sk_municipio_vizinho = viz.sk_municipio
  left join base as vizb
    on bri.sk_municipio_vizinho = vizb.sk_municipio and base.sk_cnae = vizb.sk_cnae
  group by base.sk_cnae, base.sk_municipio
),

regioes as (
  select
    base.sk_cnae,
    mun.nome_regiao_metropolitana,
    sum(base.ativos)::bigint as ativos_regiao_metropolitana,
    sum(base.inativos)::bigint as inativos_regiao_metropolitana
  from base
  inner join municipios as mun
    on base.sk_municipio = mun.sk_municipio
  where mun.nome_regiao_metropolitana not in ('NÃO PERTENCE', 'NÃO INFORMADO')
  group by base.sk_cnae, mun.nome_regiao_metropolitana
),

area as (
  select
    base.sk_cnae,
    base.cnae_principal,
    base.desc_cnae_principal,
    base.sk_municipio,
    base.municipio,
    base.uf,
    mun.nome_regiao_metropolitana,
    mun.domicilios_2022,
    mun.area_km2,
    base.ativos,
    base.inativos,
    coalesce(viz.qtd_vizinhos, 0) as qtd_vizinhos,
    coalesce(viz.ativos_vizinhos, 0) as ativos_vizinhos,
    coalesce(viz.inativos_vizinhos, 0) as inativos_vizinhos,
    reg.ativos_regiao_metropolitana,
    reg.inativos_regiao_metropolitana,
    -- denominadores da área (município + vizinhos); NULL se algum membro não tem Censo
    case
      when coalesce(viz.qtd_vizinhos, 0) = coalesce(viz.vizinhos_com_censo, 0)
        then mun.domicilios_2022 + coalesce(viz.domicilios_vizinhos, 0)
    end as domicilios_area,
    case
      when coalesce(viz.qtd_vizinhos, 0) = coalesce(viz.vizinhos_com_censo, 0)
        then mun.area_km2 + coalesce(viz.area_km2_vizinhos, 0)
    end as area_km2_area
  from base
  inner join municipios as mun
    on base.sk_municipio = mun.sk_municipio
  left join vizinhos as viz
    on base.sk_cnae = viz.sk_cnae and base.sk_municipio = viz.sk_municipio
  left join regioes as reg
    on base.sk_cnae = reg.sk_cnae and mun.nome_regiao_metropolitana = reg.nome_regiao_metropolitana
)

select
  sk_cnae,
  cnae_principal,
  desc_cnae_principal,
  sk_municipio,
  municipio,
  uf,
  nome_regiao_metropolitana,
  domicilios_2022,
  area_km2,
  ativos,
  inativos,
  qtd_vizinhos,
  ativos_vizinhos,
  inativos_vizinhos,
  ativos_regiao_metropolitana,
  inativos_regiao_metropolitana,
  round(ativos * 1000.0 / nullif(domicilios_2022, 0), 6) as ativos_por_mil_domicilios,
  round(ativos / nullif(area_km2, 0), 6) as ativos_por_km2,
  round(
    (ativos + ativos_vizinhos) * 1000.0 / nullif(domicilios_area, 0), 6
  ) as ativos_area_por_mil_domicilios,
  round((ativos + ativos_vizinhos) / nullif(area_km2_area, 0), 6) as ativos_area_por_km2
from area
