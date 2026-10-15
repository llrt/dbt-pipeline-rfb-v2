{# ---
id: gq_raw__empresa_estabelecimento__01
conceito: empresa_estabelecimento
camada: raw
perguntas:
  - "Quantas linhas de estabelecimentos e quantos CNPJs básicos a RFB publicou em cada mês?"
  - "O arquivo Estabelecimentos do mês veio completo?"
  - "Confira no raw quantos estabelecimentos a Receita publicou."
intencao: "Auditoria do raw: linhas e CNPJs básicos distintos do arquivo Estabelecimentos por mês publicado."
tabelas: [rfb.estabelecimentos]
colunas_chave: [_mes_referencia, cnpj_raiz, cnpj_ordem, cnpj_dv]
armadilhas:
  - "Camada de auditoria e linhagem: para contar empresas ou estabelecimentos numa pergunta de negócio use o gold (gq_core__empresa_estabelecimento__01) ou a semântica."
  - "O raw guarda TODOS os meses ingeridos: sem `group by` ou filtro em `_mes_referencia` a contagem soma meses."
  - "Tudo é VARCHAR no raw; o CNPJ completo é cnpj_raiz || cnpj_ordem || cnpj_dv, sem tipagem nem zeros à esquerda garantidos."
  - "O raw tem nome fantasia, endereço e contatos: nunca os selecione (ADR-0008)."
variacoes:
  - "Um mês: `where _mes_referencia = '2026-09'`."
  - "Por UF publicada: acrescente `uf` ao `select` e ao `group by`."
  - "Empresas: troque a fonte por `source('rfb', 'empresas')` e conte `cnpj_raiz`."
resposta_esperada_fixtures:
  colunas: [_mes_referencia, linhas_estabelecimentos, cnpjs_basicos]
  linhas:
    - [2026-08, 17, 16]
    - [2026-09, 18, 16]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  _mes_referencia,
  count(*) as linhas_estabelecimentos,
  count(distinct cnpj_raiz) as cnpjs_basicos
from {{ source('rfb', 'estabelecimentos') }}
group by _mes_referencia
order by _mes_referencia
