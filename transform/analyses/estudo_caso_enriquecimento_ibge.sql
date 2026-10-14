{{ config(
    tags=['escopo_adicao', 'incremento_enriquecimento_ibge'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_ibge'}
) }}

-- Incremento enriquecimento_ibge (ADR-0022): o caso com as fontes do IBGE. Três linhas: o município do
-- caso, o seu polo de compras (REGIC 2018, maior % em móveis e eletroeletrônicos) e a UF inteira, com a
-- renda per capita do Censo 2022, a hierarquia urbana, os ativos do CNAE do caso (RFB, mês do gold) e o
-- CEMPRE da classe do CNAE (5 primeiros dígitos). Na UF, a renda é a média dos municípios ponderada pelos
-- moradores e o pessoal ocupado soma só as células sem sigilo (subestima). Só agregados (ADR-0008).
{% set classe = var('caso_cnae_alvo')[:5] -%}
with caso as (
  select *
  from {{ ref('dim_municipio') }}
  where upper(nome_municipio) = '{{ var("caso_municipio") }}' and sigla_uf = '{{ var("caso_uf") }}'
),

municipios as (
  select
    mun.sk_municipio,
    mun.nome_municipio,
    mun.sigla_uf,
    mun.regic_hierarquia,
    mun.renda_per_capita_media_2022,
    mun.renda_per_capita_mediana_2022,
    mun.moradores_renda_2022,
    mun.nome_municipio_polo_compras,
    mun.pct_compras_no_polo,
    coalesce(con.ativos, 0) as ativos_cnae,
    emp.ano_cempre,
    emp.unidades_locais_cempre,
    emp.pessoal_ocupado_cempre,
    emp.tem_sigilo
  from {{ ref('dim_municipio') }} as mun
  left join {{ ref('mart_concorrencia_municipio') }} as con
    on mun.sk_municipio = con.sk_municipio and con.cnae_principal = '{{ var("caso_cnae_alvo") }}'
  left join {{ ref('mart_emprego_setor_municipio') }} as emp
    on mun.sk_municipio = emp.sk_municipio and emp.classe_cnae = '{{ classe }}'
  where mun.sigla_uf = '{{ var("caso_uf") }}'
)

select
  1 as ordem,
  'município do caso' as escopo,
  mun.nome_municipio as municipio,
  mun.regic_hierarquia,
  mun.renda_per_capita_media_2022,
  mun.renda_per_capita_mediana_2022,
  mun.nome_municipio_polo_compras as polo_compras,
  mun.pct_compras_no_polo,
  mun.ativos_cnae,
  mun.unidades_locais_cempre,
  mun.pessoal_ocupado_cempre,
  mun.tem_sigilo,
  mun.ano_cempre
from municipios as mun
inner join caso on mun.sk_municipio = caso.sk_municipio

union all

select
  2 as ordem,
  'polo de compras' as escopo,
  mun.nome_municipio as municipio,
  mun.regic_hierarquia,
  mun.renda_per_capita_media_2022,
  mun.renda_per_capita_mediana_2022,
  mun.nome_municipio_polo_compras as polo_compras,
  mun.pct_compras_no_polo,
  mun.ativos_cnae,
  mun.unidades_locais_cempre,
  mun.pessoal_ocupado_cempre,
  mun.tem_sigilo,
  mun.ano_cempre
from municipios as mun
inner join caso on mun.sk_municipio::varchar = caso.id_municipio_polo_compras

union all

select
  3 as ordem,
  'UF' as escopo,
  max(sigla_uf) as municipio,
  null as regic_hierarquia,
  (
    sum(renda_per_capita_media_2022 * moradores_renda_2022) / nullif(sum(moradores_renda_2022), 0)
  )::decimal(12, 2) as renda_per_capita_media_2022,
  null as renda_per_capita_mediana_2022,
  null as polo_compras,
  null as pct_compras_no_polo,
  sum(ativos_cnae) as ativos_cnae,
  sum(unidades_locais_cempre) as unidades_locais_cempre,
  sum(pessoal_ocupado_cempre) as pessoal_ocupado_cempre,
  coalesce(bool_or(tem_sigilo), false) as tem_sigilo,
  max(ano_cempre) as ano_cempre
from municipios

order by ordem
