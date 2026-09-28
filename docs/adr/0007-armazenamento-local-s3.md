# ADR-0007 — Armazenamento local-first; S3/Tigris opcional

**Contexto.** O original usou o Tigris (S3-compatível) como área de pouso por limitação do Databricks. O
pedido admite Parquet local ou em S3/Tigris.

**Decisão.** Um único `DATA_ROOT` (caminho local ou `s3://bucket/prefixo`). Leitura/escrita S3 pelo DuckDB
(`httpfs` + `CREATE SECRET` com `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_ENDPOINT_URL_S3`,
região `auto`, estilo de URL configurável) e comando `rfb sync` (boto3, como o `subir_arquivos_tigris.py`
original) para publicar `raw/` e `gold/`. Testes usam `moto` em modo servidor.

**Consequências.** O caminho padrão não depende de nuvem. Não há credenciais Tigris neste ambiente: a
validação real no Tigris é um passo manual documentado.
