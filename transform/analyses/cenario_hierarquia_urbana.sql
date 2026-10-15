{{ config(
    tags=['escopo_adicao', 'incremento_enriquecimento_ibge'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_ibge'}
) }}

-- Cenário 5 (docs/uso/cenarios.md), incremento enriquecimento_ibge: o CNAE do caso na rede urbana. No
-- Brasil, por nível da hierarquia da REGIC 2018 (1A Grande Metrópole Nacional … 5 Centro Local): quantos
-- municípios, quantos deles têm ativo do CNAE, os ativos e a densidade por 10 mil habitantes do nível. A
-- REGIC é de 2018 (municípios criados depois ficam em "sem classificação"). Só agregados.
with municipios as (
  select
    coalesce(mun.regic_hierarquia_codigo, '—') as codigo,
    coalesce(mun.regic_hierarquia, 'sem classificação') as hierarquia,
    mun.populacao,
    coalesce(con.ativos, 0) as ativos
  from {{ ref('dim_municipio') }} as mun
  left join {{ ref('mart_concorrencia_municipio') }} as con
    on mun.sk_municipio = con.sk_municipio and con.cnae_principal = '{{ var("caso_cnae_alvo") }}'
  where mun.sk_municipio <> -1
)

select
  codigo as regic_hierarquia_codigo,
  hierarquia as regic_hierarquia,
  count(*) as municipios,
  count(*) filter (where ativos > 0) as municipios_com_ativo,
  sum(ativos) as ativos,
  sum(populacao) as populacao,
  round(sum(ativos) * 10000.0 / nullif(sum(populacao), 0), 2) as ativos_por_10k_hab
from municipios
group by codigo, hierarquia
order by codigo
