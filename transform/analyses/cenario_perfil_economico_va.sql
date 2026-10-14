{{ config(
    tags=['escopo_adicao', 'incremento_enriquecimento_ibge'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_ibge'}
) }}

-- Cenário 4 (docs/CENARIOS_DE_USO.md), incremento enriquecimento_ibge: perfil econômico. Municípios da UF
-- do caso pela participação de cada atividade no valor adicionado (PIB dos Municípios, `ano_va`, hoje
-- 2021: as aberturas por atividade saem depois do PIB total), com a atividade predominante e a densidade
-- do CNAE do caso (ativos por 10 mil habitantes). O VA é de um ano, os ativos de outro. Só agregados.
select
  mun.nome_municipio as municipio,
  mun.ano_va,
  mun.pct_va_agropecuaria,
  mun.pct_va_industria,
  mun.pct_va_servicos,
  mun.pct_va_adm_publica,
  case greatest(
    mun.pct_va_agropecuaria, mun.pct_va_industria, mun.pct_va_servicos, mun.pct_va_adm_publica
  )
    when mun.pct_va_servicos then 'serviços'
    when mun.pct_va_industria then 'indústria'
    when mun.pct_va_agropecuaria then 'agropecuária'
    when mun.pct_va_adm_publica then 'administração pública'
  end as atividade_predominante,
  coalesce(con.ativos, 0) as ativos,
  round(coalesce(con.ativos, 0) * 10000.0 / nullif(mun.populacao, 0), 2) as ativos_por_10k_hab
from {{ ref('dim_municipio') }} as mun
left join {{ ref('mart_concorrencia_municipio') }} as con
  on mun.sk_municipio = con.sk_municipio and con.cnae_principal = '{{ var("caso_cnae_alvo") }}'
where mun.sigla_uf = '{{ var("caso_uf") }}' and mun.ano_va is not null
order by mun.pct_va_servicos desc nulls last, municipio asc
