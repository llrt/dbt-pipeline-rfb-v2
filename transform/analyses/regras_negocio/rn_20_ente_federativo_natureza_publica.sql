{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-20 (docs/referencia/regras-negocio.md): o ente federativo responsável é preenchido nas naturezas
-- jurídicas do grupo 1XXX (administração pública) e fica em branco nas demais (leiaute RFB).
-- Grão: empresa (CNPJ básico) do arquivo Empresas, pelo grupo e pela natureza (RRN-06).
with base as (
  select
    coalesce(left(emp.natureza_juridica_codigo, 1) = '1', false) as publica,
    coalesce(emp.natureza_juridica_codigo, '—') || ' '
    || coalesce(nat.descricao, '(fora do domínio)') as natureza_juridica,
    emp.ente_federativo_responsavel is not null as tem_ente
  from {{ ref('stg_rfb__empresas') }} as emp
  left join {{ ref('stg_rfb__naturezas') }} as nat
    on emp.natureza_juridica_codigo = nat.codigo
)

select
  'RN-20' as regra,
  case when publica then 'grupo 1 (administração pública)' else 'demais grupos' end as grupo_natureza,
  natureza_juridica,
  count(*) as avaliados,
  count(*) filter (where publica != tem_ente) as violacoes
from base
group by all
order by grupo_natureza, natureza_juridica
