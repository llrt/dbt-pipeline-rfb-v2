{{ config(
    tags=['escopo_adicao', 'incremento_enriquecimento_ibge'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_ibge'}
) }}

-- Cenário 2 (docs/CENARIOS_DE_USO.md), incremento enriquecimento_ibge: polo de compras e evasão de
-- demanda. Para os municípios da UF do caso, onde os moradores vão comprar móveis e eletroeletrônicos (Q2
-- da REGIC 2018, a proxy de bem durável): o polo e o % dos deslocamentos que vão a ele, quantos destinos
-- fora do município foram citados e o % que vai a lugares não listados ("Outros"), com os ativos do CNAE do
-- caso no município e no polo. A REGIC mede a divisão dos deslocamentos ENTRE destinos fora do município,
-- não quanto da demanda sai: um polo com 45 % quer dizer 45 % de quem compra fora, não 45 % de toda a
-- compra. Os 67 municípios de maior centralidade não tiveram questionário (sem polo). Só agregados.
with destinos as (
  select
    sk_municipio_origem,
    count(*) filter (where not eh_outros) as destinos_citados,
    coalesce(sum(pct) filter (where eh_outros), 0) as pct_outros
  from {{ ref('bridge_municipio_destino_compras') }}
  where tema = 'moveis_eletro'
  group by sk_municipio_origem
)

select
  are.municipio,
  mun.regic_hierarquia,
  are.nome_municipio_polo_compras as polo_compras,
  are.pct_compras_no_polo,
  des.destinos_citados,
  des.pct_outros,
  are.ativos as ativos_no_municipio,
  are.ativos_no_polo
from {{ ref('mart_concorrencia_area_mercado') }} as are
inner join {{ ref('dim_municipio') }} as mun
  on are.sk_municipio = mun.sk_municipio
left join destinos as des
  on are.sk_municipio = des.sk_municipio_origem
where
  are.cnae_principal = '{{ var("caso_cnae_alvo") }}'
  and are.uf = '{{ var("caso_uf") }}'
  and are.id_municipio_polo_compras is not null
order by are.pct_compras_no_polo desc, are.municipio asc
