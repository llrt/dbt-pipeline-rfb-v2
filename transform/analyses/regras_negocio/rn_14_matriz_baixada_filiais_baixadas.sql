{{ config(tags=['escopo_adicao'], meta={'escopo': 'adicao'}) }}

-- RN-14 (docs/REGRAS_NEGOCIO.md): a baixa da matriz implica a baixa de todas as filiais (IN RFB
-- 2.119, art. 24, § 2º). Universo: filiais cuja empresa tem matriz BAIXADA, pela situação da filial.
with raizes_matriz_baixada as (
  select distinct cnpj_raiz
  from {{ ref('int_estabelecimentos__enriquecidos') }}
  where matriz_filial_codigo = 1 and situacao_codigo = 8
)

select
  'RN-14' as regra,
  coalesce(sit.rotulo, 'NÃO INFORMADO') as situacao,
  count(*) as avaliados,
  count(*) filter (where est.situacao_codigo is distinct from 8) as violacoes
from {{ ref('int_estabelecimentos__enriquecidos') }} as est
inner join raizes_matriz_baixada as mb
  on est.cnpj_raiz = mb.cnpj_raiz
left join {{ ref('dominio_situacao_cadastral') }} as sit
  on est.situacao_codigo = sit.codigo
where est.matriz_filial_codigo = 2
group by all
order by situacao
