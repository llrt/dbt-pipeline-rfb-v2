-- incremento: enriquecimento_ibge
-- REGIC 2018: para onde os moradores de cada município vão comprar, em formato longo (origem × destino
-- × tema), só nos dois temas de compra: Q1 vestuário e calçados e Q2 móveis e eletroeletrônicos. Ficam
-- as ligações com % > 0. O destino "Outros" (lugares não listados) fica, com `eh_outros`, para a soma
-- por origem e tema bater ~100; ele nunca tem posto. `posto` = 1 é o principal destino listado da
-- origem no tema (maior %; empate fica com o menor código IBGE do destino).
with temas as (
  select
    id_municipio_origem,
    id_municipio_destino,
    destino_outros as eh_outros,
    'vestuario_calcados' as tema,
    pct_vestuario_calcados as pct
  from {{ ref('stg_ibge__regic_ligacoes') }}
  union all
  select
    id_municipio_origem,
    id_municipio_destino,
    destino_outros as eh_outros,
    'moveis_eletro' as tema,
    pct_moveis_eletro as pct
  from {{ ref('stg_ibge__regic_ligacoes') }}
),

positivos as (
  select *
  from temas
  where pct > 0 and id_municipio_origem is not null
)

select
  id_municipio_origem,
  id_municipio_destino,
  eh_outros,
  tema,
  pct,
  case
    when not eh_outros
      then row_number() over (
        partition by id_municipio_origem, tema, eh_outros
        order by pct desc, id_municipio_destino asc
      )
  end as posto
from positivos
