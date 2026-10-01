-- Dimensão de natureza jurídica (domínio RFB do mês selecionado). `sk_natureza_juridica` = código
-- como inteiro (determinística); membro -1 "NÃO INFORMADO" para empresa sem natureza no domínio.
select
  codigo::integer as sk_natureza_juridica,
  codigo as codigo_natureza_juridica,
  descricao as descricao_natureza_juridica
from {{ ref('stg_rfb__naturezas') }}

union all

select
  -1 as sk_natureza_juridica,
  '-1' as codigo_natureza_juridica,
  'NÃO INFORMADO' as descricao_natureza_juridica
