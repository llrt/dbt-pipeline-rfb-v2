-- Fato detalhada para BI (ADR-0013): grão = estabelecimento (`cnpj_completo`, dimensão degenerada).
-- Só chaves inteiras, flags e medidas. Sem descartes silenciosos: estabelecimento sem par numa
-- dimensão fica na fato com a chave -1 ("NÃO INFORMADO"); data anterior a 1900 vai para -2
-- ("DATA INVÁLIDA", emenda R3-03). `idade_anos` só para ativos (regra do original, relativa a
-- `data_referencia`).
with enriquecidos as (
  select * from {{ ref('int_estabelecimentos__enriquecidos') }}
)

select
  est.cnpj_completo,
  coalesce(mun.sk_municipio, -1) as sk_municipio,
  coalesce(cnae.sk_cnae, -1) as sk_cnae,
  coalesce(nat.sk_natureza_juridica, -1) as sk_natureza_juridica,
  coalesce(por.sk_porte, -1) as sk_porte,
  coalesce(sit.sk_situacao_cadastral, -1) as sk_situacao_cadastral,
  case
    when est.dat_inicio_atividade < date '{{ var("primeiro_dia_calendario") }}' then -2  -- DATA INVÁLIDA (R3-03)
    else coalesce(dat_ini.sk_data, -1)
  end as sk_data_inicio_atividade,
  case
    when est.dat_situacao < date '{{ var("primeiro_dia_calendario") }}' then -2
    else coalesce(dat_sit.sk_data, -1)
  end as sk_data_situacao,
  case
    when est.situacao_codigo = 2
      then round(
        datediff(
          'day', est.dat_inicio_atividade, {{ data_referencia(ref('int_estabelecimentos__enriquecidos')) }}
        ) / 365.25,
        1
      )
  end as idade_anos,
  est.opcao_simples,
  est.opcao_mei,
  est.capital_social,
  coalesce(est.matriz_filial_codigo = 1, false) as eh_matriz,
  coalesce(est.situacao_codigo = 2, false) as eh_ativa
from enriquecidos as est
left join {{ ref('dim_municipio') }} as mun
  on est.id_municipio_ibge = mun.id_municipio_ibge
left join {{ ref('dim_cnae') }} as cnae
  on est.cnae_principal = cnae.codigo_subclasse
left join {{ ref('dim_natureza_juridica') }} as nat
  on est.natureza_juridica_codigo = nat.codigo_natureza_juridica
left join {{ ref('dim_porte') }} as por
  on est.porte_codigo = por.sk_porte
left join {{ ref('dim_situacao_cadastral') }} as sit
  on est.situacao_codigo = sit.sk_situacao_cadastral
left join {{ ref('dim_data') }} as dat_ini
  on est.dat_inicio_atividade = dat_ini.data
left join {{ ref('dim_data') }} as dat_sit
  on est.dat_situacao = dat_sit.data
