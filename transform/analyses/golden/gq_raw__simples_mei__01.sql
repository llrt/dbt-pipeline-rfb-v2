{# ---
id: gq_raw__simples_mei__01
conceito: simples_mei
camada: raw
perguntas:
  - "Quantas empresas a RFB publicou como optantes pelo Simples e pelo MEI?"
  - "Que valores vieram nos campos de opção do arquivo Simples?"
intencao: "Auditoria do raw: combinação de OPÇÃO PELO SIMPLES e OPÇÃO PELO MEI no mês mais recente."
tabelas: [rfb.simples]
colunas_chave: [_mes_referencia, opcao_simples, opcao_mei]
armadilhas:
  - "O arquivo Simples é por EMPRESA (CNPJ básico); empresa sem linha no arquivo vira `false` no gold."
  - "Para contar MEI ativos use `opcao_mei` em fct_estabelecimentos (gq_core__simples_mei__01) ou `qtd_ativos_mei`."
  - "O raw só traz 'S', 'N' ou vazio: a flag é a situação no extrato, não o histórico."
variacoes:
  - "Outro mês: troque o filtro de `_mes_referencia`."
resposta_esperada_fixtures:
  colunas: [opcao_simples, opcao_mei, empresas]
  linhas:
    - [S, N, 14]
    - [S, S, 2]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  fon.opcao_simples,
  fon.opcao_mei,
  count(*) as empresas
from {{ source('rfb', 'simples') }} as fon
where fon._mes_referencia = (select max(ult._mes_referencia) from {{ source('rfb', 'simples') }} as ult)
group by fon.opcao_simples, fon.opcao_mei
order by fon.opcao_simples, fon.opcao_mei
