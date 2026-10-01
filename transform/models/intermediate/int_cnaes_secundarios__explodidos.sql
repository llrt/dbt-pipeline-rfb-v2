-- Uma linha por (estabelecimento, CNAE secundário): explode `cnaes_secundarios_lista` (lista já
-- normalizada para 7 dígitos no staging). Lista vazia não gera linhas; códigos repetidos no mesmo
-- estabelecimento contam uma vez.
select distinct
  cnpj_completo,
  unnest(cnaes_secundarios_lista) as codigo_cnae_secundario
from {{ ref('int_estabelecimentos__enriquecidos') }}
