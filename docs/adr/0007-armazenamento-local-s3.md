# ADR-0007 — Armazenamento local-first; S3/Tigris opcional

**Contexto.** O original usou o Tigris (S3-compatível) como área de pouso por limitação do Databricks. O
pedido admite Parquet local ou em S3/Tigris.

**Decisão.** Um único `RAIZ_DADOS` (caminho local ou `s3://bucket/prefixo`). Leitura/escrita S3 pelo DuckDB
(`httpfs` + `CREATE SECRET` com `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_ENDPOINT_URL_S3`,
região `auto`, estilo de URL configurável) e comando `rfb sincronizar` (boto3, como o `subir_arquivos_tigris.py`
original) para publicar `raw/` e `gold/`. Testes usam `moto` em modo servidor.

**Consequências.** O caminho padrão não depende de nuvem. Não há credenciais Tigris neste ambiente: a
validação real no Tigris é um passo manual documentado.

## Atualização 2026-09-29 (revisão R1: R1-08, R1-09, P7)

O modo `s3://` não fechava de ponta a ponta. Decisões:

- **Duas raízes.** `RAIZ_DADOS` (local ou `s3://bucket/prefixo`) é onde vivem as fontes e o `gold/` lidos
  pelo dbt. `RAIZ_DADOS_LOCAL` (padrão `./data`) é onde o EL grava, onde fica o arquivo
  `warehouse.duckdb` e onde ficam os temporários do DuckDB: **sempre local**, porque o DuckDB não abre
  banco gravável em S3. No target `s3`, `path`/`temp_directory` usam `RAIZ_DADOS_LOCAL` e
  `external_root`/fontes usam `RAIZ_DADOS`.
- **Fluxo s3.** `rfb ingerir` (grava em `RAIZ_DADOS_LOCAL`) → `rfb sincronizar` (envia `raw/` e `gold/`) →
  `dbt build --target s3` (lê `s3://…/raw`, grava `gold` em `s3://…/gold`). O `sync` compara tamanho e
  sha256 (metadado `sha256` do objeto), não o ETag.
- **Secret.** O secret S3 do DuckDB vem só do profile `s3` (`transform/profiles.yml`), sem valor
  padrão para as três variáveis `AWS_*`/`AWS_ENDPOINT_URL_S3`: se faltar, o dbt falha nomeando a
  variável (paridade com a validação do Python). O helper Python `sql_create_secret` foi **removido**:
  não era usado em produção, duplicava o profile e interpolava credenciais sem escapar `'`.
- **Variável vazia = padrão** (`configuracao.py`), e `.env.example` traz as chaves opcionais comentadas.
