-- ANA-01: densidade de concorrência. Grão = CNAE principal × município. `ativos` e `inativos` seguem a
-- regra do original (`situacao_codigo != 2` = inativo, via `eh_ativa` da fato); `ativos_por_10k_hab`
-- usa a população de `dim_municipio` e fica NULL sem população (nunca zero). `ranking_uf` ordena os
-- municípios da mesma UF e CNAE pela densidade (1 = mais concorrido); NULL quando não há densidade.
with estratos as (
  select
    fct.sk_cnae,
    fct.sk_municipio,
    count(*) filter (where fct.eh_ativa) as ativos,
    count(*) filter (where not fct.eh_ativa) as inativos
  from {{ ref('fct_estabelecimentos') }} as fct
  group by fct.sk_cnae, fct.sk_municipio
),

densidade as (
  select
    est.sk_cnae,
    cnae.codigo_subclasse as cnae_principal,
    cnae.descricao_subclasse as desc_cnae_principal,
    est.sk_municipio,
    mun.nome_municipio as municipio,
    mun.sigla_uf as uf,
    mun.populacao,
    est.ativos,
    est.inativos,
    round(est.ativos * 10000.0 / nullif(mun.populacao, 0), 2) as ativos_por_10k_hab
  from estratos as est
  inner join {{ ref('dim_cnae') }} as cnae
    on est.sk_cnae = cnae.sk_cnae
  inner join {{ ref('dim_municipio') }} as mun
    on est.sk_municipio = mun.sk_municipio
)

select
  *,
  case
    when ativos_por_10k_hab is not null
      then rank() over (partition by cnae_principal, uf order by ativos_por_10k_hab desc)
  end as ranking_uf
from densidade
