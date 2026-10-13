{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-13 (docs/REGRAS_NEGOCIO.md): nenhuma data de evento passado é posterior à data do extrato
-- (ADR-0004). As datas de exclusão do Simples/MEI ficam de fora: podem ter efeito futuro (R3-11).
-- Universo: valores preenchidos de cada campo.
with simples as (
  select
    sim.*,
    {{ data_referencia(ref('int_estabelecimentos__enriquecidos')) }} as data_referencia
  from {{ ref('stg_rfb__simples') }} as sim
)

select
  'RN-13' as regra,
  'início de atividade' as campo,
  count(*) as avaliados,
  count(*) filter (where dat_inicio_atividade > _data_referencia) as violacoes
from {{ ref('int_estabelecimentos__enriquecidos') }}
where dat_inicio_atividade is not null

union all

select
  'RN-13' as regra,
  'situação cadastral' as campo,
  count(*) as avaliados,
  count(*) filter (where dat_situacao > _data_referencia) as violacoes
from {{ ref('int_estabelecimentos__enriquecidos') }}
where dat_situacao is not null

union all

select
  'RN-13' as regra,
  'situação especial' as campo,
  count(*) as avaliados,
  count(*) filter (where dat_situacao_especial > _data_referencia) as violacoes
from {{ ref('stg_rfb__estabelecimentos') }}
where dat_situacao_especial is not null

union all

select
  'RN-13' as regra,
  'opção pelo Simples' as campo,
  count(*) as avaliados,
  count(*) filter (where dat_opcao_simples > data_referencia) as violacoes
from simples
where dat_opcao_simples is not null

union all

select
  'RN-13' as regra,
  'opção pelo MEI' as campo,
  count(*) as avaliados,
  count(*) filter (where dat_opcao_mei > data_referencia) as violacoes
from simples
where dat_opcao_mei is not null
