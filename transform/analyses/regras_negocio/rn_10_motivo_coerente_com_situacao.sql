{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-10 (docs/REGRAS_NEGOCIO.md): tradução de "empresa ativa não tem encerramento": o
-- estabelecimento ATIVO tem o motivo 00 (SEM MOTIVO) e o não ativo tem um motivo diferente de 00.
-- Motivo vazio conta como 00.
with base as (
  select
    situacao_codigo,
    case
      when situacao_codigo = 2 then coalesce(motivo_situacao_codigo, '00') != '00'
      else coalesce(motivo_situacao_codigo, '00') = '00'
    end as viola
  from {{ ref('stg_rfb__estabelecimentos') }}
)

select
  'RN-10' as regra,
  coalesce(sit.rotulo, 'NÃO INFORMADO') as situacao,
  count(*) as avaliados,
  count(*) filter (where base.viola) as violacoes
from base
left join {{ ref('dominio_situacao_cadastral') }} as sit
  on base.situacao_codigo = sit.codigo
group by all
order by situacao
