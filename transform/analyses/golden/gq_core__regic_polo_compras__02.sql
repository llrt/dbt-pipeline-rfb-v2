{# ---
id: gq_core__regic_polo_compras__02
conceito: regic_polo_compras
camada: core
perguntas:
  - "Quantos municípios há em cada nível da hierarquia urbana?"
  - "Fundão é metrópole ou cidade pequena?"
intencao: "Municípios e ativos por nível da hierarquia urbana da REGIC 2018 (atributo de dim_municipio)."
tabelas: [dim_municipio, fct_estabelecimentos]
colunas_chave: [regic_hierarquia_codigo, regic_hierarquia, sk_municipio]
armadilhas:
  - "A hierarquia é do ARRANJO populacional: Fundão é 'Metrópole' por integrar o arranjo de Vitória."
  - "Município criado depois de 2018 não tem hierarquia (NULL)."
variacoes:
  - "Uma UF: `where mun.sigla_uf = 'ES'`."
  - "Um CNAE: junte dim_cnae na contagem."
resposta_esperada_fixtures:
  colunas: [regic_hierarquia_codigo, regic_hierarquia, municipios, ativos]
  linhas:
    - [1C, Metrópole, 3, 6]
    - [3A, Centro Sub-Regional A, 1, 1]
    - [3B, Centro Sub-Regional B, 1, 1]
    - [4A, Centro de Zona A, 1, 0]
    - ['5', Centro Local, 2, 1]
--- #}
{{ config(
    tags=['escopo_adicao', 'golden_query', 'incremento_enriquecimento_ibge'],
    meta={'escopo': 'adicao', 'incremento': 'enriquecimento_ibge'}
) }}

select
  mun.regic_hierarquia_codigo,
  mun.regic_hierarquia,
  count(distinct mun.sk_municipio) as municipios,
  count(fct.cnpj_completo) filter (where fct.eh_ativa) as ativos
from {{ ref('dim_municipio') }} as mun
left join {{ ref('fct_estabelecimentos') }} as fct
  on mun.sk_municipio = fct.sk_municipio
where mun.sk_municipio <> -1
group by mun.regic_hierarquia_codigo, mun.regic_hierarquia
order by mun.regic_hierarquia_codigo
