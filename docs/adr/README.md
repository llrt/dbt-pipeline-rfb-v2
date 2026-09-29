# Registro de decisões (ADR)

Formato curto: contexto → decisão → consequências. Status: `aceita`, `substituída por ADR-XXXX`.
Decisões de processo/execução do projeto também ficam em [`.specs/STATE.md`](../../.specs/STATE.md).

| ADR | Título | Status |
|---|---|---|
| [0001](0001-duckdb-dbt-parquet.md) | DuckDB + dbt-duckdb sobre Parquet | aceita |
| [0002](0002-ingestao-python-raw-varchar.md) | Ingestão em Python fora do dbt; raw em Parquet all-VARCHAR particionado por mês | aceita |
| [0003](0003-fonte-rfb-webdav.md) | Nova fonte RFB (WebDAV) e mês de referência | aceita |
| [0004](0004-data-referencia-deterministica.md) | Data de referência determinística no lugar de `now()` | aceita |
| [0005](0005-paridade-modelos-originais.md) | Paridade dos modelos originais; adições no star schema | aceita |
| [0006](0006-marcacao-escopo.md) | Marcação de escopo original × adição no código | aceita |
| [0007](0007-armazenamento-local-s3.md) | Armazenamento local-first; S3/Tigris opcional | aceita |
| [0008](0008-minimizacao-dados-pessoais.md) | Minimização de dados pessoais | aceita |
| [0009](0009-estrategia-testes.md) | Estratégia de testes em camadas e severidades | aceita |
| [0010](0010-fixtures-sinteticas.md) | Fixtures sintéticas com respostas conhecidas | aceita |
| [0011](0011-processo-equipe-agentes.md) | Processo: equipe de agentes, roteamento de modelos e lotes | aceita |
| [0012](0012-atualizacao-mensal.md) | Atualização mensal: mês novo, completude, retenção, série histórica | aceita |
| [0013](0013-modelo-estrela-bi.md) | Modelo estrela otimizado para BI (Power BI) | aceita |
| [0014](0014-convencao-idioma.md) | Convenção de idioma: vocabulário dbt/ferramentas em inglês, resto em português | aceita |
