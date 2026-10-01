-- Dimensão de situação cadastral a partir do seed `dominio_situacao_cadastral`. `sk_situacao_cadastral`
-- = código RFB (1, 2, 3, 4, 8); membro -1 "NÃO INFORMADO" para código fora do domínio.
select
  codigo as sk_situacao_cadastral,
  codigo::varchar as codigo_situacao_cadastral,
  rotulo as rotulo_situacao_cadastral,
  descricao as descricao_situacao_cadastral
from {{ ref('dominio_situacao_cadastral') }}

union all

select
  -1 as sk_situacao_cadastral,
  '-1' as codigo_situacao_cadastral,
  'NÃO INFORMADO' as rotulo_situacao_cadastral,
  'NÃO INFORMADO' as descricao_situacao_cadastral
