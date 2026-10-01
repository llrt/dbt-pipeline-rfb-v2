# RBP — Revisão de boas práticas (guia dbt × projeto)

Revisor: agente RBP (Traycer), 2026-10-01. Base: `main` `d111d09` (branch `revisao/rbp-boas-praticas`).
Pedido do usuário: "A partir do guia, revise o projeto à luz das melhores práticas relatadas. Verifique se não
há algum gap de testes ou de estrutura que poderia ser melhorado." Absorve a R5 (validação técnica do guia).
Escopo: `docs/guia-dbt/` (README + 01–05) contra a documentação oficial e o código; o projeto inteiro
(`src/`, `transform/`, `tests/`, `Makefile`, pre-commit, profiles) contra as práticas do guia.

## Veredito

**Guia: APROVADO COM RESSALVAS — precisa de uma rodada de correção antes de servir de checklist.** A espinha
técnica está certa: seleção por espaço/vírgula (P1), `severity: warn` ignorando `error_if`, `store_failures`
em `main_dbt_test__audit`, `is_incremental()`, contratos, P8. Mas há **43 erros**, 8 deles importantes. Os
importantes são instruções que quebram ou enganam quem as segue:

- `--state target/` não detecta nada (G14).
- `dbt run` também aplica contratos, e `dbt build` não roda freshness (G20).
- `temp_directory` evitaria OOM (G21). Na verdade, a chave no topo do profile é ignorada.
- Contatos "nunca entram no warehouse" (G23). Na verdade, o raw os guarda (ADR-0008).
- O "SQL compilado real" é fabricado (G24).
- Checks de gold e de atualização mensal aparecem como implementados sem existir (G29).
- Reprocessar um mês antigo com `--vars` sobrescreve o gold corrente sem aviso (G41).
- Unit tests rodariam "sem consultar o banco" (G06).

A P2 continua aberta, porque vários trechos ainda não batem com o código. A P1 e a P8 estão resolvidas; a P8
foi conferida empiricamente. A P9 está resolvida em parte: o guia a documenta, mas o README não.

**Projeto: APROVADO COM RESSALVAS — 0 bloqueantes, 4 importantes, 9 menores, 2 sugestões.** A base é boa:

- 100% dos modelos têm `description`.
- Todos os marts `original` e `core` têm contrato, e contratos sobre `external` funcionam (mutações N08 e
  N13 foram mortas por eles).
- São 200 data tests e 35 unit tests.
- Os testes de fonte barram antes do staging: na D2, `porte='9'` resultou em ERROR e SKIP=122.
- `make ci` passa em 57 s (80 testes de integração), `pytest tests/unit` passa (184) e `make lint` está limpo.

As lacunas importantes:

- **RBP-01:** o `temp_directory` dos três targets nunca chega ao DuckDB.
- **RBP-02:** uma deriva de formato no extrato zera em silêncio todas as datas ou todo o capital social, com o
  build verde (D1 e D3 sobreviveram).
- **RBP-03:** o `make ci` não roda os 184 testes unitários nem o lint.
- **RBP-04:** o freshness (spec STG AC 8) nunca é executado nem testado.

Das 23 mutações (20 de código e 3 de dados), **18 foram mortas e 5 sobreviveram**. Seis das mortas só foram
pegas pelo pytest sobre as fixtures; em dados reais o `dbt build` não as acusaria (RBP-13).

## Como verifiquei

- `make setup` + `caffeinate -i make ci` (verde, 57 s); `make lint` (verde); `pytest tests/unit` (184).
- Métricas pelo `manifest.json` e por um `catalog.json` gerado com `dbt docs generate --target ci`
  (em `--target-path` no scratchpad).
- Doc oficial: docs.getdbt.com (unit-tests, contract, build, severity, store_failures, access, clone,
  state-comparison-caveats, best-practices/how-we-structure/3-intermediate, data-tests/arguments),
  github.com/duckdb/dbt-duckdb (README e `credentials.py` instalado), duckdb.org (configuration, concurrency),
  dbt-project-evaluator, releases do dbt-checkpoint, PR do Elementary com suporte a DuckDB.
- Comandos do guia executados numa **cópia isolada** (`git archive HEAD transform` + fixtures próprias em
  scratchpad): `dbt ls`/`run`/`show`/`clone` e seleções.
- Mutações: harness que aplica a mutação na worktree, roda `make ci` completo (+ `pytest tests/unit` quando
  o arquivo é Python ou o Makefile), registra o resultado e reverte com `git checkout`. No fim, build limpo
  (P12); a worktree ficou limpa. As mutações de dados rodaram na cópia isolada.

---

## Parte 1 — Erros do guia

Gravidade: **importante** = instrução que quebra, engana sobre o comportamento do dbt/DuckDB ou apresenta
como implementado o que não existe; **menor** = imprecisão, número desatualizado ou trecho divergente.

