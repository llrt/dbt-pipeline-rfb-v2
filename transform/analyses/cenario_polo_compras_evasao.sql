{{ config(
    tags=['escopo_adicao', 'incremento_enriquecimento_ibge'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_ibge'}
) }}

-- Cenário 2 (docs/uso/cenarios.md), incremento enriquecimento_ibge: polo de compras e evasão de
-- demanda. Para os municípios da UF do caso, onde os moradores vão comprar móveis e eletroeletrônicos (Q2
-- da REGIC 2018, a proxy de bem durável): o polo e o % dos deslocamentos que vão a ele, quantos destinos
-- fora do município foram citados e o % que vai a lugares não listados ("Outros"), com os ativos do CNAE do
-- caso no município e no polo. A REGIC mede a divisão dos deslocamentos ENTRE destinos fora do município,
-- não quanto da demanda sai: um polo com 45 % quer dizer 45 % de quem compra fora, não 45 % de toda a
-- compra. Os 67 municípios de maior centralidade não tiveram questionário (sem polo). Parte de
-- `dim_municipio` (todo município da UF com polo) e não da área de mercado, que só tem pares com o CNAE
-- no município, nos vizinhos ou na RM: um mercado sem nenhum ativo local aparece com 0 (Greptile PR #7).
-- O polo pode ficar noutra UF. Só agregados.
with destinos as (
  select
    sk_municipio_origem,
    count(*) filter (where not eh_outros) as destinos_citados,
    coalesce(sum(pct) filter (where eh_outros), 0) as pct_outros
  from {{ ref('bridge_municipio_destino_compras') }}
  where tema = 'moveis_eletro'
  group by sk_municipio_origem
),

ativos_cnae as (
  select
    sk_municipio,
    ativos
  from {{ ref('mart_concorrencia_municipio') }}
  where cnae_principal = '{{ var("caso_cnae_alvo") }}'
)

select
  mun.nome_municipio as municipio,
  mun.regic_hierarquia,
  mun.nome_municipio_polo_compras as polo_compras,
  mun.pct_compras_no_polo,
  des.destinos_citados,
  des.pct_outros,
  coalesce(loc.ativos, 0) as ativos_no_municipio,
  coalesce(polo.ativos, 0) as ativos_no_polo
from {{ ref('dim_municipio') }} as mun
left join destinos as des
  on mun.sk_municipio = des.sk_municipio_origem
left join ativos_cnae as loc
  on mun.sk_municipio = loc.sk_municipio
left join ativos_cnae as polo
  on mun.id_municipio_polo_compras::integer = polo.sk_municipio
where
  mun.sigla_uf = '{{ var("caso_uf") }}'
  and mun.sk_municipio <> -1
  and mun.id_municipio_polo_compras is not null
order by mun.pct_compras_no_polo desc, municipio asc
