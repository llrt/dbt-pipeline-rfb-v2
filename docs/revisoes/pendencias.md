# Pendências para as revisões (registradas pelo líder)

Achados do líder na verificação dos lotes, a serem tratados pelo revisor da fase indicada
(correção sempre por agente novo no nível da tarefa de origem).

| # | Lote/arquivo | Achado | Revisão | Status |
|---|---|---|---|---|
| P1 | B9a · `docs/guia-dbt/01-fundamentos.md` L434–438 | Afirma que "espaço = união / vírgula = interseção" vale a partir do dbt 1.12 e que "`or`/`and` não são mais operadores". Incorreto: essa sempre foi a sintaxe de seleção do dbt; `or`/`and` nunca foram operadores. Reescrever sem a ressalva de versão. | R5 | aberto |
| P2 | B9a · mesmo arquivo | Snippets de unit tests/contratos seguem o design (ARCHITECTURE), não o código final; alinhar com `transform/` depois de B5–B7. | R5 | aberto |
| P3 | B1 · `Makefile` alvo `lint` | Templater dbt do sqlfluff abre `DATA_ROOT/warehouse.duckdb`; garantir `mkdir -p $(DATA_ROOT)` antes do lint quando existirem modelos. | B4 (brief) | resolvido em T10 |
| P4 | B2 · `src/rfb_pipeline/rfb_client.py` | Download: só 3 tentativas no total e sem velocidade mínima; o WebDAV da RFB trava/fica lento (observado no B3). Renovar tentativas enquanto houver progresso e abortar/retomar se a taxa ficar abaixo de um mínimo por N s. | B4 (brief) | resolvido em T10 |
| P5 | B3 · leitura raw | DuckDB ativa hive automaticamente em caminhos `mes_referencia=`; fontes dbt devem usar glob `<entidade>/mes_referencia=*/*.parquet` e escolher explicitamente entre `mes_referencia` (hive) e `_mes_referencia` (gravada). | B4 (brief) | resolvido em T12 |
| P6 | B4 · `rfb_client.baixar_com_retry` | Contador de tentativas só avança sem progresso: servidor que sempre avança um pouco e nunca termina não tem teto. Avaliar teto global (tempo total ou nº máximo de retomadas). | R1 | confirmado (R1-01) → F1a |
| P7 | B4 · ADR-0007 | Implementação usa `DATA_ROOT_LOCAL` para o EL quando `DATA_ROOT=s3://`; atualizar ADR-0007/ARCHITECTURE §4 para refletir isso. | R1 | confirmado e ampliado (R1-08) → F1a |
| P8 | B4 · guia dbt | Unit tests dbt sobre modelos que leem fontes `external_location` precisam de `format: sql` no `given` (o builder de fixtures tenta introspectar a relação). Documentar no guia parte 2. | B9b | aberto |
| P9 | F1a · operação | 1ª execução em checkout novo pode levar minutos (download de dependências via `uv sync` e da extensão `httpfs` do DuckDB no teste `dbt debug --target s3`); execuções seguintes ~20 s. Documentar no README/guia ("primeira execução") e considerar marcar o teste s3 como opcional offline. | B8/B9b | aberto |
