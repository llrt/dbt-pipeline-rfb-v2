{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-27 (docs/referencia/regras-negocio.md): a filial não começa atividade depois da data em que a matriz foi
-- baixada, declarada inapta ou nula (coerência apoiada na IN RFB 2.119, art. 21, IV, que impede a
-- inscrição de filial nesses casos). Universo: filiais com início de atividade, de CNPJ básico com
-- uma única matriz NULA, INAPTA ou BAIXADA com data da situação; pela situação da matriz.
with matrizes as (
  select
    cnpj_raiz,
    any_value(situacao_codigo) as situacao_codigo,
    any_value(dat_situacao) as dat_situacao
  from {{ ref('int_estabelecimentos__enriquecidos') }}
  where matriz_filial_codigo = 1
  group by cnpj_raiz
  having count(*) = 1
),

matrizes_encerradas as (
  select *
  from matrizes
  where situacao_codigo in (1, 4, 8) and dat_situacao is not null
)

select
  'RN-27' as regra,
  coalesce(sit.rotulo, 'NÃO INFORMADO') as situacao_matriz,
  count(*) as avaliados,
  count(*) filter (where fil.dat_inicio_atividade > mat.dat_situacao) as violacoes
from {{ ref('int_estabelecimentos__enriquecidos') }} as fil
inner join matrizes_encerradas as mat
  on fil.cnpj_raiz = mat.cnpj_raiz
left join {{ ref('dominio_situacao_cadastral') }} as sit
  on mat.situacao_codigo = sit.codigo
where fil.matriz_filial_codigo = 2 and fil.dat_inicio_atividade is not null
group by all
order by situacao_matriz
