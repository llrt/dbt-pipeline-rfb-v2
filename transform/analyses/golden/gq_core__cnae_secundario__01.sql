{# ---
id: gq_core__cnae_secundario__01
conceito: cnae_secundario
camada: core
perguntas:
  - "Quantos estabelecimentos ativos trabalham com o CNAE 4679699, como principal ou secundário?"
  - "Quem vende material de construção mesmo que não seja a atividade principal?"
intencao: "Ativos que têm um CNAE como principal ou como secundário (ponte bridge_estabelecimento_cnae_secundario), sem contar o mesmo estabelecimento duas vezes."
tabelas: [fct_estabelecimentos, dim_cnae, bridge_estabelecimento_cnae_secundario]
colunas_chave: [cnpj_completo, sk_cnae, codigo_cnae_secundario]
armadilhas:
  - "A ponte é muitos-para-muitos: junte e conte `distinct cnpj_completo`, senão um estabelecimento com o CNAE nos dois papéis conta duas vezes."
  - "O CNAE secundário fica fora da camada semântica: só SQL."
  - "`codigo_cnae_secundario` guarda o código original; `sk_cnae` = -1 quando ele não tem par na Base dos Dados."
variacoes:
  - "Outro CNAE: troque o código nos dois filtros."
  - "Por município: junte dim_municipio por `sk_municipio`."
resposta_esperada_fixtures:
  colunas: [ativos_com_o_cnae, como_principal, como_secundario]
  linhas:
    - [1, 0, 1]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

with alvo as (
  select
    fct.cnpj_completo,
    'principal' as papel
  from {{ ref('fct_estabelecimentos') }} as fct
  inner join {{ ref('dim_cnae') }} as cnae
    on fct.sk_cnae = cnae.sk_cnae
  where fct.eh_ativa and cnae.codigo_subclasse = '4679699'
  union
  select
    fct.cnpj_completo,
    'secundario' as papel
  from {{ ref('fct_estabelecimentos') }} as fct
  inner join {{ ref('bridge_estabelecimento_cnae_secundario') }} as bri
    on fct.cnpj_completo = bri.cnpj_completo
  where fct.eh_ativa and bri.codigo_cnae_secundario = '4679699'
)

select
  count(distinct cnpj_completo) as ativos_com_o_cnae,
  count(distinct cnpj_completo) filter (where papel = 'principal') as como_principal,
  count(distinct cnpj_completo) filter (where papel = 'secundario') as como_secundario
from alvo
order by ativos_com_o_cnae
