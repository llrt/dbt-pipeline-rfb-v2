select
  {{ texto_ou_nulo('id_municipio') }} as id_municipio,
  {{ texto_ou_nulo('sigla_uf') }} as sigla_uf,
  ano::int as ano,
  populacao::bigint as populacao
from {{ source('basedosdados', 'populacao') }}
