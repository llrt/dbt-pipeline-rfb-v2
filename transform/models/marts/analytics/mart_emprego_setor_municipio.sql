-- incremento: enriquecimento_ibge (ADR-0022). Tamanho do setor no município: CEMPRE (IBGE) ao lado
-- dos CNPJs ativos da RFB. Grão = município × classe CNAE (5 dígitos), só onde o CEMPRE tem unidade
-- local (`unidades_locais` > 0) OU a RFB tem estabelecimento ativo com subclasse da classe. O CEMPRE
-- vem do ano mais recente baixado; a RFB, do mês do gold (`mes_referencia_rfb`): os anos são
-- diferentes. Sigilo (`X` do IBGE) nunca é imputado: o valor fica NULL e `tem_sigilo` true, e
-- `pessoal_por_unidade` sai NULL. Município (-1) e CNAE (-1) desconhecidos ficam de fora. Classe do
-- CEMPRE sem par na CNAE da RFB (`dim_cnae`, ex.: 70.10-7 "Sedes de empresas") leva a descrição do
-- próprio CEMPRE (RIBG-09).
with mes as (
  select max(_mes_referencia)::varchar as mes_referencia
  from {{ ref('stg_rfb__estabelecimentos') }}
),

ano_cempre as (
  select max(ano) as ano from {{ ref('stg_ibge__cempre_municipio_classe') }}
),

cempre as (
  select
    mun.sk_municipio,
    cla.classe_cnae,
    cla.nome_classe_cnae,
    cla.ano,
    cla.unidades_locais,
    cla.pessoal_ocupado,
    cla.pessoal_assalariado,
    cla.salarios_mil_reais,
    cla.tem_sigilo
  from {{ ref('stg_ibge__cempre_municipio_classe') }} as cla
  inner join ano_cempre on cla.ano = ano_cempre.ano
  inner join {{ ref('dim_municipio') }} as mun
    on cla.id_municipio = mun.id_municipio_ibge
),

rfb as (
  select
    fct.sk_municipio,
    cnae.codigo_classe as classe_cnae,
    count(*)::bigint as ativos_rfb,
    count(*) filter (where not fct.opcao_mei)::bigint as ativos_rfb_sem_mei
  from {{ ref('fct_estabelecimentos') }} as fct
  inner join {{ ref('dim_cnae') }} as cnae
    on fct.sk_cnae = cnae.sk_cnae
  where fct.eh_ativa and fct.sk_municipio <> -1 and fct.sk_cnae <> -1
  group by fct.sk_municipio, cnae.codigo_classe
),

classes as (
  select distinct
    codigo_classe,
    descricao_classe
  from {{ ref('dim_cnae') }}
  where sk_cnae <> -1
),

pares as (
  select
    coalesce(cem.sk_municipio, rfb.sk_municipio) as sk_municipio,
    coalesce(cem.classe_cnae, rfb.classe_cnae) as classe_cnae,
    cem.nome_classe_cnae,
    cem.unidades_locais,
    cem.pessoal_ocupado,
    cem.pessoal_assalariado,
    cem.salarios_mil_reais,
    cem.tem_sigilo,
    coalesce(rfb.ativos_rfb, 0) as ativos_rfb,
    coalesce(rfb.ativos_rfb_sem_mei, 0) as ativos_rfb_sem_mei
  from cempre as cem
  full outer join rfb
    on cem.sk_municipio = rfb.sk_municipio and cem.classe_cnae = rfb.classe_cnae
  where coalesce(cem.unidades_locais, 0) > 0 or coalesce(rfb.ativos_rfb, 0) > 0
)

select
  par.sk_municipio,
  mun.id_municipio_ibge,
  mun.nome_municipio as municipio,
  mun.sigla_uf as uf,
  par.classe_cnae,
  coalesce(cla.descricao_classe, par.nome_classe_cnae) as descricao_classe,
  ano_cempre.ano as ano_cempre,
  par.unidades_locais as unidades_locais_cempre,
  par.pessoal_ocupado as pessoal_ocupado_cempre,
  par.pessoal_assalariado as pessoal_assalariado_cempre,
  par.salarios_mil_reais,
  coalesce(par.tem_sigilo, false) as tem_sigilo,
  par.ativos_rfb,
  par.ativos_rfb_sem_mei,
  case
    when not coalesce(par.tem_sigilo, false) and par.unidades_locais > 0
      then round(par.pessoal_ocupado * 1.0 / par.unidades_locais, 2)
  end as pessoal_por_unidade,
  round(par.unidades_locais * 1.0 / nullif(par.ativos_rfb, 0), 4)
    as razao_unidades_cempre_ativos_rfb,
  mes.mes_referencia as mes_referencia_rfb
from pares as par
inner join {{ ref('dim_municipio') }} as mun
  on par.sk_municipio = mun.sk_municipio
left join classes as cla
  on par.classe_cnae = cla.codigo_classe
cross join ano_cempre
cross join mes
