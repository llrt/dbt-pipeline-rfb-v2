-- ANA-02: sobrevivência por coorte (ano de `dat_inicio`). Grão = coorte × CNAE principal × porte × UF.
-- Definição (spec, "Sobrevivência a N anos"): a coorte inteira é elegível no horizonte N quando
-- `make_date(ano_coorte + N, 12, 31) <= data_referencia` (coorte sem censura); um membro sobrevive se
-- está ativo ou se `dat_situacao >= dat_inicio + N anos`. Inativo sem `dat_situacao` não sobrevive
-- (sem evidência). Como a elegibilidade é da coorte e não do membro, sobreviventes_N ⊆ sobreviventes_M
-- (N > M) e as taxas são monotônicas. Taxa = NULL quando a coorte ainda não é elegível no horizonte.
with estabelecimentos as (
  select
    year(ini.data) as ano_coorte,
    cnae.codigo_subclasse as cnae_principal,
    por.rotulo_porte as porte,
    mun.sigla_uf as uf,
    fct.eh_ativa,
    ini.data as dat_inicio,
    case when sit.sk_data > 0 then sit.data end as dat_situacao  -- -1/-2: sem data de situação
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
  where ini.sk_data > 0  -- sem início de atividade (-1) ou inválido (-2) não há coorte
),

marcados as (
  select
    *,
    make_date(ano_coorte + 1, 12, 31) <= {{ data_referencia(ref('int_estabelecimentos__enriquecidos')) }} as elegivel_1a,
    eh_ativa or coalesce(dat_situacao >= dat_inicio + to_years(1), false) as sobrevive_1a,
    make_date(ano_coorte + 3, 12, 31) <= {{ data_referencia(ref('int_estabelecimentos__enriquecidos')) }} as elegivel_3a,
    eh_ativa or coalesce(dat_situacao >= dat_inicio + to_years(3), false) as sobrevive_3a,
    make_date(ano_coorte + 5, 12, 31) <= {{ data_referencia(ref('int_estabelecimentos__enriquecidos')) }} as elegivel_5a,
    eh_ativa or coalesce(dat_situacao >= dat_inicio + to_years(5), false) as sobrevive_5a
  from estabelecimentos
)

select
  ano_coorte,
  cnae_principal,
  porte,
  uf,
  count(*) as estabelecimentos,
  count(*) filter (where elegivel_1a) as elegiveis_1a,
  count(*) filter (where elegivel_1a and sobrevive_1a) as sobreviventes_1a,
  count(*) filter (where elegivel_1a and sobrevive_1a)::double
  / nullif(count(*) filter (where elegivel_1a), 0) as taxa_1a,
  count(*) filter (where elegivel_3a) as elegiveis_3a,
  count(*) filter (where elegivel_3a and sobrevive_3a) as sobreviventes_3a,
  count(*) filter (where elegivel_3a and sobrevive_3a)::double
  / nullif(count(*) filter (where elegivel_3a), 0) as taxa_3a,
  count(*) filter (where elegivel_5a) as elegiveis_5a,
  count(*) filter (where elegivel_5a and sobrevive_5a) as sobreviventes_5a,
  count(*) filter (where elegivel_5a and sobrevive_5a)::double
  / nullif(count(*) filter (where elegivel_5a), 0) as taxa_5a
from marcados
group by ano_coorte, cnae_principal, porte, uf
