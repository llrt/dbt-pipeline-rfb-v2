{# ---
id: gq_raw__cnae_secundario__01
conceito: cnae_secundario
camada: raw
perguntas:
  - "Quantos estabelecimentos a RFB publicou com algum CNAE secundário preenchido?"
  - "Confira no raw o formato da lista de CNAEs secundários."
intencao: "Auditoria do raw: quantas linhas do mês mais recente têm o campo CNAE FISCAL SECUNDÁRIA preenchido e quantos códigos ele lista."
tabelas: [rfb.estabelecimentos]
colunas_chave: [_mes_referencia, cnaes_secundarios]
armadilhas:
  - "No raw a lista é um texto separado por vírgula; para filtrar por CNAE secundário use a ponte bridge_estabelecimento_cnae_secundario (gq_core__cnae_secundario__01)."
  - "Um `like '%4741500%'` no texto casa códigos que contêm a sequência; use a ponte."
variacoes:
  - "Outro mês: troque o filtro de `_mes_referencia`."
resposta_esperada_fixtures:
  colunas: [com_secundario, linhas, codigos_listados]
  linhas:
    - [1, 18, 2]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  count(*) filter (where nullif(trim(fon.cnaes_secundarios), '') is not null) as com_secundario,
  count(*) as linhas,
  sum(len(string_split(nullif(trim(fon.cnaes_secundarios), ''), ','))) as codigos_listados
from {{ source('rfb', 'estabelecimentos') }} as fon
where fon._mes_referencia = (select max(ult._mes_referencia) from {{ source('rfb', 'estabelecimentos') }} as ult)
order by com_secundario
