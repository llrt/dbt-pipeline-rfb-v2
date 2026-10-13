{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-13 (docs/REGRAS_NEGOCIO.md): nenhuma data de evento passado passa do limite do extrato
-- (ADR-0004). Limites (RRN-02): o dia seguinte à data de referência (o corte do extrato inclui esse
-- dia) e, para a opção pelo Simples ou pelo MEI, 1º de janeiro do ano seguinte, a data de efeito da
-- opção feita no ano anterior (CGSN 190 e 194/2026). As datas de exclusão ficam de fora: podem ter efeito futuro (R3-11). Universo:
-- valores preenchidos de cada campo, pela faixa; só "além do limite" viola.
with referencia as (
  select {{ data_referencia(ref('int_estabelecimentos__enriquecidos')) }} as data_referencia
),

datas as (
  select
    'início de atividade' as campo,
    false as opcao,
    dat_inicio_atividade as data_evento
  from {{ ref('int_estabelecimentos__enriquecidos') }}
  where dat_inicio_atividade is not null

  union all

  select
    'situação cadastral' as campo,
    false as opcao,
    dat_situacao as data_evento
  from {{ ref('int_estabelecimentos__enriquecidos') }}
  where dat_situacao is not null

  union all

  select
    'situação especial' as campo,
    false as opcao,
    dat_situacao_especial as data_evento
  from {{ ref('stg_rfb__estabelecimentos') }}
  where dat_situacao_especial is not null

  union all

  select
    'opção pelo Simples' as campo,
    true as opcao,
    dat_opcao_simples as data_evento
  from {{ ref('stg_rfb__simples') }}
  where dat_opcao_simples is not null

  union all

  select
    'opção pelo MEI' as campo,
    true as opcao,
    dat_opcao_mei as data_evento
  from {{ ref('stg_rfb__simples') }}
  where dat_opcao_mei is not null
),

base as (
  select
    datas.campo,
    case
      when datas.data_evento <= extrato.data_referencia then 'até a data do extrato'
      when datas.data_evento = extrato.data_referencia + 1 then 'dia seguinte ao extrato'
      when datas.opcao and datas.data_evento <= make_date(year(extrato.data_referencia) + 1, 1, 1)
        then 'opção até 1º de janeiro seguinte'
      else 'além do limite'
    end as faixa
  from datas
  cross join referencia as extrato
)

select
  'RN-13' as regra,
  campo,
  faixa,
  count(*) as avaliados,
  count(*) filter (where faixa = 'além do limite') as violacoes
from base
group by all
order by campo, faixa
