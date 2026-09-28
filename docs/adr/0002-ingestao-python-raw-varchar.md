# ADR-0002 — Ingestão em Python fora do dbt; raw em Parquet all-VARCHAR particionado por mês

**Contexto.** dbt transforma dados que já estão acessíveis ao warehouse; ele não baixa arquivos. Os CSV da
RFB vêm zipados, sem header, em latin-1, com aspas e escapes irregulares e campos multilinha.

**Decisão.** Pacote Python `rfb_pipeline` faz o EL: baixa, valida, descompacta e converte cada CSV para
Parquet com DuckDB `read_csv` (opções equivalentes às do Spark original), **todas as colunas como
VARCHAR**, com colunas técnicas (`_arquivo_origem`, `_mes_referencia`, `_data_referencia`, `_ingerido_em`),
particionado `mes_referencia=YYYY-MM`. Rejeitos do parser são gravados e limitados por limiar.

**Por que all-VARCHAR.** O original usava `inferSchema`, que transformava códigos com zero à esquerda (CNAE
`0111301`, município `0001`) em inteiros. Bronze fiel ao arquivo; tipagem explícita e testada no staging.

**Consequências.** dbt lê o raw via `external_location`. Vários meses podem coexistir; o dbt escolhe um via
var `mes_referencia`. Reprocessar um mês é idempotente (manifesto com sha256).
