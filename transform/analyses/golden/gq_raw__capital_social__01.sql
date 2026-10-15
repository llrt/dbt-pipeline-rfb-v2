{# ---
id: gq_raw__capital_social__01
conceito: capital_social
camada: raw
perguntas:
  - "Em que formato a RFB publica o capital social?"
  - "Confira no raw os valores de capital social que vieram com centavos."
intencao: "Auditoria do raw: formato do CAPITAL SOCIAL DA EMPRESA (texto com vírgula decimal) e a conversão que o staging aplica."
tabelas: [rfb.empresas]
colunas_chave: [_mes_referencia, capital_soc]
armadilhas:
  - "O raw usa vírgula decimal ('1000,50'); somar sem converter falha ou dá errado."
  - "Para somar capital use o gold, só nas matrizes (gq_core__capital_social__01)."
variacoes:
  - "Outro mês: troque o filtro de `_mes_referencia`."
resposta_esperada_fixtures:
  colunas: [capital_soc, capital_convertido, empresas]
  linhas:
    - ['0,00', 0.0, 1]
    - ['1000,00', 1000.0, 15]
    - ['1000,50', 1000.5, 1]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  fon.capital_soc,
  replace(fon.capital_soc, ',', '.')::decimal(18, 2) as capital_convertido,
  count(*) as empresas
from {{ source('rfb', 'empresas') }} as fon
where fon._mes_referencia = (select max(ult._mes_referencia) from {{ source('rfb', 'empresas') }} as ult)
group by fon.capital_soc
order by fon.capital_soc
