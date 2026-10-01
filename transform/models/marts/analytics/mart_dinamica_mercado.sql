-- ANA-03: dinâmica de mercado. Grão = ano × CNAE principal × município. `aberturas` = estabelecimentos
-- com `dat_inicio` no ano; `encerramentos` = inativos (`situacao != 2`, regra do original) com
-- `dat_situacao` no ano; `saldo` = aberturas − encerramentos. Datas nulas (`-1`) ou inválidas
-- (`-2`) em `dim_data` (ano NULL) não geram evento. Um estabelecimento pode gerar os dois eventos,
-- em anos diferentes.
with eventos as (
  select
    ini.ano,
    fct.sk_cnae,
    fct.sk_municipio,
    1 as abertura,
    0 as encerramento
  from {{ ref('fct_estabelecimentos') }} as fct
  inner join {{ ref('dim_data') }} as ini
    on fct.sk_data_inicio_atividade = ini.sk_data
  where ini.ano is not null

  union all

  select
    sit.ano,
    fct.sk_cnae,
    fct.sk_municipio,
    0 as abertura,
    1 as encerramento
  from {{ ref('fct_estabelecimentos') }} as fct
  inner join {{ ref('dim_data') }} as sit
    on fct.sk_data_situacao = sit.sk_data
  where not fct.eh_ativa and sit.ano is not null
)

select
  eve.ano,
  cnae.codigo_subclasse as cnae_principal,
  cnae.descricao_subclasse as desc_cnae_principal,
  mun.nome_municipio as municipio,
  mun.sigla_uf as uf,
  sum(eve.abertura)::bigint as aberturas,
  sum(eve.encerramento)::bigint as encerramentos,
  (sum(eve.abertura) - sum(eve.encerramento))::bigint as saldo
from eventos as eve
inner join {{ ref('dim_cnae') }} as cnae
  on eve.sk_cnae = cnae.sk_cnae
inner join {{ ref('dim_municipio') }} as mun
  on eve.sk_municipio = mun.sk_municipio
group by
  eve.ano,
  cnae.codigo_subclasse,
  cnae.descricao_subclasse,
  mun.nome_municipio,
  mun.sigla_uf,
  mun.sk_municipio