| # | Grav. | Arquivo:linha | O que diz | Correto | Fonte / evidência |
|---|---|---|---|---|---|
| RBP-G01 | menor | `01-fundamentos.md:45-50` | Fusion "está em beta". | Desatualizado. A doc atual trata o motor Rust como "dbt v2"; ele é GA na dbt platform para Snowflake e preview nos demais adaptadores. Trocar por "ver status atual" + link. | docs.getdbt.com/docs/fusion/about-fusion; fusion-releases |
| RBP-G02 | menor | `01-fundamentos.md:175-211` (DAG) | `SEED→INT_EST`, `INT_EST/INT_MUN→bh_empresas`, `STG_RFB/STG_BD→audit`. | `bh_empresas` lê o **staging** (`bh_empresas.sql:6-24`); `audit__…` lê as **fontes raw** (`audit__…sql:13-64`); `int_estabelecimentos__enriquecidos` não lê seeds (os seeds alimentam `dim_porte`/`dim_situacao_cadastral` e o relationships de matriz/filial). | código |
| RBP-G03 | menor | `01-fundamentos.md:229` | "pastas viram esquema/nomes compostos". | Pastas só entram no FQN (config por caminho); o schema vem de `+schema`/`generate_schema_name`. | docs.getdbt.com/docs/build/custom-schemas |
| RBP-G04 | menor | `01-fundamentos.md:252-267`; `04-bibliotecas-e-tecnicas.md:192-197` | Fonte `rfb` com `meta.external_location` no nível da fonte, `{name}` e mês **fixo** `mes_referencia=2026-09`. | O `{name}` é um recurso válido do dbt-duckdb, mas **não** é o que o projeto faz: cada tabela tem `read_parquet('…/<entidade>/mes_referencia=*/*.parquet', hive_partitioning=false)` (`_rfb__sources.yml:20-22`). Um mês fixo quebraria a atualização mensal. P2. | código; README dbt-duckdb |
| RBP-G05 | menor | `01-fundamentos.md:315-324` | Trecho "de `_rfb__sources.yml`" com `cnpj_completo` + `dbt_utils.expression_is_true`. | A fonte não tem `cnpj_completo`, e o projeto não usa `expression_is_true`. Os testes de `cnpj_completo` (`unique`, `not_null`, `tamanho_exato`, `cnpj_dv_valido`) estão em `_rfb__staging.yml:181-195`. | `git grep expression_is_true` = 0 |
| RBP-G06 | **importante** | `01-fundamentos.md:328`; `02-fluxo-e-testes.md:441` | Unit tests verificam a lógica "sem precisar consultar o banco de dados real". | Por padrão, **cada unit test envia uma consulta ao data platform**, e os pais diretos precisam existir (ou ser criados com `--empty`). É justamente por isso que existe a P8. | docs.getdbt.com/docs/build/unit-tests ("each unit test sends a query to your data platform"; "direct parents … need to exist") |
| RBP-G07 | menor | `01-fundamentos.md:354`; `02-fluxo-e-testes.md:298` | 33 unit tests; 189 data tests. | 35 unit tests e 200 data tests (manifest de `d111d09`). | `dbt ls -s test_type:unit` = 35 |
| RBP-G08 | menor | `01-fundamentos.md:366-384` | `texto_ou_nulo` como `case … trim … end`; uso com `cnpj_basico`. | A macro é `nullif(trim(col), '')` (`texto_ou_nulo.sql:2`); a coluna é `cnpj_raiz` (`stg_rfb__estabelecimentos.sql:10`). P2. | código |
| RBP-G09 | menor | `01-fundamentos.md:390-405`, `660`; `04:300` | `packages.yml` com faixas de versão e `godatadriven/dbt_date` direto; "dbt_date: SIM". | `packages.yml` fixa `dbt_utils 1.4.1` e `dbt_expectations 0.10.10`; `dbt_date` é só dependência transitiva (`package-lock.yml`). Nenhum modelo usa `dbt_date`. | `transform/packages.yml` |
| RBP-G10 | menor | `01-fundamentos.md:414` | `dq_resumo_execucao` é `table`. | É `view`: `config(materialized='view')` no modelo sobrepõe o `+materialized: table` da pasta (`dq_resumo_execucao.sql:4`). A parte 2 (L292) está certa. | manifest |
| RBP-G11 | menor | `01-fundamentos.md:431` | Macro `garantir_tabela_historico_testes`. | A macro é `criar_historico_testes` (`registrar_resultados_testes.sql:6`; `dbt_project.yml:15`). | código |
| RBP-G12 | menor | `01-fundamentos.md:476-506` | Profile com `threads: "{{ env_var('DUCKDB_THREADS', 4) }}"` e sem `settings.threads`. | Desde o F3a: `threads: env_var('DBT_THREADS') \| as_number` e `settings.threads: env_var('DUCKDB_THREADS')` (`profiles.yml:9-13`). O próprio texto de L511-513 contradiz o snippet. P2. | código |
| RBP-G13 | menor | `01-fundamentos.md:636` | `dbt run --select source:rfb.*` = "modelos que leem diretamente fontes". | Esse critério seleciona as **fontes**: `dbt run` responde "Nothing to do". Para os modelos que leem a fonte: `source:rfb+1` (filhos diretos) ou `source:rfb+` (todo o downstream). | executado: `WARNING: Nothing to do` |
| RBP-G14 | **importante** | `01-fundamentos.md:638`, `801-803` | `dbt ls/build --select state:modified --state target/` "só o que mudou desde o último build". | A doc manda **não** usar o mesmo caminho em `--state` e `--target-path`: o dbt regrava o `manifest.json` antes de comparar. Executado: "The selection criterion 'state:modified' does not match any enabled nodes". Correto: copiar o manifest para `state/` (ou usar `--target-path` diferente / `--no-write-json`). | docs.getdbt.com/reference/node-selection/state-comparison-caveats |
| RBP-G15 | menor | `01-fundamentos.md:714-715` | Staging com joins "vira craveling"; a dbt Labs recomenda intermediate como `table`. | "craveling" não existe. A recomendação oficial para intermediate é **ephemeral** (ponto de partida) ou **view em schema próprio**. `table` é escolha do projeto (justificável pelo volume), não recomendação da dbt Labs. | best-practices/how-we-structure/3-intermediate |
| RBP-G16 | menor | `01-fundamentos.md:767`; `04:280` | `dbt clone` "exige warehouse com clone"; no DuckDB, "copiar os .parquet". | Sem clone zero-copy, o dbt cria uma **view ponteiro** (`select * from` o objeto do state). Executado no DuckDB: `dbt clone --state … -s dim_porte` → PASS. | docs.getdbt.com/reference/commands/clone |
| RBP-G17 | menor | `01-fundamentos.md:785` | `--store-failures` cria "tabelas `*_dbt_test__audit`". | Cria um **schema** `<schema>_dbt_test__audit`; cada tabela recebe o nome do teste. A parte 2 (L426) está certa. | docs.getdbt.com/reference/resource-configs/store_failures |
| RBP-G18 | menor | `01-fundamentos.md:795-796` | `make pipeline` = ingest → freshness → build → relatório; `make docs` = generate + serve. | `make pipeline` não está implementado (`exit 2`, T28); `make docs` só roda `dbt docs generate` (`Makefile:30-38`). | `Makefile` |
| RBP-G19 | menor | `01-fundamentos.md:848-851` | DuckDB aceita leitores read-only concorrentes; basta evitar clientes com "lock de gravação". | Um processo que abre o arquivo, **mesmo read-only**, impede outro processo de gravar ("Multiple processes can read … but no processes can write"). Um DBeaver/notebook aberto em read-only também derruba o `dbt run`. | duckdb.org/docs/current/connect/concurrency |
| RBP-G20 | **importante** | `01-fundamentos.md:853-856` | `dbt run` "não valida contratos ou regras de freshness"; `build` é que valida. | Contratos são checados **no `dbt run`** (preflight antes de materializar) e em qualquer comando que materializa. **Nem `run` nem `build` rodam freshness**: só `dbt source freshness`. | docs.getdbt.com/reference/resource-configs/contract; reference/commands/build |
| RBP-G21 | **importante** | `01-fundamentos.md:858-861`; `05-boas-praticas-e-usos.md:151-152` | Sem `temp_directory` o DuckDB não faz spill e o processo é morto por OOM; configure `temp_directory` no profile. | (a) O padrão de `temp_directory` é `<banco>.tmp`, ou seja, o spill já existe sem configuração. (b) No dbt-duckdb, `temp_directory` precisa ir em `settings:`; **no topo do profile ele é ignorado** (RBP-01). (c) `memory_limit` não limita o RSS total (P14: 26 GiB com limite de 16 GB), e nem todo operador faz spill. | duckdb.org/docs/current/configuration/overview; `credentials.py` do dbt-duckdb 1.11.0 (sem o campo); `current_setting('temp_directory')` = `…/warehouse.duckdb.tmp` |
| RBP-G22 | menor | `02-fluxo-e-testes.md:36-68, 82, 137, 157-160, 228, 280-284` | Contagens "reais" das fixtures (15 estabelecimentos, 14 empresas, `bh_empresas` 12, `dim_data` 9.753, resumo 29, concorrência 10, fornecedores 2, coortes 15, dinâmica 20, histórico 242). | Em `d111d09`: 16, 15, 13, **46.278** (o calendário começa em 1900 desde o F3a), 31, 11, 3, 16, 21; `dq_historico_testes` é cumulativo (251 nesta execução), então não cabe como contagem fixa. | consulta ao `warehouse.duckdb` do `make ci` |
| RBP-G23 | **importante** | `02-fluxo-e-testes.md:80`; `03-qualidade-antes-e-depois.md:59` | `Socios*` **e colunas de contato** são descartados na ingestão e "jamais entram no warehouse"; a ingestão bloqueia "colunas LGPD". | Só `Socios*` deixa de ser ingerido. O **raw guarda `email`, `ddd*`, `tel*`, `fax`** como publicado; quem os descarta é o **staging** (ADR-0008; `_rfb__sources.yml:141-156`). Sobre dados pessoais (LGPD), o guia precisa dizer onde o dado de fato está. | ADR-0008 |
| RBP-G24 | **importante** | `02-fluxo-e-testes.md:4, 93-135, 146, 267-278`; `05:62-89` | O "SQL compilado real" de `stg_rfb__estabelecimentos` seria "extraído diretamente"; `st_point(longitude, latitude)` no intermediário; haversine com raio 6371,0 e `abs`; `int_cnaes_secundarios__explodidos` com CTEs como "exemplo real". | São fabricados. O staging real usa `lpad_codigo` (que não trunca), `\|\|`, `list_transform`/`list_filter`, `data_rfb` = `try_strptime` sem lista de sentinelas, e outros nomes de coluna. Não há `st_point` (lat/long `double`). O haversine usa 6371,0088, `least(1, …)` e não usa `abs`. O intermediário é um `select distinct … unnest` sobre `int_estabelecimentos__enriquecidos`. P2 **reaberta**. | `target/compiled/…`; código |
| RBP-G25 | menor | `02-fluxo-e-testes.md:307` | `accepted_values` de situação `['1','2','3','4','8']`. | Raw: `["01","02","03","04","08"]`; staging: inteiros `[1,2,3,4,8]` com `quote: false`. | `_rfb__sources.yml:105`, `_rfb__staging.yml:203` |
| RBP-G26 | menor | `02-fluxo-e-testes.md:339-341` | `tamanho_exato` é macro em `transform/macros/`. | É um teste genérico em `transform/tests/generic/tamanho_exato.sql`. | código |
| RBP-G27 | menor | `02-fluxo-e-testes.md:412-420` | Exemplo `severity: warn` + `error_if: "> 10"` com o comentário "Quebra apenas se ultrapassar 10". | A nota logo abaixo (L422-423) está certa e contradiz o exemplo: com `severity: warn`, `error_if` é ignorado. O exemplo deveria usar `severity: error`. | docs.getdbt.com/reference/resource-configs/severity |
| RBP-G28 | menor | `03-qualidade-antes-e-depois.md:179` | "Saldo = aberturas − encerramentos", teste singular em `_analytics__models.yml`. | Não existe. `saldo` só tem `not_null` (`_analytics__models.yml:150-152`); `mart_dinamica_mercado` não tem unit test. | código |
| RBP-G29 | **importante** | `03-qualidade-antes-e-depois.md:190-194, 204-210` | Ordem de meses (P22) garantida por Makefile/`cli.py`; política de retenção em `cli.py`; Parquet "sem corrupção" validado; exposure como check `error`. | P22 e a retenção são do B8 (T28/T36) e **não existem**. A leitura do Parquet só ocorre no pytest das fixtures (não em dados reais). Exposure não é check. A matriz mistura o planejado com o implementado. Marcar como "planejado (B8)". | `git grep reten` = 0; `pendencias.md` P22 |
| RBP-G30 | menor | `03-qualidade-antes-e-depois.md:55-62` | `erros.py` L12, L59, L77, L86, L94. | As classes estão em L10, L57, L75, L84, L92. | `erros.py` |
| RBP-G31 | menor | `01:403`; `04:67, 86, 132, 299` | `dbt_utils` usado "extensivamente" com `expression_is_true`; `dbt_expectations`: SIM; `codegen` "útil na exploração". | `expression_is_true` e `dbt_expectations` **não são usados** (ver RBP-10). Não há registro de uso do `codegen`. O exemplo `generate_source(schema_name: raw)` nem se aplica a fontes `external_location`. | `git grep` |
| RBP-G32 | menor | `04:102, 303` | Teste de paridade "~3,4× mais veloz" que o audit-helper. | Os 3,4× (R2-12) comparam **hash da linha × 15 colunas**, não o audit-helper. | R2.md R2-12 |
| RBP-G33 | menor | `04:110` | Elementary: `edr monitor` para o relatório. | `edr monitor` envia **alertas**; o relatório HTML é `edr report`. | docs.elementary-data.com |
| RBP-G34 | menor | `04:236-247` | Exemplo incremental filtra `_ingerido_em` de `stg_rfb__estabelecimentos`. | O staging não expõe `_ingerido_em`, então o exemplo falha. Usar `_data_referencia` ou marcá-lo como genérico. | código |
| RBP-G35 | menor | `04:274` | `make ci` "em menos de 15 segundos". | Medido: 57 s (o README/AC dizem < 120 s). | medição |
| RBP-G36 | menor | `04:308-309` | CI Slim/`--defer`: "SIM — documentado e suportado". | Nada usa `state:`/`--defer` (não há manifest de produção nem comando). Num DuckDB local de arquivo único, defer para "produção" mal se aplica. | `git grep state:modified` = 0 |
| RBP-G37 | menor | `05:43` | Meta em inglês: `scope: original`. | O projeto usa `meta.escopo` (ADR-0006, guarda `test_escopo_meta.py`). | código |
| RBP-G38 | menor | `05:124-126` | `access: private` = referenciável "dentro da mesma pasta". | `private` = só dentro do mesmo **group**; `protected` (padrão) = mesmo projeto. | docs.getdbt.com/reference/resource-configs/access |
| RBP-G39 | menor | `05:240` | `dbt show --inline "select … limit 3"`. | Falha: `dbt show` acrescenta o próprio `limit`, e o DuckDB acusa "syntax error at or near limit". Tirar o `limit` do SQL e usar `--limit 3`. | executado |
| RBP-G40 | menor | `05:262-265` | `dbt run-operation macro_limpeza_artefatos`. | A macro não existe no projeto; marcar como hipotética. | código |
| RBP-G41 | **importante** | `05:270-277` | Reprocessar jan/2025 com `dbt build --vars '{"mes_referencia": "2025-01", …}'` "sem modificar código". | Os modelos `external` **sobrescrevem o gold corrente** com o mês antigo (P22, já confirmada na R3). Também muda `caso_municipio` para todo o gold de analytics. Avisar e indicar `external_root` temporário (`--vars` + `RAIZ_DADOS`/target separado), como a R3 propôs. | `pendencias.md` P22 |
| RBP-G42 | menor | `05:184, 189` | O DuckDB "baixa e compila" o `httpfs`; `caffeinate -i` dá "prioridade total" à CPU. | O DuckDB baixa um binário pré-compilado. O `caffeinate -i` só impede o sleep por ociosidade. | duckdb.org extensions; `man caffeinate` |
| RBP-G43 | menor | `05:301-303` | A guarda do catálogo é `git diff --exit-code docs/QUALIDADE_DADOS.md`. | É o pytest `tests/integration/test_catalogo_dq.py`, que regera o catálogo do manifest e compara. | código |

