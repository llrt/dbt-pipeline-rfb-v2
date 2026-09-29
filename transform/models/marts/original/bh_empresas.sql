-- Flat table granular do notebook 3 (ADR-0005): mesmas 15 colunas e regras, com os mesmos inner
-- joins (estabelecimentos sem empresa, natureza, CNAE BD ou município BD saem — ver o teste
-- `bh_empresas_descartes_inner_join`). Diferenças intencionais: `idade_atual` relativa a
-- `data_referencia` em vez de `now()` (ADR-0004) e `nome` sem espaços nas bordas (trim do staging;
-- ADR-0005, emenda R2-01).
with estabelecimentos as (
  select * from {{ ref('stg_rfb__estabelecimentos') }}
),

empresas as (
  select * from {{ ref('stg_rfb__empresas') }}
),

naturezas as (
  select * from {{ ref('stg_rfb__naturezas') }}
),

cnaes_bd as (
  select * from {{ ref('stg_bd__cnaes') }}
),

municipios_bd as (
  select * from {{ ref('stg_bd__municipios') }}
)

select
  est.cnpj_raiz,
  est.cnpj_completo,
  upper(coalesce(est.nome_fantasia, emp.razao_social)) as nome,
  upper(nat.descricao) as natureza_juridica,
  case emp.porte_codigo
    when 0 then 'N/A'
    when 1 then 'MICRO'
    when 3 then 'PEQUENA'
    when 5 then 'DEMAIS'
  end as porte,
  est.cnae_principal,
  upper(cnae.descricao_subclasse) as desc_cnae_principal,
  upper(cnae.descricao_grupo) as grupo_cnae_principal,
  est.cnaes_secundarios,
  upper(mun.nome) as municipio,
  upper(mun.nome_microrregiao) as microrregiao_municipio,
  upper(mun.nome_mesorregiao) as mesorregiao_municipio,
  upper(mun.sigla_uf) as uf,
  case est.situacao_codigo when 2 then 'ATIVA' else 'INATIVA' end as situacao,
  case est.situacao_codigo
    when 2
      then round(
        datediff(
          'day', est.dat_inicio_atividade, {{ data_referencia(ref('stg_rfb__estabelecimentos')) }}
        ) / 365.25,
        1
      )
  end as idade_atual
from empresas as emp
inner join estabelecimentos as est
  on emp.cnpj_raiz = est.cnpj_raiz
inner join naturezas as nat
  on emp.natureza_juridica_codigo = nat.codigo
inner join cnaes_bd as cnae
  on est.cnae_principal = cnae.subclasse
inner join municipios_bd as mun
  on est.municipio_rfb_codigo = mun.id_municipio_rf
