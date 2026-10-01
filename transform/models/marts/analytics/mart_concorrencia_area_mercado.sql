-- incremento: enriquecimento_bd (ADR-0015, ENR-03; P23/AD-028). Concorrência na área de mercado.
-- Grão = CNAE principal × município em que o município tem ao menos um estabelecimento do CNAE
-- (os pares de `mart_concorrencia_municipio`) OU algum vizinho (`bridge_municipio_vizinho`) ou a
-- região metropolitana tem ao menos um ATIVO do CNAE: o segundo caso são os vazios de mercado, com
-- ativos = inativos = 0 no município e `tem_estabelecimento_local` = false. Para cada par:
-- ativos/inativos no município, nos vizinhos e na região metropolitana (município incluído; NULL
-- fora de região metropolitana). Indicadores por mil domicílios e por km² (Censo 2022) do município
-- (0 nos vazios com denominador, NULL sem denominador) e da área de mercado (município + vizinhos);
-- Vazios só para CNAE e município conhecidos (`sk_cnae`/`sk_municipio` <> -1); os pares locais com -1
-- ficam como antes.
-- NULL quando falta o denominador no município ou em qualquer vizinho (nunca parcial).
with base as (
  select * from {{ ref('mart_concorrencia_municipio') }}
),

municipios as (
  select
    sk_municipio,
    nome_municipio,
    sigla_uf,
    nome_regiao_metropolitana,
    domicilios_2022,
    area_km2
  from {{ ref('dim_municipio') }}
),

cnaes as (
  select distinct
    sk_cnae,
    cnae_principal,
    desc_cnae_principal
  from base
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

-- pares candidatos: os locais (base), os vizinhos de quem tem ativo do CNAE e os municípios das
-- regiões metropolitanas com ativo do CNAE; `union` deduplica e os vazios entram aqui
pares as (
  select
    sk_cnae,
    sk_municipio
  from base
  union
  select
    bas.sk_cnae,
    bri.sk_municipio
  from base as bas
  inner join {{ ref('bridge_municipio_vizinho') }} as bri
    on bas.sk_municipio = bri.sk_municipio_vizinho
  where bas.ativos > 0 and bas.sk_cnae <> -1 and bri.sk_municipio <> -1
  union
  select
    reg.sk_cnae,
    mun.sk_municipio
  from regioes as reg
  inner join municipios as mun
    on reg.nome_regiao_metropolitana = mun.nome_regiao_metropolitana
  where reg.ativos_regiao_metropolitana > 0 and reg.sk_cnae <> -1 and mun.sk_municipio <> -1
),

vizinhos as (
  select
    par.sk_cnae,
    par.sk_municipio,
    count(*) as qtd_vizinhos,
    count(viz.domicilios_2022) as vizinhos_com_censo,
    sum(coalesce(vizb.ativos, 0))::bigint as ativos_vizinhos,
    sum(coalesce(vizb.inativos, 0))::bigint as inativos_vizinhos,
    sum(viz.domicilios_2022) as domicilios_vizinhos,
    sum(viz.area_km2) as area_km2_vizinhos
  from pares as par
  inner join {{ ref('bridge_municipio_vizinho') }} as bri
    on par.sk_municipio = bri.sk_municipio
  inner join municipios as viz
    on bri.sk_municipio_vizinho = viz.sk_municipio
  left join base as vizb
    on bri.sk_municipio_vizinho = vizb.sk_municipio and par.sk_cnae = vizb.sk_cnae
  group by par.sk_cnae, par.sk_municipio
),

area as (
  select
    par.sk_cnae,
    cnae.cnae_principal,
    cnae.desc_cnae_principal,
    par.sk_municipio,
    mun.nome_municipio as municipio,
    mun.sigla_uf as uf,
    mun.nome_regiao_metropolitana,
    mun.domicilios_2022,
    mun.area_km2,
    loc.sk_cnae is not null as tem_estabelecimento_local,
    coalesce(loc.ativos, 0) as ativos,
    coalesce(loc.inativos, 0) as inativos,
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
  from pares as par
  inner join cnaes as cnae
    on par.sk_cnae = cnae.sk_cnae
  inner join municipios as mun
    on par.sk_municipio = mun.sk_municipio
  left join base as loc
    on par.sk_cnae = loc.sk_cnae and par.sk_municipio = loc.sk_municipio
  left join vizinhos as viz
    on par.sk_cnae = viz.sk_cnae and par.sk_municipio = viz.sk_municipio
  left join regioes as reg
    on par.sk_cnae = reg.sk_cnae and mun.nome_regiao_metropolitana = reg.nome_regiao_metropolitana
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
  tem_estabelecimento_local,
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
