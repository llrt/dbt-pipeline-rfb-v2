{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-20 (docs/REGRAS_NEGOCIO.md): o ente federativo responsável é preenchido nas naturezas
-- jurídicas do grupo 1XXX (administração pública) e fica em branco nas demais (leiaute RFB).
-- Grão: empresa (CNPJ básico) do arquivo Empresas, pelo grupo da natureza.
with base as (
  select
    coalesce(left(natureza_juridica_codigo, 1) = '1', false) as publica,
    ente_federativo_responsavel is not null as tem_ente
  from {{ ref('stg_rfb__empresas') }}
)

select
  'RN-20' as regra,
  case when publica then 'grupo 1 (administração pública)' else 'demais grupos' end as grupo_natureza,
  count(*) as avaliados,
  count(*) filter (where publica != tem_ente) as violacoes
from base
group by all
order by grupo_natureza
