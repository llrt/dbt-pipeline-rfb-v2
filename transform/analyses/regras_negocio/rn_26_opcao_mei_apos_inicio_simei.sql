{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-26 (docs/referencia/regras-negocio.md): a opção pelo MEI não é anterior a 1º/7/2009, quando os arts.
-- 18-A a 18-C da LC 123 (o SIMEI) passaram a produzir efeitos (LC 128/2008, art. 14, III).
-- Universo: registros do arquivo Simples com data de opção pelo MEI.
select
  'RN-26' as regra,
  count(*) as avaliados,
  count(*) filter (where dat_opcao_mei < date '2009-07-01') as violacoes
from {{ ref('stg_rfb__simples') }}
where dat_opcao_mei is not null
