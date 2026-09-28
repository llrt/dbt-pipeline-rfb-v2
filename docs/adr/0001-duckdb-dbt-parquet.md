# ADR-0001 — DuckDB + dbt-duckdb sobre Parquet

**Contexto.** O original usava Spark no Databricks Community Edition, com limite de 1 h de cluster, perda
do Hive Metastore ao desligar e notebooks grandes demais para exportar (ver `5 - Autoavaliação`). O pedido
é portar para dbt com engine DuckDB sobre Parquet local/S3.

**Decisão.** dbt-core + adaptador `dbt-duckdb`; DuckDB ≥ 1.5 como motor; Parquet como formato de
persistência de todas as camadas (raw e gold). O arquivo `.duckdb` é cache descartável.

**Alternativas.** Spark local (pesado para laptop, JVM); Postgres (carga lenta, sem Parquet nativo);
Polars sem dbt (sem linhagem/testes/docs declarativos).

**Consequências.** Roda num laptop (máquina de referência: 48 GB RAM, 15 núcleos). Qualquer ferramenta que
lê Parquet consome o gold. Dependemos da compatibilidade dbt-core ↔ dbt-duckdb (fixada no `uv.lock`).
