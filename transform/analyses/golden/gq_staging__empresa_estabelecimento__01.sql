{# ---
id: gq_staging__empresa_estabelecimento__01
conceito: empresa_estabelecimento
camada: staging
perguntas:
  - "No mês selecionado, quantos estabelecimentos e quantas empresas distintas há no staging?"
  - "Confira no staging se algum CNPJ completo se repete."
intencao: "Auditoria do staging: estabelecimentos, CNPJs completos e CNPJs básicos distintos do mês selecionado, depois da tipagem."
tabelas: [stg_rfb__estabelecimentos]
colunas_chave: [cnpj_completo, cnpj_raiz]
armadilhas:
  - "O staging tem só o mês selecionado do build (o do gold corrente), não todos os meses do raw."
  - "Empresa = CNPJ básico (`cnpj_raiz`); estabelecimento = CNPJ completo. No gold, empresas se contam pelas matrizes (gq_core__empresa_estabelecimento__01)."
  - "O staging ainda tem nome fantasia e endereço: nunca os selecione (ADR-0008)."
variacoes:
  - "Por UF: acrescente `uf` ao `select` e um `group by`."
resposta_esperada_fixtures:
  colunas: [estabelecimentos, cnpjs_completos, cnpjs_basicos]
  linhas:
    - [18, 18, 16]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  count(*) as estabelecimentos,
  count(distinct cnpj_completo) as cnpjs_completos,
  count(distinct cnpj_raiz) as cnpjs_basicos
from {{ ref('stg_rfb__estabelecimentos') }}
order by estabelecimentos
