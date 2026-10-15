{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-16 (docs/referencia/regras-negocio.md): cada CNPJ básico do arquivo Estabelecimentos tem exatamente uma
-- matriz. Grão: empresa (CNPJ básico), pelo número de matrizes.
with por_empresa as (
  select
    cnpj_raiz,
    count(*) filter (where matriz_filial_codigo = 1) as matrizes
  from {{ ref('int_estabelecimentos__enriquecidos') }}
  group by cnpj_raiz
)

select
  'RN-16' as regra,
  case when matrizes >= 2 then '2 ou mais' else matrizes::varchar end as matrizes,
  count(*) as avaliados,
  count(*) filter (where matrizes != 1) as violacoes
from por_empresa
group by all
order by matrizes