**O que está correto e foi conferido.** Espaço = união e vírgula = interseção, e `or`/`and` não são
operadores (executado: "criterion 'or' does not match"). `severity: warn` ignora `error_if`. `store_failures`
vai para `main_dbt_test__audit`. `is_incremental()` é falso no primeiro build e no `--full-refresh`.
Estratégias do dbt-duckdb (append, delete+insert, merge com DuckDB ≥ 1.4, microbatch com dbt ≥ 1.9).
`--empty`. `dbt ls --select +exposure:…` (189 nós). `dbt ls -s dim_municipio+` lista a exposure.
`test_type:unit`. `dbt show --select … --limit 5`. Contratos falham antes de gravar o Parquet (N08/N13).
`dbt-project-evaluator` suporta DuckDB. `dbt-checkpoint` v2.0.6 existe. Todos os links internos e as 57 URLs
externas respondem 200.

### Pendências do líder sobre o guia

| # | Situação | Evidência |
|---|---|---|
| P1 | **Resolvida.** `01:641-648` está correto e sem a ressalva de versão. | executado |
| P2 | **Reaberta.** Ainda há snippets que não batem com o código: G04, G05, G08, G09, G11, G12 e G24. | tabela acima |
| P8 | **Resolvida e correta.** Troquei o `given` de `test_stg_rfb__cnaes_lpad_e_texto_vazio` por `rows:` dict numa cópia: "Not able to get columns for unit test 'cnaes' from relation "warehouse"."rfb"."cnaes" because the relation doesn't exist". Ressalva: chamar `format: sql` de "solução oficial" é exagero; a doc o exige só para inputs ephemeral; aqui é contorno do dbt-duckdb. | experimento |
| P9 | **Resolvida em parte.** O guia (`05:178-189`) documenta a primeira execução, e `test_dbt_s3.py` pula sem rede. O **README** não diz nada sobre a primeira execução. | `README.md` |

