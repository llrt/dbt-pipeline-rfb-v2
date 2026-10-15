{# ---
id: gq_intermediate__cnae_principal__01
conceito: cnae_principal
camada: intermediate
perguntas:
  - "Que CNAEs principais do cadastro não existem na tabela CNAE da Base dos Dados?"
  - "Por que um CNAE aparece como NÃO INFORMADO no gold?"
intencao: "Linhagem: CNAEs principais sem par na CNAE da Base dos Dados (viram `sk_cnae` -1 no gold), com o número de estabelecimentos."
tabelas: [int_estabelecimentos__enriquecidos]
colunas_chave: [cnae_principal, tem_cnae_bd]
armadilhas:
  - "Estabelecimentos com CNAE sem par somem de qualquer recorte por seção, divisão ou classe: ficam no membro -1."
  - "Esses CNAEs existem no domínio da RFB; é a hierarquia da Base dos Dados que não os tem."
variacoes:
  - "Só ativos: `and situacao_codigo = 2`."
resposta_esperada_fixtures:
  colunas: [cnae_principal, estabelecimentos]
  linhas:
    - ['3511500', 1]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  cnae_principal,
  count(*) as estabelecimentos
from {{ ref('int_estabelecimentos__enriquecidos') }}
where not tem_cnae_bd
group by cnae_principal
order by cnae_principal
