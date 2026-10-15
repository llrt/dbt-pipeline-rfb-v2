{# ---
id: gq_raw__matriz_filial__01
conceito: matriz_filial
camada: raw
perguntas:
  - "Que valores de identificador matriz/filial a RFB publicou no mês?"
  - "Confira no raw quantas matrizes e filiais vieram no arquivo."
intencao: "Auditoria do raw: distribuição do campo IDENTIFICADOR MATRIZ/FILIAL (1 matriz, 2 filial) no mês mais recente."
tabelas: [rfb.estabelecimentos]
colunas_chave: [_mes_referencia, ind_matriz_filial]
armadilhas:
  - "Camada de auditoria: para contar matrizes ou empresas use gq_core__matriz_filial__01."
  - "O valor é texto ('1', '2'); não use a ordem `0001` do CNPJ como sinônimo de matriz (CNPJ alfanumérico)."
  - "Filtre o mês: o raw guarda todos os meses ingeridos."
variacoes:
  - "Outro mês: troque o filtro de `_mes_referencia`."
  - "Por UF publicada: acrescente `uf` ao `select` e ao `group by`."
resposta_esperada_fixtures:
  colunas: [ind_matriz_filial, linhas]
  linhas:
    - ['1', 16]
    - ['2', 2]
--- #}
{{ config(tags=['escopo_adicao', 'golden_query'], meta={'escopo': 'adicao'}) }}

select
  fon.ind_matriz_filial,
  count(*) as linhas
from {{ source('rfb', 'estabelecimentos') }} as fon
where fon._mes_referencia = (select max(ult._mes_referencia) from {{ source('rfb', 'estabelecimentos') }} as ult)
group by fon.ind_matriz_filial
order by fon.ind_matriz_filial