---

## Parte 2 — Lacunas do projeto

| ID | Severidade | Arquivo:linha | Achado | Evidência | Correção sugerida | Etapa / tarefa de origem |
|---|---|---|---|---|---|---|
| RBP-01 | **importante** | `transform/profiles.yml:11, 19, 32` | **`temp_directory` nunca chega ao DuckDB.** O dbt-duckdb 1.11 não tem o campo `temp_directory` no topo do profile (os campos são `path`, `settings`, `extensions`, `secrets`, `external_root`…) e o ignora em silêncio. Assim, o spill vai para `<path>.tmp`, e não para `RAIZ_DADOS/_tmp` ou `RAIZ_DADOS_LOCAL/_tmp` como dizem o ADR-0007, o `ARCHITECTURE.md:338` e o guia. Hoje fica no mesmo disco por coincidência; com `CAMINHO_DUCKDB` apontando para outro volume, o spill vai junto. | `dbt show --inline "select current_setting('temp_directory')"` (target ci) → `…/.tmp/ci/dados/warehouse.duckdb.tmp`; `credentials.py` sem o campo. | Mover para `settings: {temp_directory: …}` nos três targets. Estender `tests/integration/test_profiles_threads.py` com `current_setting('temp_directory')` (mesmo padrão do R3-05). | B1/T3 (profile), F3a |
| RBP-02 | **importante** | `transform/macros/staging/data_rfb.sql:2`, `decimal_rfb.sql:4`; `_rfb__staging.yml` | **Perda de tipagem silenciosa no staging.** `try_strptime`/`try_cast` transformam lixo em NULL (correto por linha), mas **nenhum teste mede a proporção** de valores não vazios no raw que viram NULL. Uma deriva de formato do extrato passa verde e zera as análises. Falta o "antes" do formato do raw e o "depois" da conversão. | **D1** (datas `AAAA-MM-DD` no raw): `dbt build` PASS=267 ERROR=0; `stg` com 0/16 datas, `bh_empresas.idade_atual` 0/13, `mart_dinamica_mercado` 0 linhas, coortes vazias. A paridade passa (os dois lados ficam NULL). **D3** (`capital_soc` `1.1000,50`): PASS, 0/15 capitais e soma 0 no resumo. | Teste genérico `conversao_sem_perda(coluna_raw, coluna_tipada)` ou singulares por entidade: % de raw não vazio → NULL tipado, com `warn_if: ">0"` e `error_if` em limiar (ex.: > 1% das linhas) para datas, capital, situação e porte. Somar "não vazio" (`dbt_utils`/`dbt_expectations` row count > 0) em `mart_dinamica_mercado`, `mart_sobrevivencia_coorte` e na fração de `dat_inicio_atividade` não nula. | B4/T14 (staging), DQ-01 |
| RBP-03 | **importante** | `Makefile:23-33`; `.pre-commit-config.yaml` | **O `make ci` não roda os testes unitários Python (184) nem o lint**, e não há CI remoto (`.github/` não existe). O pre-commit roda ruff e sqlfluff só em quem instalou o hook. Os 184 testes de EL, configuração e relatório só rodam se alguém lembrar. | **N01** (`_ingerido_em` fixo em 2000-01-01) passa no `make ci` e só é pego por `tests/unit/test_conversao.py::test_colunas_tecnicas_e_cnae_texto`. Nas R1/R2, várias mutações de EL também só morreram no unit. | `ci`: acrescentar `uv run pytest -q tests/unit` (2 s) e `$(MAKE) lint` (9 s), ou criar um alvo `verificar` = lint + unit + ci. Opcional: workflow do GitHub Actions com cache de `.venv`, `dbt_packages` e `~/.duckdb/extensions` (ver "adições"). | B1/T1–T3 (Makefile) |
| RBP-04 | **importante** | `_rfb__sources.yml:9-12`; spec STG AC 8 (`spec.md:143`) | **O freshness nunca é executado nem testado.** Nenhum alvo do Makefile, nem o CLI nem o pytest roda `dbt source freshness` (o `make pipeline` é do B8). Além disso, `loaded_at_field: _ingerido_em` mede **quando ingerimos**, não a **data do extrato**: reingerir um mês antigo hoje dá "fresco". Pelo ADR-0004, a data do dado é `_data_referencia`. | **N01** sobrevive ao `make ci`. `dbt source freshness --target ci` funciona (9 PASS), mas só se rodado à mão. | Teste de integração que roda `dbt source freshness` sobre as fixtures (um caso fresco, e um com `_ingerido_em`/`_data_referencia` antiga esperando WARN/ERROR). Avaliar `loaded_at_field: _data_referencia` (ou um segundo critério) e registrar a decisão. Incluir no `make pipeline` (T28) **antes** do build. | B4/T12 (fontes); T28 |
| RBP-05 | menor | `transform/models/marts/analytics/_analytics__models.yml` | **Os marts de analytics (4) não têm contrato**, embora sejam gold consumido pelo BI e o guia (`05:113-114`) recomende contrato em todos os marts. Uma mudança de tipo passa pelo dbt. | **N14** (`ano::varchar` em `mart_dinamica_mercado`): nenhum teste dbt falha; só o pytest das fixtures (`test_dinamica_fundao_…`). | `contract: {enforced: true}` + `data_type` nas 46 colunas dos 4 marts. | B7/T23–T25 |
| RBP-06 | menor | `stg_bd__pib.sql`, `stg_bd__populacao.sql`; `_bd__staging.yml:92-125` | **`stg_bd__pib` e `stg_bd__populacao` não têm nenhum teste**: só a unicidade `(id_municipio, ano)` na fonte, sem unit test. `pib` só alimenta `dim_municipio`. | **N10** (`va::double as pib`) sobrevive a tudo. | Invariante barata: `abs(pib - (va + impostos_liquidos)) <= 1` (identidade do IBGE) em warn; `populacao > 0`; `not_null` em `id_municipio`/`ano`. | B5/T12 (staging BD) |
| RBP-07 | menor | `transform/macros/staging/filtro_mes_referencia.sql:4-6` | A validação de `mes_referencia` (formato `AAAA-MM`) não tem teste. | **N09** (trocar `raise_compiler_error` por `log`) sobrevive. | pytest: `dbt compile --vars '{mes_referencia: 2026-9}'` deve falhar com a mensagem. | B4/T14 |
| RBP-08 | menor | `src/rfb_pipeline/relatorio.py:99-118` | A seção de qualidade do relatório só é testada em `renderizar` (com dados falsos); o SQL de `ler_qualidade` não é afirmado. Além disso, `except duckdb.Error: return None` transforma qualquer erro (coluna renomeada, view ausente) em "histórico indisponível", em silêncio. | **N17** (`status not in ('pass','warn')`, que esconde os avisos do relatório) sobrevive ao unit e à integração. | Teste de integração que gera o relatório após o `make ci` e afirma que os 4 WARN conhecidos aparecem. Capturar só "tabela inexistente" e propagar os demais erros. | B7/T27 |
| RBP-09 | menor | `_core__models.yml:4-17, 302-319` | Cobertura de documentação: **100% dos modelos e das colunas declaradas**, mas só **87,3% das colunas reais** (262/300). Os intermediários documentam 2 de 21 colunas cada (`int_municipios__conformados`, `int_estabelecimentos__enriquecidos`), inclusive as flags `tem_*`, que o guia chama de diagnóstico. Não há guarda de cobertura. | `catalog.json` × `manifest.json` (tabela de métricas). | Documentar as 38 colunas (as `tem_*` primeiro). Guarda pytest: toda coluna do `catalog` de `marts/` e `intermediate/` tem `description` (ou adotar o `dbt-project-evaluator`, ver "adições"). | B6/T17–T18 |
| RBP-10 | menor | `transform/packages.yml:4-5` | `dbt_expectations` (e com ele o `dbt_date`) é instalado e **não é usado** por nenhum teste. Custa o tempo do `dbt deps` e a superfície de dependência, e o guia o dá como usado. | `git grep dbt_expectations` só acha `packages.yml`/lock. | Usar (ex.: `expect_table_row_count_to_be_between` para o RBP-02) ou remover. | B1/T3 |
| RBP-11 | menor | `transform/dbt_project.yml:5`; `pyproject.toml:8-13` | `require-dbt-version: [">=1.8.0", "<2.0.0"]`, mas o projeto usa `arguments:` em testes genéricos, disponível **só a partir do 1.10.5**. Com dbt < 1.10.5 a guarda de versão aceita o ambiente, mas o `arguments:` não é reconhecido e o erro aparece longe da causa. `dbt-core`/`dbt-duckdb`/`duckdb` estão sem faixa no `pyproject` (o `uv.lock` fixa, mas um `uv lock --upgrade` pode levar ao dbt 2.x/Fusion). | doc `data-tests` ("available in v1.10.5 and higher") | `require-dbt-version: [">=1.10.5", "<2.0.0"]`; `dbt-core>=1.10.5,<2`, `dbt-duckdb>=1.10,<2`. | B1/T3 |
| RBP-12 | menor | `registrar_resultados_testes.sql:6-14`; `01:217`, `04:202` | O histórico de DQ (`main.dq_historico_testes`) vive **só dentro do `warehouse.duckdb`**, que o guia chama de "catálogo descartável" e que no modo S3 é local (`RAIZ_DADOS_LOCAL`). Apagar ou recriar o banco perde todo o histórico; ele não vai para o gold nem é sincronizado. | leitura | Exportar o histórico para Parquet em `gold/dq_historico_testes/` (append por `invocation_id`) no `on-run-end`, ou documentar que o `.duckdb` de dev/prod **não** é descartável. | B7/T26 |
| RBP-13 | menor | `_core__models.yml`, `_analytics__models.yml` | **Regras de negócio protegidas só pelo pytest sobre fixtures.** As mutações abaixo passam no `dbt build` e só morrem por valores esperados no pytest de integração. Em dados reais (onde só o `dbt build` roda) não há rede: N11 (densidade ×10), N14 (tipo), N19 (`dat_situacao` = início de atividade) e N20 (MEI recebe a flag do Simples). | tabela de mutações | Invariantes de dados baratas: `dat_situacao >= dat_inicio_atividade` (warn, com store_failures) no staging; `opcao_mei ⇒ opcao_simples` (MEI exige Simples) na fato; `ativos_por_10k_hab = round(ativos*1e4/populacao, 2)` no mart de concorrência; unit tests para `mart_concorrencia_municipio` e `mart_dinamica_mercado` (hoje 0). | B6/B7 |
| RBP-14 | sugestão | `Makefile:23-33` | A sequência do CI (mês antigo sem testes → teste do resumo do mês antigo → build do corrente) é uma seleção complexa repetida por flags. O guia ensina YAML selectors e o projeto não tem `selectors.yml`. | leitura | `transform/selectors.yml` com `ci_mes_antigo` e `ci_resumo_mes_antigo` (e, no B8, `pipeline`), usados via `--selector`. Isso documenta a intenção e evita divergência entre `make ci` e `rfb atualizar`. | B8 |
| RBP-15 | sugestão | `transform/dbt_project.yml` | `groups`/`access` não são usados: todos os 31 modelos são `protected`. | manifest | Barato: um `group` por domínio (ex.: `rfb`) com staging/intermediate `private` e marts `public`. O `ref` errado (um mart lendo staging de outra camada sem querer) passaria a falhar no parse. Valor moderado num projeto único; adotar só se houver um segundo projeto/consumidor dbt. | — |

