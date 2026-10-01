-- Estabelecimentos do mês selecionado enriquecidos com empresa, Simples/MEI e os pares nos
-- domínios (natureza RFB, CNAE BD, município BD). Diferente de `bh_empresas` (inner joins), os joins
-- são LEFT: nada é descartado; a ausência de par vira flag `tem_*` e a fato mapeia para o membro
-- -1 das dimensões. Base de `fct_estabelecimentos` e da bridge de CNAEs secundários.
with estabelecimentos as (
  select * from {{ ref('stg_rfb__estabelecimentos') }}
),

empresas as (
  select * from {{ ref('stg_rfb__empresas') }}
),

simples as (
  select * from {{ ref('stg_rfb__simples') }}
),

naturezas as (
  select * from {{ ref('stg_rfb__naturezas') }}
),

cnaes_bd as (
  select * from {{ ref('stg_bd__cnaes') }}
),

-- `id_municipio_rf` só tem `unique` como warn no BD: se repetir, fica o menor id IBGE, para o
-- join não multiplicar estabelecimentos.
municipios_bd as (
  select
    codigo_rfb,
    id_municipio_ibge
  from {{ ref('int_municipios__conformados') }}
  qualify row_number() over (partition by codigo_rfb order by id_municipio_ibge) = 1
)

select
  est.cnpj_completo,
  est.cnpj_raiz,
  est.matriz_filial_codigo,
  est.situacao_codigo,
  est.dat_inicio_atividade,
  est.dat_situacao,
  est.cnae_principal,
  est.cnaes_secundarios_lista,
  est.municipio_rfb_codigo,
  mun.id_municipio_ibge,
  emp.natureza_juridica_codigo,
  emp.porte_codigo,
  emp.capital_social,
  coalesce(sim.opcao_simples, false) as opcao_simples,
  coalesce(sim.opcao_mei, false) as opcao_mei,
  emp.cnpj_raiz is not null as tem_empresa,
  nat.codigo is not null as tem_natureza,
  cnae.subclasse is not null as tem_cnae_bd,
  mun.codigo_rfb is not null as tem_municipio_bd,
  est._mes_referencia,
  est._data_referencia
from estabelecimentos as est
left join empresas as emp
  on est.cnpj_raiz = emp.cnpj_raiz
left join simples as sim
  on est.cnpj_raiz = sim.cnpj_raiz
left join naturezas as nat
  on emp.natureza_juridica_codigo = nat.codigo
left join cnaes_bd as cnae
  on est.cnae_principal = cnae.subclasse
left join municipios_bd as mun
  on est.municipio_rfb_codigo = mun.codigo_rfb
