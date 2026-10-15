{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-28 (docs/referencia/regras-negocio.md): observação do projeto, não regra legal: a opção pelo Simples ou
-- pelo MEI não antecede o início de atividade da matriz. Universo: registros do arquivo Simples com
-- a data de opção do regime, de CNPJ básico com uma única matriz com início de atividade.
with matrizes as (
  select
    cnpj_raiz,
    any_value(dat_inicio_atividade) as dat_inicio_atividade
  from {{ ref('int_estabelecimentos__enriquecidos') }}
  where matriz_filial_codigo = 1
  group by cnpj_raiz
  having count(*) = 1 and count(dat_inicio_atividade) = 1
),

base as (
  select
    sim.dat_opcao_simples,
    sim.dat_opcao_mei,
    mat.dat_inicio_atividade
  from {{ ref('stg_rfb__simples') }} as sim
  inner join matrizes as mat
    on sim.cnpj_raiz = mat.cnpj_raiz
)

select
  'RN-28' as regra,
  'Simples Nacional' as regime,
  count(*) as avaliados,
  count(*) filter (where dat_opcao_simples < dat_inicio_atividade) as violacoes
from base
where dat_opcao_simples is not null

union all

select
  'RN-28' as regra,
  'MEI' as regime,
  count(*) as avaliados,
  count(*) filter (where dat_opcao_mei < dat_inicio_atividade) as violacoes
from base
where dat_opcao_mei is not null