Contagem: **0 bloqueantes, 4 importantes, 9 menores, 2 sugestões.**

---

## Antes × depois por etapa (projeto real)

✅ = há check automatizado que roda no `make ci`/`dbt build`; ⚠️ = parcial (ver nota); ❌ = ausente.

| Etapa | Antes | Depois | Nota |
|---|---|---|---|
| EL Python (ingestão) | ✅ mês existe/completo, allowlist de host, zip-slip, `Socios*` fora, credenciais S3 | ✅ tamanho, sha256 no manifesto, taxa de rejeito, entidade não vazia, publicação atômica, no-op | N02–N05 mortas; N01 só pelo unit, fora do `make ci` (RBP-03) |
| Fontes raw | ⚠️ unicidade por mês, chaves não nulas, `porte`/`situacao` em domínio, `_data_referencia` não nula, FKs por mês (singular) | ❌ freshness | Sem conformidade de formato de data/decimal (RBP-02); freshness nunca roda (RBP-04); BD só com unicidade |
| Staging | ✅ fonte testada antes (D2: ERROR + SKIP=122) | ⚠️ `unique`/`not_null`/`tamanho_exato`, DV (warn), datas não futuras e ≥ 1900 (warn), sem contatos, 15 unit tests | Sem taxa de perda de tipagem (D1/D3 sobrevivem); `stg_bd__pib`/`populacao` sem nada (N10) |
| Intermediate | ✅ (DAG) | ✅ unicidade, relationships matriz/filial, unit tests de flags, explosão e ano | Colunas pouco documentadas (RBP-09) |
| Marts original | ✅ contrato | ✅ paridade hash `EXCEPT ALL`, reconciliação agg×bh, descartes (warn), `accepted_range` warn/error, 5 unit tests | Mais forte do projeto |
| Core / estrela | ✅ contrato, calendário completo | ✅ relationships de todas as FKs, reconciliação fato×staging e resumo×fato, unicidade composta, membros −1/−2 | N08/N13 mortas por contrato |
| Analytics | ⚠️ (DAG) | ⚠️ `not_null`, relationships, faixa de densidade, invariantes de sobrevivência, `via` | Sem contrato (RBP-05); concorrência e dinâmica sem unit test; N11/N14 só pelo pytest (RBP-13) |
| Observabilidade | ✅ `on-run-start` cria a tabela | ✅ uma linha por teste, acúmulo entre execuções, resumo | N15/N16/N18 mortas pelo pytest; histórico só no `.duckdb` (RBP-12) |
| Gold / BI | ⚠️ `mkdir gold` só no `make ci` (P11) | ⚠️ exposure (documental), leitura do Parquet no pytest das fixtures | Nada em dados reais; P22 aberta |
| Atualização mensal | ❌ (`rfb atualizar`/`make pipeline` = B8) | ❌ | P11, P22, ordem de meses, freshness, retenção: B8 |

