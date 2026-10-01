-- Dimensão de CNAE para BI (ADR-0013): hierarquia seção → divisão → grupo → classe → subclasse da
-- Base dos Dados, código e descrição em colunas separadas. `sk_cnae` = subclasse como inteiro
-- (determinística; '0111301' → 111301). Membro -1 "NÃO INFORMADO" para CNAE sem par no BD
-- (ex.: 3511500 do cenário) ou estabelecimento sem CNAE.
select
  subclasse::integer as sk_cnae,
  secao as codigo_secao,
  descricao_secao,
  divisao as codigo_divisao,
  descricao_divisao,
  grupo as codigo_grupo,
  descricao_grupo,
  classe as codigo_classe,
  descricao_classe,
  subclasse as codigo_subclasse,
  descricao_subclasse
from {{ ref('stg_bd__cnaes') }}

union all

select
  -1 as sk_cnae,
  '-1' as codigo_secao,
  'NÃO INFORMADO' as descricao_secao,
  '-1' as codigo_divisao,
  'NÃO INFORMADO' as descricao_divisao,
  '-1' as codigo_grupo,
  'NÃO INFORMADO' as descricao_grupo,
  '-1' as codigo_classe,
  'NÃO INFORMADO' as descricao_classe,
  '-1' as codigo_subclasse,
  'NÃO INFORMADO' as descricao_subclasse
