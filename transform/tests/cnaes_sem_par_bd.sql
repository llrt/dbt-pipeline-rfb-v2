{{ config(
    severity='warn',
    store_failures=true,
    tags=['escopo_original'],
    meta={'escopo': 'original'}
) }}

-- Reproduz o check do notebook 2.1.2 (qualidade dos domínios): CNAEs RFB sem par na Base dos
-- Dados. São casos pontuais e esperados (CNAEs "raiz" que a RFB manteve na lista, ou
-- descontinuados na versão atual do IBGE, ex. 3511500) -- por isso severidade warn, não error.
-- O raw retém múltiplos meses (atualização mensal): a checagem considera só o mês selecionado (`filtro_mes_referencia`:
-- var `mes_referencia` ou o mês mais recente).
with cnaes_rfb as (
  select
    codigo,
    descricao
  from {{ source('rfb', 'cnaes') }}
  where {{ filtro_mes_referencia(source('rfb', 'cnaes')) }}
)

select
  c.codigo,
  c.descricao
from cnaes_rfb as c
left join {{ source('basedosdados', 'cnae_2') }} as bd
  on c.codigo = bd.subclasse
where bd.subclasse is null