## Métricas de cobertura (`d111d09`, target ci)

| Métrica | Valor |
|---|---|
| Modelos com `description` | **31/31 (100%)** |
| Colunas declaradas com `description` | 262/262 (100%) |
| Colunas reais (catalog) com `description` | **262/300 (87,3%)**. Faltam 19 em `int_municipios__conformados` e 19 em `int_estabelecimentos__enriquecidos`; `audit__…` (ephemeral, 15 colunas) fica fora do catalog |
| Fontes com `description` (tabela/colunas) | 14/14 / todas as colunas declaradas |
| Macros com `description` | 15/15 |
| Seeds com `description` | 3/4 (`excecoes_conhecidas_municipio` sem descrição nem colunas) |
| Contratos | **11/31 modelos**: 2/2 `original` e 9/9 `core`; 0/4 `analytics`; staging, intermediate e observability sem contrato (aceitável) |
| Colunas com `data_type` | 100% nos 11 contratados; 0 nos demais |
| Data tests | 200 |
| Unit tests | 35. Por modelo: `bh_empresas` 4, `stg_rfb__estabelecimentos` 4, `stg_rfb__municipios` 3; zero em `mart_concorrencia_municipio`, `mart_dinamica_mercado`, `dim_porte`, `dim_situacao_cadastral`, `stg_bd__cnaes/pib/populacao`, `stg_rfb__motivos/naturezas`, `dq_resumo_execucao` |
| Data tests por modelo | mín. 0 (`stg_bd__pib`, `stg_bd__populacao`); máx. 19 (`stg_rfb__estabelecimentos`, `fct_estabelecimentos`); mediana 5 |
| Freshness | 9/9 fontes RFB configuradas; 0 execuções no CI |
| Groups / access / versions / selectors | 0 / todos `protected` / 0 / 0 |
| pytest | 184 unit + 80 integração (o `make ci` roda só a integração) |

