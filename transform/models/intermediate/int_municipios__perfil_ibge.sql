-- incremento: enriquecimento_ibge
-- Perfil do município com as fontes do IBGE, uma linha por município de `int_municipios__conformados`
-- (base das colunas novas de `dim_municipio`): renda do Censo 2022, valor adicionado (VA) por atividade,
-- hierarquia urbana e polo de compras da REGIC 2018 e o total do CEMPRE. NULL onde a fonte não tem o
-- município (ou está vazia, no modo offline sem `ibge/`).
--
-- VA: `ano_va` é o último ano com as quatro aberturas preenchidas, independente de `ano_pib` (o IBGE
-- publica o PIB total antes das aberturas por atividade). As participações `pct_va_*` são sobre a soma das
-- quatro aberturas (0–100). Polo de compras: o destino listado com maior % em móveis e eletroeletrônicos
-- (Q2, a melhor proxy de bem durável e material de construção), `posto` 1 de `int_regic__destinos_compras`.
with municipios as (
  select
    id_municipio_ibge,
    nome_municipio
  from {{ ref('int_municipios__conformados') }}
),

ano_va as (
  select max(ano) as ano
  from {{ ref('stg_bd__pib') }}
  where
    va_agropecuaria is not null
    and va_industria is not null
    and va_servicos is not null
    and va_adespss is not null
),

va as (
  select
    pib.id_municipio,
    pib.ano,
    pib.va_agropecuaria,
    pib.va_industria,
    pib.va_servicos,
    pib.va_adespss,
    pib.va_agropecuaria + pib.va_industria + pib.va_servicos + pib.va_adespss as va_soma
  from {{ ref('stg_bd__pib') }} as pib
  inner join ano_va on pib.ano = ano_va.ano
),

polo as (
  select
    id_municipio_origem,
    id_municipio_destino,
    pct
  from {{ ref('int_regic__destinos_compras') }}
  where tema = 'moveis_eletro' and posto = 1
),

ano_cempre as (
  select max(ano) as ano from {{ ref('stg_ibge__cempre_municipio_total') }}
),

cempre as (
  select
    tot.id_municipio,
    tot.ano,
    tot.unidades_locais,
    tot.pessoal_ocupado
  from {{ ref('stg_ibge__cempre_municipio_total') }} as tot
  inner join ano_cempre on tot.ano = ano_cempre.ano
)

select
  mun.id_municipio_ibge,
  ren.renda_per_capita_media as renda_per_capita_media_2022,
  ren.renda_per_capita_mediana as renda_per_capita_mediana_2022,
  ren.moradores as moradores_renda_2022,
  va.ano as ano_va,
  va.va_agropecuaria,
  va.va_industria,
  va.va_servicos,
  va.va_adespss as va_adm_publica,
  round(va.va_agropecuaria * 100.0 / nullif(va.va_soma, 0), 2) as pct_va_agropecuaria,
  round(va.va_industria * 100.0 / nullif(va.va_soma, 0), 2) as pct_va_industria,
  round(va.va_servicos * 100.0 / nullif(va.va_soma, 0), 2) as pct_va_servicos,
  round(va.va_adespss * 100.0 / nullif(va.va_soma, 0), 2) as pct_va_adm_publica,
  hie.codigo_hierarquia as regic_hierarquia_codigo,
  hie.nome_hierarquia as regic_hierarquia,
  hie.nome_arranjo_populacional as regic_arranjo_populacional,
  hie.regiao_influencia as regic_regiao_influencia,
  atr.indice_atracao as regic_indice_atracao,
  polo.id_municipio_destino as id_municipio_polo_compras,
  destino.nome_municipio as nome_municipio_polo_compras,
  polo.pct as pct_compras_no_polo,
  cem.ano as ano_cempre,
  cem.unidades_locais as unidades_locais_cempre,
  cem.pessoal_ocupado as pessoal_ocupado_cempre
from municipios as mun
left join {{ ref('stg_ibge__renda_municipio') }} as ren
  on mun.id_municipio_ibge = ren.id_municipio and ren.ano = 2022
left join va
  on mun.id_municipio_ibge = va.id_municipio
left join {{ ref('stg_ibge__regic_hierarquia') }} as hie
  on mun.id_municipio_ibge = hie.id_municipio
left join {{ ref('stg_ibge__regic_atracao') }} as atr
  on mun.id_municipio_ibge = atr.id_municipio
left join polo
  on mun.id_municipio_ibge = polo.id_municipio_origem
left join municipios as destino
  on polo.id_municipio_destino = destino.id_municipio_ibge
left join cempre as cem
  on mun.id_municipio_ibge = cem.id_municipio
