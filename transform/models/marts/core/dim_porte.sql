-- Dimensão de porte da empresa a partir do seed `dominio_porte`. `sk_porte` = código RFB
-- (0, 1, 3, 5); membro -1 "NÃO INFORMADO" para porte vazio ou fora do domínio (diferente do
-- código 0, "N/A", que a RFB informa explicitamente).
select
  codigo as sk_porte,
  codigo::varchar as codigo_porte,
  rotulo as rotulo_porte,
  descricao as descricao_porte
from {{ ref('dominio_porte') }}

union all

select
  -1 as sk_porte,
  '-1' as codigo_porte,
  'NÃO INFORMADO' as rotulo_porte,
  'NÃO INFORMADO' as descricao_porte