## Mutações (23: 20 de código + 3 de dados)

Código: harness com `make ci` completo por mutação (+ `pytest tests/unit` para Python/Makefile), com
reversão por `git checkout` e build limpo final (P12). Dados: `dbt build --target ci` numa cópia isolada, com
o Parquet raw de 2026-09 alterado.

| # | Área | Mutação | Resultado | Quem pegou |
|---|---|---|---|---|
| N01 | EL | `_ingerido_em` fixo em 2000-01-01 | **sobrevive ao `make ci`** | só `tests/unit/test_conversao.py::test_colunas_tecnicas_e_cnae_texto` (fora do `make ci`); freshness não roda (RBP-03/04) |
| N02 | EL | RFB lido como UTF-8 (não latin-1) | morta | taxa de rejeito (6,7% > 0,01%) na ingestão |
| N03 | EL | nunca pula a reconversão (= R1 M4) | morta | `test_segunda_execucao_nao_reescreve…` + unit (R1-10 confirmado) |
| N04 | EL | manifesto com `sha256=""` (= R1 M20) | morta | `test_manifesto_do_cli_tem_o_sha256_real_dos_zips` (R1 confirmado) |
| N05 | EL | `_data_referencia` sempre NULL (R2-03) | morta | `fct_resumo_mensal_relacionamentos_mes`; no build completo, o `not_null` da fonte |
| N06 | macro | `texto_ou_nulo` sem `trim` | morta | unit `empresas_tipagem`, `estabelecimentos_cnaes_secundarios` |
| N07 | macro | `lpad_codigo` trunca código maior | morta | unit `cnaes_lpad_nao_trunca_codigo_maior` |
| N08 | macro | `decimal_rfb` → `decimal(18,0)` | morta | **contrato** de `fct_estabelecimentos` |
| N09 | macro | var `mes_referencia` inválida não aborta | **sobrevive** | — (RBP-07) |
| N10 | staging BD | `pib` lido de `va` | **sobrevive** | — (RBP-06) |
| N11 | analytics | densidade por 1k, não 10k | morta só pelo pytest | `test_concorrencia_fundao_tintas_…_0_5_por_10k` (RBP-13) |
| N12 | staging BD | longitude = latitude | morta | unit `stg_bd__municipios_parse_centroide` |
| N13 | contrato | `qtd_estabelecimentos::integer` no resumo | morta | **contrato** de `fct_resumo_mensal` |
| N14 | sem contrato | `ano::varchar` em `mart_dinamica_mercado` | morta só pelo pytest | `test_dinamica_fundao_…` (RBP-05) |
| N15 | hook | `create or replace` no histórico | morta | `test_duas_execucoes_acumulam…` |
| N16 | hook | unit tests fora do histórico | morta | `test_build_completo_registra_uma_linha_por_teste` |
| N17 | relatório | avisos somem da seção de qualidade | **sobrevive** | — (RBP-08) |
| N18 | Makefile | `make ci` sem unit tests dbt | morta | `test_build_completo_registra_uma_linha_por_teste` (conta pelo manifest) |
| N19 | staging | `dat_situacao` := início de atividade | morta só pelo pytest | `test_sobrevivencia_…`, `test_dinamica_…`, `test_fato_m_…` (RBP-13) |
| N20 | intermediate | `opcao_mei` := flag do Simples | morta só pelo pytest | `test_fato_a_e_c_sao_mei` (RBP-13) |
| D1 | dados | datas do raw em `AAAA-MM-DD` | **sobrevive** (PASS=267, ERROR=0) | — todas as datas, idades, dinâmica e coortes viram NULL ou vazio (RBP-02) |
| D2 | dados | `porte='9'` em empresas | morta | `source_accepted_values_rfb_empresas_porte…` (ERROR, SKIP=122 a jusante) |
| D3 | dados | `capital_soc` com separador de milhar | **sobrevive** (PASS=267) | — 0/15 capitais, soma 0 (RBP-02) |

