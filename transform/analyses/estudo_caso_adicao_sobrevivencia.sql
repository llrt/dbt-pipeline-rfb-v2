{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- Adição (ANA-02): sobrevivência a 1, 3 e 5 anos das coortes do CNAE do caso na UF (todas as
-- coortes e portes somados). Fixtures: 6/6, 5/4 e 4/2.
select
  sum(elegiveis_1a) as elegiveis_1a,
  sum(sobreviventes_1a) as sobreviventes_1a,
  sum(sobreviventes_1a) * 1.0 / nullif(sum(elegiveis_1a), 0) as taxa_1a,
  sum(elegiveis_3a) as elegiveis_3a,
  sum(sobreviventes_3a) as sobreviventes_3a,
  sum(sobreviventes_3a) * 1.0 / nullif(sum(elegiveis_3a), 0) as taxa_3a,
  sum(elegiveis_5a) as elegiveis_5a,
  sum(sobreviventes_5a) as sobreviventes_5a,
  sum(sobreviventes_5a) * 1.0 / nullif(sum(elegiveis_5a), 0) as taxa_5a
from {{ ref('mart_sobrevivencia_coorte') }}
where cnae_principal = '{{ var("caso_cnae_alvo") }}' and uf = '{{ var("caso_uf") }}'
