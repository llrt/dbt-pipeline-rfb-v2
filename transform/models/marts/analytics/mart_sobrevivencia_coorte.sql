-- ANA-02: sobrevivência por coorte (ano de `dat_inicio`). Grão = coorte × CNAE principal × porte × UF.
-- Definição (spec, "Sobrevivência a N anos"): a coorte inteira é elegível no horizonte N quando
-- `make_date(ano_coorte + N, 12, 31) <= data_referencia` (coorte sem censura); um membro sobrevive se
-- está ativo ou se `dat_situacao >= dat_inicio + N anos`. Inativo sem `dat_situacao` não sobrevive
-- (sem evidência). Como a elegibilidade é da coorte e não do membro, sobreviventes_N ⊆ sobreviventes_M
-- (N > M) e as taxas são monotônicas. Taxa = NULL quando a coorte ainda não é elegível no horizonte.
{%- set horizontes = [1, 3, 5] %}
with estabelecimentos as (
  select
    year(ini.data) as ano_coorte,
    cnae.codigo_subclasse as cnae_principal,
    por.rotulo_porte as porte,
    mun.sigla_uf as uf,
    fct.eh_ativa,
    ini.data as dat_inicio,
    sit.data as dat_situacao
  from {{ ref('fct_estabelecimentos') }} as fct
  inner join {{ ref('dim_data') }} as ini
    on fct.sk_data_inicio_atividade = ini.sk_data
  inner join {{ ref('dim_data') }} as sit
    on fct.sk_data_situacao = sit.sk_data
  inner join {{ ref('dim_cnae') }} as cnae
    on fct.sk_cnae = cnae.sk_cnae
  inner join {{ ref('dim_porte') }} as por
    on fct.sk_porte = por.sk_porte
  inner join {{ ref('dim_municipio') }} as mun
    on fct.sk_municipio = mun.sk_municipio
  where ini.data is not null  -- sem início de atividade não há coorte
),

marcados as (
  select
    *,
    {%- for n in horizontes %}
    make_date(ano_coorte + {{ n }}, 12, 31) <= {{ data_referencia(ref('int_estabelecimentos__enriquecidos')) }} as elegivel_{{ n }}a,
    eh_ativa or coalesce(dat_situacao >= dat_inicio + to_years({{ n }}), false) as sobrevive_{{ n }}a{{ "," if not loop.last }}
    {%- endfor %}
  from estabelecimentos
)

select
  ano_coorte,
  cnae_principal,
  porte,
  uf,
  count(*) as estabelecimentos,
  {%- for n in horizontes %}
  count(*) filter (where elegivel_{{ n }}a) as elegiveis_{{ n }}a,
  count(*) filter (where elegivel_{{ n }}a and sobrevive_{{ n }}a) as sobreviventes_{{ n }}a,
  count(*) filter (where elegivel_{{ n }}a and sobrevive_{{ n }}a)::double
  / nullif(count(*) filter (where elegivel_{{ n }}a), 0) as taxa_{{ n }}a{{ "," if not loop.last }}
  {%- endfor %}
from marcados
group by ano_coorte, cnae_principal, porte, uf