Total: **18 mortas, 5 sobreviventes** (N09, N10, N17, D1, D3). Além disso, N01 passa no `make ci`, e 6 mortas
(N11, N14, N15, N16, N19, N20) dependem só de valores esperados no pytest das fixtures. Para N15/N16/N18
(infraestrutura) isso basta; para N11/N14/N19/N20 (regra de negócio), não há rede em dados reais (RBP-13).

## Sugestões "adição" (ferramentas que o projeto não usa por escolha — não são defeitos)

| Adição | Custo | Benefício | Recomendação |
|---|---|---|---|
| **CI remoto** (GitHub Actions: `make lint` + `pytest tests/unit` + `make ci`, com cache) | baixo (1 workflow, ~2 min por PR) | Garante que o RBP-03 não volte; executa o que hoje depende de disciplina local | **Adotar** quando houver remoto no GitHub |
| **dbt-project-evaluator** (suporta DuckDB) | baixo-médio: pacote + ~30 modelos/testes extras no build; exige desligar regras que colidem com ADR-0014 (prefixos `bh_`/`agg_`, `mart_`) via seeds de exceção | Cobre doc, testes por modelo, fan-out, staging com join, `ref` direto à fonte etc. Acharia o RBP-09 sozinho | **Adotar em modo relatório** (`dbt build -s package:dbt_project_evaluator`, `severity: warn`), fora do `make ci` padrão |
| **dbt-checkpoint** | baixo (hooks de pre-commit) | `check-model-has-description`, `check-column-desc-are-same`, `check-model-has-tests` antes do commit | Opcional: as guardas pytest cobrem nomes e escopo, mas não doc/teste por modelo. Se adotar, só esses 3 hooks |
| **Elementary** | médio-alto: pacote com modelos incrementais + CLI `edr`; o suporte a DuckDB existe, mas é menos maduro (correções recentes para Fusion) | Anomalias de volume e frescor e relatório HTML. Resolveria parte do RBP-02 (volume) e do RBP-12 (histórico fora do `.duckdb`) | **Não agora**: o histórico próprio + RBP-02/12 dão 80% do valor com 10% do custo. Reavaliar com execução mensal em produção |
| **audit_helper** | baixo | `compare_relation_columns`/`compare_all_columns` para investigar *qual* coluna diverge quando a paridade falha | **Opcional, como ferramenta de diagnóstico** (`dbt show`/analysis), sem substituir o teste hash |
| **Snapshots (SCD2)** | médio (tabela cresce com cada mês × 64 M) | Histórico de mudanças por CNPJ (situação, porte) | **Não**: o produto não pergunta isso, e a fato por mês + `fct_resumo_mensal` particionado já dão a série. Reavaliar se surgir uma pergunta de transição de situação |
| **codegen** | nulo | Scaffold de YAML | Irrelevante: as fontes são `external_location`, e o `generate_source` não as introspecta |
| **`dbt_expectations`** (já instalado) | nulo | Testes de volume e distribuição para o RBP-02 | **Usar** (ou remover, RBP-10) |

## Observações sobre qualidade (sem achado)

- **Credenciais:** `.env` no `.gitignore`; profile `s3` sem padrão para as chaves (o dbt falha nomeando a
  variável); `.env.example` presente. **Logs:** `transform/logs/` ignorado; o EL imprime por entidade.
  **Idempotência:** no-op por hash (N03 morta), publicação atômica, `overwrite_or_ignore` por partição.
- **Desempenho:** `DBT_THREADS` × `DUCKDB_THREADS` separados e testados (R3-05); `memory_limit` chega
  (`1.8 GiB` no ci); `hive_partitioning=false` explícito nas fontes; staging em view e intermediate em
  table, o que é coerente com 64 M linhas. Só o `temp_directory` falha (RBP-01).
- **Nomes (ADR-0014)** e escopo (ADR-0006) têm guardas próprias que passam; `sqlfluff` 4.3 aplica as
  exclusões legadas `L0xx` (verificado: LT05/ST06/CV04 fora do rulepack).

## Reprodução

```bash
make setup && caffeinate -i make ci && make lint && uv run pytest -q tests/unit
# temp_directory (RBP-01)
cd transform && RAIZ_DADOS=$PWD/../.tmp/ci/dados DBT_PROFILES_DIR=$PWD uv run dbt show --target ci \
  --inline "select current_setting('temp_directory')"
# métricas: dbt docs generate --target ci --target-path <tmp> e comparar catalog × manifest
# mutações: scratchpad/mutar.py (N01–N20); dados: alterar o Parquet raw de 2026-09 numa cópia e `dbt build`
```
