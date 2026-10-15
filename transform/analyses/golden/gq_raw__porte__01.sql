{# ---
id: gq_raw__porte__01
conceito: porte
camada: raw
perguntas:
  - "Que códigos de porte a RFB publicou no arquivo Empresas?"
  - "Quantas empresas vieram sem porte no raw?"
intencao: "Auditoria do raw: códigos de PORTE DA EMPRESA no mês mais recente (00 não informado, 01 micro, 03 pequena, 05 demais; vazio vira NULL)."
tabelas: [rfb.empresas]
colunas_chave: [_mes_referencia, porte]
armadilhas:
  - "Camada de auditoria: para o porte com rótulo use gq_core__porte__01."
  - "O porte é da EMPRESA (CNPJ básico), não do estabelecimento; MEI não é porte."
  - "O porte é declarado, não medido: não há receita nos dados abertos."
  - "'00' (N/A da RFB) e o vazio (membro -1 NÃO INFORMADO no gold) são coisas diferentes."
variacoes:
  - "Outro mês: troque o filtro de `_mes_referencia`."
resposta_esperada_fixtures:
  colunas: [porte, empresas]
  linhas:
    - ['00', 3]
    - ['01', 6]
    - ['03', 4]
    - ['05', 3]
    - [null, 1]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  fon.porte,
  count(*) as empresas
from {{ source('rfb', 'empresas') }} as fon
where fon._mes_referencia = (select max(ult._mes_referencia) from {{ source('rfb', 'empresas') }} as ult)
group by fon.porte
order by fon.porte
