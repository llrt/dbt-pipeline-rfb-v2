{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-25 (docs/REGRAS_NEGOCIO.md): a opção pelo Simples Nacional não é anterior a 1º/7/2007, quando
-- o regime entrou em vigor (LC 123, art. 88). Universo: registros do arquivo Simples com data de
-- opção pelo Simples.
select
  'RN-25' as regra,
  count(*) as avaliados,
  count(*) filter (where dat_opcao_simples < date '2007-07-01') as violacoes
from {{ ref('stg_rfb__simples') }}
where dat_opcao_simples is not null
