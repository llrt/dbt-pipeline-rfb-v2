{# ---
id: gq_core__natureza_juridica__01
conceito: natureza_juridica
camada: core
perguntas:
  - "Quantos estabelecimentos ativos há por natureza jurídica?"
  - "Quantos empresários individuais ativos existem?"
intencao: "Ativos por natureza jurídica (código e descrição de dim_natureza_juridica)."
tabelas: [fct_estabelecimentos, dim_natureza_juridica]
colunas_chave: [sk_natureza_juridica, codigo_natureza_juridica, descricao_natureza_juridica]
armadilhas:
  - "MEI não é natureza: quase todo MEI é 2135 Empresário (Individual), mas o filtro de MEI é `opcao_mei`."
  - "Natureza jurídica só existe na fato detalhada, não em fct_resumo_mensal nem nos marts."
  - "A natureza é da empresa e se repete em cada estabelecimento: para empresas, filtre `eh_matriz`."
variacoes:
  - "Uma natureza: `where nat.codigo_natureza_juridica = '2135'`."
  - "Busca por texto: `nat.descricao_natureza_juridica ilike '%limitada%'`."
resposta_esperada_fixtures:
  colunas: [codigo_natureza_juridica, descricao_natureza_juridica, ativos]
  linhas:
    - ['2062', Sociedade Empresária Limitada, 7]
    - ['2135', Empresário (Individual), 4]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  nat.codigo_natureza_juridica,
  nat.descricao_natureza_juridica,
  count(*) as ativos
from {{ ref('fct_estabelecimentos') }} as fct
inner join {{ ref('dim_natureza_juridica') }} as nat
  on fct.sk_natureza_juridica = nat.sk_natureza_juridica
where fct.eh_ativa
group by nat.codigo_natureza_juridica, nat.descricao_natureza_juridica
order by nat.codigo_natureza_juridica
