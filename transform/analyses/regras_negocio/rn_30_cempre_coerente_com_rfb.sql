{{ config(
    tags=['escopo_adicao', 'incremento_enriquecimento_ibge'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_ibge'}
) }}

-- RN-30 (docs/REGRAS_NEGOCIO.md): onde o CEMPRE do IBGE vê ao menos 3 unidades locais de uma classe
-- CNAE num município, a RFB tem ao menos um estabelecimento ativo, sem MEI, da classe. Observação de
-- coerência entre as bases: uma violação aponta divergência de classificação CNAE ou defasagem do
-- cadastro, não erro de nenhuma delas. Universo: pares município × classe com unidade local no CEMPRE
-- (ano mais recente) ou ativo na RFB (os de `mart_emprego_setor_municipio`), por UF e faixa da razão
-- unidades CEMPRE ÷ ativos RFB sem MEI. Lê o CEMPRE pela fonte (o warehouse de quem só roda
-- `rfb regras` pode não ter o staging do IBGE) e a RFB por `fct_estabelecimentos`. Só classes que
-- existem na CNAE da RFB (`dim_cnae`): uma classe do CEMPRE sem par (70.10-7, "Sedes de empresas")
-- nunca tem ativo na RFB e seria violação estrutural, não divergência (RIBG-09).
with categorias as (
  select
    d4c as id_categoria_sidra,
    replace(replace(split_part(d4n, ' ', 1), '.', ''), '-', '') as classe_cnae
  from {{ source('ibge', 'cempre_categorias_cnae') }}
  where regexp_matches(d4n, '^\d{2}\.\d{2}-\d ')
),

unidades as (
  select
    {{ texto_ou_nulo('cem.d1c') }} as id_municipio,
    cem.d3c::int as ano,
    cat.classe_cnae,
    {{ valor_ibge('cem.v', 'bigint') }} as unidades_locais
  from {{ source('ibge', 'cempre_municipio_cnae') }} as cem
  inner join categorias as cat on cem.d4c = cat.id_categoria_sidra
  where cem.d2c = '706'
),

cempre as (
  select
    mun.sk_municipio,
    uni.classe_cnae,
    uni.unidades_locais
  from unidades as uni
  inner join {{ ref('dim_municipio') }} as mun
    on uni.id_municipio = mun.id_municipio_ibge
  where
    uni.ano = (select max(ult.ano) from unidades as ult)
    and uni.unidades_locais > 0
    and uni.classe_cnae in (
      select cnae.codigo_classe
      from {{ ref('dim_cnae') }} as cnae
      where cnae.sk_cnae <> -1
    )
),

rfb as (
  select
    fct.sk_municipio,
    cnae.codigo_classe as classe_cnae,
    count(*) as ativos,
    count(*) filter (where not fct.opcao_mei) as ativos_sem_mei
  from {{ ref('fct_estabelecimentos') }} as fct
  inner join {{ ref('dim_cnae') }} as cnae
    on fct.sk_cnae = cnae.sk_cnae
  where fct.eh_ativa and fct.sk_municipio <> -1 and fct.sk_cnae <> -1
  group by fct.sk_municipio, cnae.codigo_classe
),

pares as (
  select
    coalesce(cem.sk_municipio, rfb.sk_municipio) as sk_municipio,
    coalesce(cem.unidades_locais, 0) as unidades_locais,
    coalesce(rfb.ativos_sem_mei, 0) as ativos_sem_mei
  from cempre as cem
  full outer join rfb
    on cem.sk_municipio = rfb.sk_municipio and cem.classe_cnae = rfb.classe_cnae
),

base as (
  select
    mun.sigla_uf as uf,
    case
      when par.ativos_sem_mei = 0 then 'sem ativo RFB sem MEI'
      when par.unidades_locais = 0 then 'sem unidade no CEMPRE'
      when par.unidades_locais < par.ativos_sem_mei * 0.5 then 'razão < 0,5'
      when par.unidades_locais <= par.ativos_sem_mei * 2 then 'razão de 0,5 a 2'
      else 'razão > 2'
    end as faixa,
    par.unidades_locais >= 3 and par.ativos_sem_mei = 0 as violacao
  from pares as par
  inner join {{ ref('dim_municipio') }} as mun
    on par.sk_municipio = mun.sk_municipio
)

select
  'RN-30' as regra,
  uf,
  faixa,
  count(*) as avaliados,
  count(*) filter (where violacao) as violacoes
from base
group by all
order by uf, faixa
