# ADR-0017 — Avaliação do dbt Fusion (dbt v2): adiar a migração

**Contexto.** Pedido do usuário (2026-10-02): avaliar o uso do dbt Fusion no lugar do dbt-core, com ganhos e
mudanças necessárias, sem alterar o projeto. O Fusion virou o **dbt v2** (GA em 2026-09-14), um binário Rust
com adaptador DuckDB embutido (driver ADBC, DuckDB 1.5.4) e documentado como GA só na linha de comando. O épico de
paridade com o dbt-duckdb do v1 ([dbt-fusion#1593](https://github.com/dbt-labs/dbt-fusion/issues/1593))
continua aberto.

A avaliação foi prática. O dbt 2.0.6 (`pip install dbt`) foi instalado num ambiente isolado e rodou
`parse`, `compile`, `build`, `source freshness`, `ls`, `docs generate`, `show` e `lint` numa **cópia** de
`transform/`, sobre as fixtures do `make ci` (mês 2026-08). As comparações usaram o dbt-core 1.12.5 com as
mesmas fixtures.

**Ganhos medidos.**

| Aspecto | dbt-core 1.12 | dbt v2 |
|---|---|---|
| `parse` | 3,9 s | 1,0 s |
| Lint | sqlfluff 27 s no CI | `dbt lint` 1,1 s, com regras diferentes: 10 erros e 59 avisos a triar |
| `build` sobre as fixtures (tempo total) | 8–11 s | 15 s |
| `build` sobre as fixtures (CPU) | 7–9 s | 3 s |
| Erros de macro, variável ou teste inexistente | aparecem no `compile` | aparecem já no `parse` |
| Linhagem por coluna e extensão do VS Code | — | locais, sem conta na plataforma |

Com dado real, quem domina o tempo é o DuckDB, praticamente a mesma versão nos dois motores, então não se
espera ganho de execução (não foi medido). O ganho que mais pesa é na experiência de desenvolvimento.

**Incompatibilidades encontradas.**

| # | Problema no v2 | Gravidade | Caminho |
|---|---|---|---|
| 1 | `parse` com 67 erros: `meta`, `tags`, `freshness` e `loaded_at_field` fora de `config:` | baixa | `dbt-autofix deprecations` (9 arquivos, ~500 linhas). A versão convertida **passa no dbt-core 1.12** (PASS=354 WARN=5, série particionada) |
| 2 | `options={'partition_by': …}` da materialização `external` é rejeitado ([dbt#16526](https://github.com/dbt-labs/dbt/issues/16526), aberto). O autofix move a opção para `meta` sem avisar, e a `fct_resumo_mensal` perde a partição | alta | `location` por mês (`…/mes_referencia=AAAA-MM/`) ou `COPY … PARTITION_BY` em post-hook. Exige revalidar o backfill (P22, L-003) |
| 3 | `config_options.temp_directory` ignorado em silêncio: o spill vai para `warehouse.duckdb.tmp` | alta com dado real | Testar `settings.temp_directory`, que no v1 falhava após o 1º spill (B8). `test_profiles_threads` quebra |
| 4 | Unit test com coluna do tipo lista não é suportado (2 testes de CNAEs secundários) | média | Comparar a lista serializada como texto, ou mover a regra para teste de dados |
| 5 | `dbt source freshness` falha nas fontes com `external_location`: consulta `rfb.cnaes`, que não existe | alta (gate do pipeline) | Teste singular sobre `read_parquet`, a partir do `extrato_desatualizado` |
| 6 | `sqlfluff-templater-dbt` depende do dbt-core, e os dois pacotes instalam o executável `dbt` | média | `dbt lint`, com triagem de regras, ou sqlfluff com templater jinja |
| 7 | Saída de `dbt show` em outro formato; `docs generate` sem `catalog.json`; seletores com +1 a +4 nós; `manifest.json` e `run_results.json` lidos por `gerar_qualidade_dados.py` e ~8 testes de integração | média | Recalibrar os testes de escopo e conferir os consumidores dos artefatos. O orquestrador chama `dbt` por subprocesso e segue funcionando |
| 8 | Dependências e CI: `dbt-core` + `dbt-duckdb` → `dbt`; driver baixado na 1ª execução; aviso de análise estática no `*COLUMNS(...)` do teste de paridade, que só avisa | baixa | `pyproject.toml`, `uv.lock` e cache no CI |
| 9 | Guia dbt (capítulos 01–05) e ADRs escritos para o dbt-core 1.12 | média | Revisar comandos, sintaxe de config, lint e unit tests |
| 10 | Licença: `pip install dbt` instala a distribuição sob a licença proprietária (gratuita) do dbt v2; a Apache 2.0 é o `dbt-oss`, instalado à parte | decisão do usuário | Confirmar se o `dbt-oss` traz o adaptador DuckDB antes de escolher |

O que funcionou sem mudança:
- `external` sem `options`, que cria uma tabela temporária e faz `COPY … (format parquet)`;
- contratos, `store_failures`, `on-run-end` com `results`, `dbt_utils` e `dbt_expectations` (já declaram `<3.0.0`);
- `settings` (`threads`, `memory_limit`);
- `extensions: [httpfs]` e `secrets` S3 no target `s3`.

**Decisão.**
- **Adiar a migração para o dbt v2.** O projeto continua no dbt-core 1.12 + dbt-duckdb. Os itens 2, 3 e 5
  afetam a série mensal, o spill com dado real e um gate do pipeline, e o adaptador DuckDB do v2 tem duas
  semanas de GA.
- **Antecipação permitida, sem risco:** o item 1 (`dbt-autofix` nos YAMLs) vale para os dois motores e pode
  entrar num lote próprio, verificado por `make ci`, quando o usuário pedir.
  *Aplicado em 2026-10-02 no lote AF (AD-036).* O `options` da `fct_resumo_mensal` ficou fora, porque movê-lo para
  `meta` desliga a partição no dbt-core. No dbt v2, o `parse` caiu de 67 erros para 1, justamente esse `options`.
- **Critérios para reavaliar** (todos necessários):
  1. `options` da materialização `external` aceito no v2, com `partition_by` gravando partições hive
     (dbt#16526 fechado), ou um caminho alternativo validado no backfill;
  2. `temp_directory` aplicado pelo profile, verificado com `current_setting('temp_directory')`;
  3. `dbt source freshness` funcionando com `external_location`, ou o gate substituído por teste singular;
  4. unit tests com colunas de tipo lista suportados, ou os 2 testes reescritos;
  5. licença definida pelo usuário (dbt v2 ou `dbt-oss`, com adaptador DuckDB confirmado).
- **Gatilhos para reabrir a avaliação:** nova versão menor do dbt v2 com notas sobre DuckDB, fechamento do
  dbt#16526 ou do épico dbt-fusion#1593, ou pedido do usuário.
- **Como reavaliar:** repetir o roteiro numa cópia (venv isolado, `dbt-autofix`, `build` sobre as fixtures,
  `freshness`, `ls` por seletor, `show` de `temp_directory`). Se os critérios 1–4 passarem, fazer a migração
  num lote médio (itens 2–9) e validar com dado real antes do merge (critério 2 e paridade).

**Consequências.**
- Nada muda no código agora.
- A dívida conhecida fica registrada: sqlfluff com templater dbt e dependência de `options` e
  `config_options`, que são específicos do dbt-duckdb do v1. O YAML no formato antigo deixou de ser dívida
  com o lote AF.
- O guia dbt segue descrevendo o dbt-core.

Fontes: [DuckDB Now Ships inside dbt v2](https://duckdb.org/2026/09/22/dbt-fusion),
[Supported features](https://docs.getdbt.com/docs/fusion/supported-features),
[Upgrading to v2](https://docs.getdbt.com/docs/dbt-versions/core-upgrade/upgrading-to-fusion),
[DuckDB setup](https://docs.getdbt.com/docs/local/connect-data-platform/duckdb-setup),
[Install dbt](https://docs.getdbt.com/docs/local/install-dbt).
