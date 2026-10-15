{# ---
id: gq_original__empresa_estabelecimento__01
conceito: empresa_estabelecimento
camada: original
perguntas:
  - "Quantos estabelecimentos e empresas o bh_empresas do MVP tem?"
  - "Paridade: o modelo original perde estabelecimentos em relação ao gold?"
intencao: "Paridade com o MVP: estabelecimentos e CNPJs básicos em bh_empresas (que descarta por inner join quem não tem par)."
tabelas: [bh_empresas]
colunas_chave: [cnpj_completo, cnpj_raiz]
armadilhas:
  - "Só para paridade com o MVP: bh_empresas descarta estabelecimentos sem empresa, natureza, CNAE ou município (inner joins); para pergunta nova use fct_estabelecimentos."
  - "bh_empresas tem `nome` (mascarado): nunca o selecione numa resposta."
variacoes:
  - "Compare com gq_core__empresa_estabelecimento__01 para ver os descartes."
resposta_esperada_fixtures:
  colunas: [estabelecimentos, cnpjs_basicos]
  linhas:
    - [15, 13]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  count(*) as estabelecimentos,
  count(distinct cnpj_raiz) as cnpjs_basicos
from {{ ref('bh_empresas') }}
order by estabelecimentos
