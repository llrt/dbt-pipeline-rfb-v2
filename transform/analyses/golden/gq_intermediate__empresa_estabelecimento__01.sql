{# ---
id: gq_intermediate__empresa_estabelecimento__01
conceito: empresa_estabelecimento
camada: intermediate
perguntas:
  - "Quantos estabelecimentos ficam sem par de empresa, natureza, CNAE ou município?"
  - "Por que há estabelecimentos no membro NÃO INFORMADO das dimensões?"
intencao: "Linhagem: as flags `tem_*` do intermediate, que dizem quantos estabelecimentos vão para o membro -1 de cada dimensão no gold."
tabelas: [int_estabelecimentos__enriquecidos]
colunas_chave: [cnpj_completo, tem_empresa, tem_natureza, tem_cnae_bd, tem_municipio_bd]
armadilhas:
  - "O gold não descarta nada: o que não tem par vai para o membro -1 ('NÃO INFORMADO'); `bh_empresas` (original) descarta por inner join."
  - "Sem par de município inclui o exterior (código RFB 9707)."
variacoes:
  - "Por UF: acrescente `uf` (staging) ou `id_municipio_ibge`."
resposta_esperada_fixtures:
  colunas: [estabelecimentos, sem_empresa, sem_natureza, sem_cnae_bd, sem_municipio_bd]
  linhas:
    - [18, 0, 0, 1, 2]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  count(*) as estabelecimentos,
  count(*) filter (where not tem_empresa) as sem_empresa,
  count(*) filter (where not tem_natureza) as sem_natureza,
  count(*) filter (where not tem_cnae_bd) as sem_cnae_bd,
  count(*) filter (where not tem_municipio_bd) as sem_municipio_bd
from {{ ref('int_estabelecimentos__enriquecidos') }}
order by estabelecimentos
