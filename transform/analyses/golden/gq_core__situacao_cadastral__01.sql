{# ---
id: gq_core__situacao_cadastral__01
conceito: situacao_cadastral
camada: core
perguntas:
  - "Quantos estabelecimentos há em cada situação cadastral?"
  - "Quantas empresas estão ativas, suspensas, inaptas ou baixadas?"
intencao: "Estabelecimentos do mês do gold por situação cadastral (rótulo da dimensão)."
tabelas: [fct_estabelecimentos, dim_situacao_cadastral]
colunas_chave: [sk_situacao_cadastral, rotulo_situacao_cadastral]
armadilhas:
  - "Ativa ≠ em operação (IN 2.119, art. 9º, parágrafo único)."
  - "Empresa × estabelecimento: conta estabelecimentos. A situação é do estabelecimento; a 'situação da empresa' é a da matriz (filtre `eh_matriz`)."
  - "Só a situação no dia do extrato: transições entre dois extratos não aparecem."
variacoes:
  - "Por UF ou CNAE: junte a dimensão e acrescente ao `group by`."
  - "Só empresas: `where fct.eh_matriz`."
resposta_esperada_fixtures:
  colunas: [codigo_situacao_cadastral, rotulo_situacao_cadastral, estabelecimentos]
  linhas:
    - ['2', ATIVA, 11]
    - ['4', INAPTA, 1]
    - ['8', BAIXADA, 6]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  sit.codigo_situacao_cadastral,
  sit.rotulo_situacao_cadastral,
  count(*) as estabelecimentos
from {{ ref('fct_estabelecimentos') }} as fct
inner join {{ ref('dim_situacao_cadastral') }} as sit
  on fct.sk_situacao_cadastral = sit.sk_situacao_cadastral
group by sit.codigo_situacao_cadastral, sit.rotulo_situacao_cadastral
order by sit.codigo_situacao_cadastral
