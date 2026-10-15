{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-22 (docs/referencia/regras-negocio.md): grão declarado e sem teste (RDIC-09): o arquivo Simples tem uma
-- linha por CNPJ básico no mês selecionado. Violações = linhas excedentes (linhas − chaves).
with por_raiz as (
  select
    cnpj_raiz,
    count(*) as linhas
  from {{ ref('stg_rfb__simples') }}
  group by cnpj_raiz
)

select
  'RN-22' as regra,
  coalesce(sum(linhas), 0) as avaliados,
  coalesce(sum(linhas - 1), 0) as violacoes
from por_raiz
