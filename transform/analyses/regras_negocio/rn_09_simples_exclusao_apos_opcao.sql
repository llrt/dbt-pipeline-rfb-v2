{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-09 (docs/REGRAS_NEGOCIO.md): a data de exclusão não é anterior à data de opção, no Simples
-- Nacional e no MEI. Universo: registros do arquivo Simples com as duas datas do regime.
select
  'RN-09' as regra,
  'Simples Nacional' as regime,
  count(*) as avaliados,
  count(*) filter (where dat_exclusao_simples < dat_opcao_simples) as violacoes
from {{ ref('stg_rfb__simples') }}
where dat_opcao_simples is not null and dat_exclusao_simples is not null

union all

select
  'RN-09' as regra,
  'MEI' as regime,
  count(*) as avaliados,
  count(*) filter (where dat_exclusao_mei < dat_opcao_mei) as violacoes
from {{ ref('stg_rfb__simples') }}
where dat_opcao_mei is not null and dat_exclusao_mei is not null
