# Pendências para as revisões (registradas pelo líder)

Achados do líder na verificação dos lotes, a serem tratados pelo revisor da fase indicada
(correção sempre por agente novo no nível da tarefa de origem).

| # | Lote/arquivo | Achado | Revisão | Status |
|---|---|---|---|---|
| P1 | B9a · `docs/guia-dbt/01-fundamentos.md` L434–438 | Afirma que "espaço = união / vírgula = interseção" vale a partir do dbt 1.12 e que "`or`/`and` não são mais operadores". Incorreto: essa sempre foi a sintaxe de seleção do dbt; `or`/`and` nunca foram operadores. Reescrever sem a ressalva de versão. | R5 | aberto |
| P2 | B9a · mesmo arquivo | Snippets de unit tests/contratos seguem o design (ARCHITECTURE), não o código final; alinhar com `transform/` depois de B5–B7. | R5 | aberto |
| P3 | B1 · `Makefile` alvo `lint` | Templater dbt do sqlfluff abre `DATA_ROOT/warehouse.duckdb`; garantir `mkdir -p $(DATA_ROOT)` antes do lint quando existirem modelos. | B4 (brief) | aberto |
| P4 | B2 · `src/rfb_pipeline/rfb_client.py` | Download: só 3 tentativas no total e sem velocidade mínima; o WebDAV da RFB trava/fica lento (observado no B3). Renovar tentativas enquanto houver progresso e abortar/retomar se a taxa ficar abaixo de um mínimo por N s. | B4 (brief) | aberto |
| P5 | B3 · leitura raw | DuckDB ativa hive automaticamente em caminhos `mes_referencia=`; fontes dbt devem usar glob `<entidade>/mes_referencia=*/*.parquet` e escolher explicitamente entre `mes_referencia` (hive) e `_mes_referencia` (gravada). | B4 (brief) | aberto |
