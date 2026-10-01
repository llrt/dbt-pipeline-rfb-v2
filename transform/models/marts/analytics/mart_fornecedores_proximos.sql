-- ANA-04: fornecedores ativos por distância. Parametrizado pelas vars do caso (`caso_municipio`,
-- `caso_uf`, `caso_cnaes_fornecedores`, `raio_fornecedores_km`). Um fornecedor é um estabelecimento
-- ATIVO cujo CNAE principal ou secundário está em `caso_cnaes_fornecedores` e cujo município fica a
-- até `raio_fornecedores_km` do centroide do município do caso (haversine entre centroides BD; sem
-- geocodificação por endereço). Grão = estabelecimento; `via` = 'principal' se o CNAE principal casa,
-- senão 'secundario' (o menor CNAE secundário que casa). Fornecedores sem centroide ficam de fora.
{%- set cnaes = var('caso_cnaes_fornecedores') %}
with caso as (
  select
    latitude,
    longitude
  from {{ ref('dim_municipio') }}
  where upper(nome_municipio) = upper('{{ var("caso_municipio") }}') and sigla_uf = '{{ var("caso_uf") }}'
),

candidatos as (
  select
    est.cnpj_completo,
    est.cnae_principal as cnae_fornecido,
    'principal' as via,
    1 as prioridade
  from {{ ref('int_estabelecimentos__enriquecidos') }} as est
  where est.cnae_principal in ({{ cnaes | map('tojson') | join(', ') | replace('"', "'") }})

  union all

  select
    est.cnpj_completo,
    bri.codigo_cnae_secundario as cnae_fornecido,
    'secundario' as via,
    2 as prioridade
  from {{ ref('bridge_estabelecimento_cnae_secundario') }} as bri
  inner join {{ ref('int_estabelecimentos__enriquecidos') }} as est
    on bri.cnpj_completo = est.cnpj_completo
  where bri.codigo_cnae_secundario in ({{ cnaes | map('tojson') | join(', ') | replace('"', "'") }})
),

escolhidos as (
  select
    cnpj_completo,
    cnae_fornecido,
    via
  from candidatos
  qualify row_number() over (partition by cnpj_completo order by prioridade, cnae_fornecido) = 1
),

fornecedores as (
  select
    fct.cnpj_completo,
    esc.cnae_fornecido,
    esc.via,
    fct.sk_municipio,
    mun.nome_municipio as municipio,
    mun.sigla_uf as uf,
    round(
      {{ haversine_km('caso.latitude', 'caso.longitude', 'mun.latitude', 'mun.longitude') }}, 2
    ) as distancia_km
  from {{ ref('fct_estabelecimentos') }} as fct
  inner join escolhidos as esc
    on fct.cnpj_completo = esc.cnpj_completo
  inner join {{ ref('dim_municipio') }} as mun
    on fct.sk_municipio = mun.sk_municipio
  cross join caso
  where fct.eh_ativa and mun.latitude is not null
)

select
  frn.cnpj_completo,
  coalesce(est.nome_fantasia, emp.razao_social) as nome,
  coalesce(cnae.sk_cnae, -1) as sk_cnae,
  frn.cnae_fornecido,
  frn.via,
  frn.sk_municipio,
  frn.municipio,
  frn.uf,
  frn.distancia_km
from fornecedores as frn
inner join {{ ref('stg_rfb__estabelecimentos') }} as est
  on frn.cnpj_completo = est.cnpj_completo
left join {{ ref('stg_rfb__empresas') }} as emp
  on est.cnpj_raiz = emp.cnpj_raiz
left join {{ ref('dim_cnae') }} as cnae
  on frn.cnae_fornecido = cnae.codigo_subclasse
where frn.distancia_km <= {{ var('raio_fornecedores_km') }}
