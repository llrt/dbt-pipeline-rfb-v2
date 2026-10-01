# ADR-0016 — Publicação opcional do gold no MotherDuck e formas de acesso pelo Power BI

**Contexto.** Pedido do usuário (2026-10-01): verificar a possibilidade de publicar as tabelas finais numa conta
MotherDuck, quando configurada, e deixar claro como o Power BI acessa os marts (DuckDB local, MotherDuck ou
Parquet). Hoje o dbt grava os marts como Parquet em `gold/` (materialização `external`) e o
`warehouse.duckdb` só tem views sobre esses arquivos. Não há token do MotherDuck configurado no ambiente.

Fatos verificados na documentação oficial:
- dbt-duckdb conecta ao MotherDuck com `path: "md:<banco>"` e lê o token de `MOTHERDUCK_TOKEN`
  ([MotherDuck — dbt](https://motherduck.com/docs/integrations/transformation/dbt/)).
- O Power BI conecta ao MotherDuck pelo **conector PostgreSQL nativo**, via o *Postgres endpoint*
  (servidor `pg.<região>-aws.motherduck.com`, usuário `postgres`, senha = token), em **Import ou
  DirectQuery**; no Power BI Service exige o On-premises Data Gateway
  ([Power BI Desktop com MotherDuck](https://motherduck.com/docs/integrations/bi-tools/powerbi/powerbi-desktop/),
  [Power BI Service](https://motherduck.com/docs/integrations/bi-tools/powerbi/powerbi-service/)).
- Para arquivo DuckDB local, o caminho é o driver ODBC do DuckDB (+ conector Power Query customizado, que a
  MotherDuck chama de legado).

**Decisão.**
- **Publicação desacoplada do dbt**: novo subcomando `rfb publicar --destino motherduck`, que, **só quando
  `MOTHERDUCK_TOKEN` e `MOTHERDUCK_BANCO` estiverem definidos**, faz `ATTACH 'md:<banco>'` e recria cada
  tabela do gold (`CREATE OR REPLACE TABLE … AS SELECT * FROM read_parquet(…)`): dimensões, fatos, ponte,
  marts do original e de analytics, e a série `fct_resumo_mensal` (todas as partições). Sem configuração, sai
  com mensagem clara e código 0 ("MotherDuck não configurado; nada publicado"). O gold em Parquet continua
  sendo o contrato; o dbt não muda de materialização.
- Alternativa descartada: um target dbt `motherduck` com os marts como tabelas no MotherDuck — exigiria
  trocar a materialização `external` por target, duplicar configurações e testes, e acoplar o build à rede.
- `rfb atualizar` (B8) chama a publicação no fim, quando configurada.
- Testes sem rede: a mesma função publica num destino DuckDB local (arquivo), o que cobre o SQL gerado; o
  `md:` real só é exercido manualmente com a conta do usuário (primeira publicação real só com OK dele).
- **Guia Power BI**: seção nova "Como o Power BI acessa os dados" comparando Parquet (`gold/`), DuckDB local
  (ODBC) e MotherDuck (PostgreSQL endpoint), com modo (Import/DirectQuery), instalação, atualização no
  Service (gateway), travas de arquivo e recomendação por cenário.
- Tudo é **adição** (ADR-0006).

**Consequências.** Nova dependência opcional de rede/credencial (`MOTHERDUCK_TOKEN`, nunca no repositório);
custo/limites do plano MotherDuck por conta do usuário; o tamanho real (fato com ~65 M linhas) deve ser
avaliado antes de publicar a fato detalhada — a publicação permite escolher as tabelas.
