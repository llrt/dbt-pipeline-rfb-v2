{{ config(
    severity='error',
    tags=['escopo_adicao'],
    meta={'escopo': 'adicao'}
) }}

-- ANA-02 AC 3: taxas em [0,1] e, dentro da linha, taxa_1a >= taxa_3a >= taxa_5a quando ambas as
-- taxas comparadas são não nulas. Retorna uma linha por violação.
select
  ano_coorte,
  cnae_principal,
  porte,
  uf,
  taxa_1a,
  taxa_3a,
  taxa_5a
from {{ ref('mart_sobrevivencia_coorte') }}
where
  coalesce(taxa_1a not between 0 and 1, false)
  or coalesce(taxa_3a not between 0 and 1, false)
  or coalesce(taxa_5a not between 0 and 1, false)
  or coalesce(taxa_1a < taxa_3a, false)
  or coalesce(taxa_3a < taxa_5a, false)
