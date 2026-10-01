# Port RFB/CNPJ para dbt + DuckDB — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

Child workers also follow the `traycer-implement` skill (when to ask the lead, when to decide alone, what to report).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Spec**: `.specs/features/rfb-dbt-port/spec.md`
**Design**: `ARCHITECTURE.md` (design completo) + `docs/adr/` — este feature não tem `design.md` separado; a arquitetura do projeto é o design.
**Status**: Approved (líder, autonomia delegada pelo usuário)

Legenda de classificação: complexidade **P** (pequena) / **M** (média) / **G** (grande); criticidade **C** (crítica) / **NC** (não crítica).
Roteamento (docs/PLANO.md): C → Opus esforço médio · G/NC → Sonnet médio · M/NC → **Sonnet médio** (decisão do usuário em 2026-09-28, AD-014; antes DeepSeek v4 flash alto) · P/NC → DeepSeek v4 flash baixo.
Críticas ou grandes: T8, T14, T15, T28 (= 4, limite do guia). T36 (atualização mensal) é M/NC mas roda em Opus por ser E2E (regra do guia).
Melhorias pedidas pelo usuário em 2026-09-28 (ADR-0012/0013): T32–T36 e ajustes BI em T17–T19.
Enriquecimento com bases externas da Base dos Dados (pedido do usuário em 2026-10-01, ADR-0015): T38–T41, marcados com o incremento `enriquecimento_bd`.

---

## Test Coverage Matrix

> Generated from project guidelines and spec. Guidelines found: `ARCHITECTURE.md` §6, `docs/adr/0009-estrategia-testes.md`, `docs/adr/0010-fixtures-sinteticas.md` (repo greenfield — strong defaults applied).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Python EL (`src/rfb_pipeline/*`) | unit | Todos os ramos; 1:1 com os ACs de ingestão; todo edge case listado; rede sempre mockada (`httpx.MockTransport`), S3 via moto | `tests/unit/test_*.py` | `uv run pytest -q tests/unit` |
| CLI + fluxo fixtures→dbt→gold | integration | Happy path + números do cenário conhecido da spec + caminhos de erro (limiar de rejeito, mês inexistente) | `tests/integration/test_*.py` | `make ci` |
| dbt sources/staging/marts | dbt data tests + dbt unit tests | Todo AC de modelo com teste dbt; regras de negócio com `unit_tests` given/expect; contratos nos marts original/core | `transform/models/**/_*.yml`, `transform/tests/**` | `make ci` (executa `dbt build --target ci`) |
| Fixtures (`scripts/gerar_fixtures.py`) | unit | Cada linha/quirk do cenário presente nos arquivos gerados; saída determinística | `tests/unit/test_gerar_fixtures.py` | `uv run pytest -q tests/unit` |
| Config/tooling (pyproject, Makefile, profiles, lint) | none | build gate only | - | build gate |
| Documentação | none | revisão independente (R5) | `docs/**` | - |

## Gate Check Commands

> Generated from design — commands are created by T1/T2/T3 and completed by T10.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Tarefas só com testes unitários Python | `uv run pytest -q tests/unit` |
| Full | Tarefas dbt ou de integração (a partir de T10) | `make ci` |
| Build | Fim de lote / tarefas de config | `make lint && uv run pytest -q tests/unit` (antes de T10) · `make lint && make ci` (a partir de T10) |

---

## Execution Plan

Fases executam em ordem; tarefas dentro da fase em ordem. Lotes (B*) = unidade de execução de um agente.

### Phase 1: Fundação — lote B1 (P/NC)

```
T1 → T2 → T3
```

### Phase 2: Fixtures e clientes de download — lote B2 (M/NC)

```
T1 → T4 → T5 → T6 → T7
```

### Phase 3: Conversão CSV→Parquet — lote B3 (C)

```
T7 → T8
```

### Phase 4: Orquestração da ingestão, storage, fontes e staging de domínios — lote B4 (M/NC)

```
T8 → T9 → T10 → T11
T10 → T12 → T13
```

### Phase 5: Staging principal e modelo original — lote B5 (C)

```
T13 → T14 → T15
```

### Phase 5b: Padronização de nomes (ADR-0014) — lote RN (M/NC)

```
T15 → T37
```

### Phase 6: Segundo mês nas fixtures, agregado original e star schema para BI — lote B6 (M/NC)

```
T37 → T32 → T16
T16 → T17 → T19
T16 → T18 → T19
T16 → T33 → T19
T19 → T20
```

### Phase 7: Análises, DQ e estudo de caso — lote B7 (M/NC)

```
T20 → T21
T20 → T22
T20 → T23
T20 → T24 → T27
T20 → T25 → T26
```

### Phase 7b: Série mensal e Power BI — lote B7b (M/NC)

```
T20 → T34 → T35
```

### Phase 7c: Enriquecimento com novas bases da Base dos Dados (ADR-0015) — lote B10 (M/NC)

```
T35 → T38 → T39 → T40 → T41
```

### Phase 7d: Publicação no MotherDuck e acesso pelo Power BI (ADR-0016) — lote B11 (M/NC)

```
T41 → T42 → T43
```

### Phase 8: Ponta a ponta com dados reais e atualização mensal — lote B8 (C, E2E)

```
T43 → T28
T41 → T28
T27 → T28 → T36
T34 → T36
```

### Phase 9: Guia dbt e documentação — lote B9 (M/NC; T29 roda em paralelo desde a Fase 2)

```
T29
T30 → T31
```

---

## Task Breakdown

### T1: Ambiente Python e Makefile

**What**: `pyproject.toml` (Python 3.12, pacote `rfb_pipeline` em `src/`, CLI `rfb`, deps: dbt-core, dbt-duckdb, duckdb, httpx, boto3; dev: pytest, moto[server], ruff, sqlfluff, sqlfluff-templater-dbt, pre-commit), `uv.lock`, `Makefile` (alvos `setup fixtures ingest ci pipeline docs lint sync report clean` — os que dependem de código futuro podem imprimir "não implementado" e sair ≠0), `.gitignore` (`data/`, `.venv/`, `transform/target/`, `transform/dbt_packages/`, `transform/logs/`, `.env`, `tests/fixtures/generated/`), `.env.example`.
**Where**: `pyproject.toml`
**Depends on**: None
**Reuses**: ARCHITECTURE.md §2, §3, §7
**Requirement**: OPS-01
**Classificação**: P/NC

**Done when**:
- [x] `uv sync` resolve e instala; `uv run rfb --help` imprime ajuda (stub em `src/rfb_pipeline/cli.py`)
- [x] `uv run python -c "import duckdb, dbt"` ok; versões resolvidas registradas no relatório
- [x] Gate build passa (pytest sem testes coletados tratado como ok via `tests/unit/test_importacao.py` trivial)

**Tests**: none
**Gate**: build
**Commit**: `chore(setup): python env, makefile and project scaffolding`

---

### T2: Esqueleto do projeto dbt

**What**: `transform/dbt_project.yml` (nome `rfb`, pastas conforme ARCHITECTURE §3, materializações por pasta §5.1, vars §5.2, `+meta.escopo` default ausente), `transform/profiles.yml` (targets `ci`, `dev`, `s3`; path do `.duckdb` e `RAIZ_DADOS` via `env_var`; `threads`, `memory_limit`, `temp_directory` configuráveis por env), `transform/packages.yml` (dbt_utils, metaplane/dbt_expectations), pastas vazias com `.gitkeep`.
**Where**: `transform/dbt_project.yml`
**Depends on**: T1
**Reuses**: ARCHITECTURE.md §5
**Requirement**: OPS-01
**Classificação**: P/NC

**Done when**:
- [x] `cd transform && uv run dbt deps && uv run dbt parse --target ci` sem erro (com `RAIZ_DADOS` apontando para diretório temporário)
- [x] `uv run dbt debug --target ci` ok
- [x] Gate build passa

**Tests**: none
**Gate**: build
**Commit**: `chore(dbt): dbt project skeleton, profiles and packages`

---

### T3: Lint e pre-commit

**What**: `.sqlfluff` (dialeto duckdb, templater jinja com vars/macros dbt stubados ou templater dbt), config ruff em `pyproject.toml`, `.pre-commit-config.yaml` (ruff, sqlfluff lint, end-of-file, check-yaml), alvo `make lint`.
**Where**: `.sqlfluff`
**Depends on**: T2
**Reuses**: -
**Requirement**: OPS-01
**Classificação**: P/NC

**Done when**:
- [x] `make lint` roda e passa no repositório atual
- [x] Gate build passa

**Tests**: none
**Gate**: build
**Commit**: `chore(lint): ruff, sqlfluff and pre-commit`

---

### T4: Gerador de fixtures sintéticas

**What**: `scripts/gerar_fixtures.py` gera deterministicamente em `tests/fixtures/generated/` (ou dir passado) os zips RFB do mês `2026-09` (`Empresas0.zip`, `Estabelecimentos0.zip`, `Simples.zip`, `Cnaes.zip`, `Municipios.zip`, `Naturezas.zip`, `Motivos.zip`, `Paises.zip`, `Qualificacoes.zip`, cada um com um arquivo interno `F.K03200$Z.D60912.<TIPO>CSV`, latin-1, `;`, todos os campos entre aspas) e os csv.gz BD (`municipio`, `cnae_2`, `populacao`, `pib`) exatamente conforme o "Cenário de fixtures" da spec, incluindo: `\"` na razão social de K, nome_fantasia multilinha em O, datas `00000000`, porte vazio em E, CNAE `0111301`, DV inválido só em L (calcular DV correto para os demais), registro multilinha no `cnae_2`.
**Where**: `scripts/gerar_fixtures.py`
**Depends on**: T1
**Reuses**: spec — seção "Cenário de fixtures"; `docs/referencia-original/1_Coleta_e_Carga_de_Dados.md` (quirks)
**Requirement**: ING-03
**Classificação**: M/NC

**Done when**:
- [x] `make fixtures` gera os arquivos; duas execuções produzem bytes idênticos
- [x] `tests/unit/test_gerar_fixtures.py` verifica: encoding latin-1 (bytes de `Ã`), presença de `\"` em K, quebra de linha dentro de aspas em O, 15 estabelecimentos/14 empresas, DV válido em todos exceto L
- [x] Gate quick passa

**Tests**: unit
**Gate**: quick
**Commit**: `test(fixtures): deterministic synthetic RFB/BD fixture generator`

---

### T5: Config e contrato de schemas

**What**: `src/rfb_pipeline/configuracao.py` (RAIZ_DADOS, URLs/token WebDAV, allowlist de hosts, limiar de rejeito, timeouts, lendo env/`.env`) e `src/rfb_pipeline/esquemas.py` (para cada entidade RFB: padrão do zip, tipo interno, lista ordenada de colunas conforme ARCHITECTURE §4.2; tabelas BD com dataset/tabela; `Socios` explicitamente excluído).
**Where**: `src/rfb_pipeline/esquemas.py`
**Depends on**: T4
**Reuses**: ARCHITECTURE §4.1–4.2
**Requirement**: ING-02
**Classificação**: M/NC

**Done when**:
- [x] Testes: 30 colunas em estabelecimentos, 7 em empresas, 7 em simples, 2 nos domínios; nenhuma entidade casa `Socios*`; config lê overrides do ambiente
- [x] Gate quick passa

**Tests**: unit
**Gate**: quick
**Commit**: `feat(ingest): configuration and raw schema contract`

---

### T6: Cliente WebDAV da RFB

**What**: `src/rfb_pipeline/cliente_rfb.py`: `listar_meses()`, `mes_mais_recente()`, `listar_arquivos(mes)` (nome, tamanho) via `PROPFIND Depth:1`; `baixar(arquivo, destino)` com 3 tentativas e backoff, retomada com `Range`, verificação de tamanho, gravação em `.part` + rename; erro claro para mês inexistente; só hosts da allowlist.
**Where**: `src/rfb_pipeline/cliente_rfb.py`
**Depends on**: T5
**Reuses**: resposta PROPFIND real (formato `<d:response><d:href>/public.php/webdav/2026-09/</d:href>...<d:getcontentlength>`)
**Requirement**: ING-01, ING-04
**Classificação**: M/NC

**Done when**:
- [x] Testes com `httpx.MockTransport`: último mês detectado; mês inexistente lista disponíveis; tamanho divergente apaga arquivo e levanta erro; falha 3x levanta erro citando o arquivo; sucesso após 2 falhas; retomada com Range
- [x] Gate quick passa

**Tests**: unit
**Gate**: quick
**Commit**: `feat(ingest): RFB WebDAV client with retry and size verification`

---

### T7: Download da Base dos Dados

**What**: `src/rfb_pipeline/basedosdados.py`: baixa as 4 tabelas (`one-click-download/<dataset>/<tabela>/<tabela>.csv.gz`) para o cache de downloads com retry e escrita atômica; suporta origem local (fixtures).
**Where**: `src/rfb_pipeline/basedosdados.py`
**Depends on**: T6
**Reuses**: `cliente_rfb.py` (helper de download/retry)
**Requirement**: ING-06
**Classificação**: M/NC

**Done when**:
- [x] Testes com MockTransport: 4 arquivos baixados; falha persistente não deixa arquivo parcial
- [x] Gate quick passa

**Tests**: unit
**Gate**: quick
**Commit**: `feat(ingest): Base dos Dados downloader`

---

### T8: Conversão zip/CSV → Parquet raw ★ crítica, grande

**What**: `src/rfb_pipeline/conversao.py`: extração segura de zip (anti zip-slip, checagem de integridade); conversão com DuckDB `read_csv` (opções ARCHITECTURE §4.2, `encoding='latin-1'`, colunas nomeadas, all VARCHAR, `store_rejects`) para `raw/rfb/<entidade>/mes_referencia=<mes>/` em Parquet zstd, com colunas técnicas; extração de `_data_referencia` do nome interno (`D60912` → 2026-09-12); rejeitos para `raw/_rejeitos/...`; limiar de rejeito; escrita em diretório temporário + rename atômico; conversão BD csv.gz (header, multilinha) para `raw/bd/<tabela>/`; streaming arquivo a arquivo e limites de memória/threads configuráveis para os ~8 GB de `Estabelecimentos0`.
**Where**: `src/rfb_pipeline/conversao.py`
**Depends on**: T7
**Reuses**: `esquemas.py`, `configuracao.py`, fixtures de T4
**Requirement**: ING-02, ING-03, ING-04
**Classificação**: G/C

**Done when**:
- [x] Testes cobrem ACs de ingestão 2–8, 13, 16: contagens 14/15/0 nas fixtures, `\`` final em K, O como registro único, `_data_referencia=2026-09-12`, CNAE `0111301` preservado como texto, limiar de rejeito com arquivo corrompido gerado no teste, zip-slip recusado, nenhuma pasta parcial após falha simulada
- [x] Gate quick passa

**Tests**: unit
**Gate**: quick
**Commit**: `feat(ingest): safe zip extraction and CSV to raw Parquet conversion`

---

### T9: Manifesto e idempotência

**What**: `src/rfb_pipeline/manifesto.py`: leitura/escrita de `_manifestos/<mes>.json` (formato ARCHITECTURE §4.3), sha256 em streaming, decisão "pular se checksum igual", `--force`.
**Where**: `src/rfb_pipeline/manifesto.py`
**Depends on**: T8
**Reuses**: `conversao.py` (contagens)
**Requirement**: ING-05
**Classificação**: M/NC

**Done when**:
- [x] Testes: manifesto com campos exigidos; segunda execução com mesmos zips não reescreve Parquet (mtime inalterado); `--force` reescreve
- [x] Gate quick passa

**Tests**: unit
**Gate**: quick
**Commit**: `feat(ingest): run manifest and idempotent re-ingestion`

---

### T10: CLI `rfb ingerir` e alvo `make ci` (parte EL)

**What**: `src/rfb_pipeline/cli.py` com `rfb ingerir [--mes] [--origem-local DIR] [--force]` (`--data-root` removido: `RAIZ_DADOS` vem do ambiente — R1-27) ligando cliente/BD/conversão/manifesto; `make ci` passa a: gerar fixtures → `rfb ingerir --origem-local` em `RAIZ_DADOS` temporário → `dbt deps/build --target ci` → `pytest tests/integration`. Teste de integração da ingestão.
**Where**: `src/rfb_pipeline/cli.py`
**Depends on**: T9
**Reuses**: todos os módulos EL
**Requirement**: ING-01..06, OPS-01
**Classificação**: M/NC

**Done when**:
- [x] `tests/integration/test_ingerir_cli.py`: datasets das 9 entidades + 4 BD criados; manifesto presente; exit ≠0 para mês inexistente e para limiar de rejeito excedido
- [x] `make ci` roda (dbt build vazio ok)
- [x] Gate full passa

**Tests**: integration
**Gate**: full
**Commit**: `feat(cli): rfb ingerir command and local CI pipeline`

---

### T11: Armazenamento remoto S3/Tigris

**What**: `src/rfb_pipeline/armazenamento.py` + `rfb sincronizar`: detecção `s3://`, validação de `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/`AWS_ENDPOINT_URL_S3`, SQL de `CREATE SECRET` para DuckDB (região `auto`, `URL_STYLE` configurável), upload boto3 de `raw/` e `gold/` pulando objetos com mesmo tamanho+checksum; target `s3` do profile usando o secret.
**Where**: `src/rfb_pipeline/armazenamento.py`
**Depends on**: T10
**Reuses**: `subir_arquivos_tigris.py` do original (lógica de upload)
**Requirement**: OPS-02
**Classificação**: M/NC

**Done when**:
- [x] Testes com moto server: upload, segunda sync não reenvia, variáveis faltantes nomeadas no erro, DuckDB lê Parquet de `s3://` do moto com o secret gerado
- [x] Gate quick passa

**Tests**: unit
**Gate**: quick
**Commit**: `feat(storage): S3/Tigris data root and sync command`

---

### T12: Fontes dbt com os checks do original

**What**: `transform/models/staging/rfb/_rfb__sources.yml` e `transform/models/staging/basedosdados/_bd__sources.yml` com `external_location` via `RAIZ_DADOS`, descrições (catálogo do notebook 3), freshness (`_ingerido_em`, 35/65 dias), testes de fonte dos ACs SRC 2–7 (unicidade/completude dos domínios, cnpj, relacionamentos, accepted_values de porte/situação, cobertura município RFB×BD contra seed `excecoes_conhecidas_municipio`, CNAEs sem par = warn), `meta.escopo: original` nos checks vindos dos notebooks 2.x e `adicao` nos novos.
**Where**: `transform/models/staging/rfb/_rfb__sources.yml`
**Depends on**: T10
**Reuses**: `docs/referencia-original/2.*.md`
**Requirement**: SRC-01
**Classificação**: M/NC

**Done when**:
- [x] `make ci` executa os testes de fonte: todos passam exceto 1 warn (CNAE sem par = 1)
- [x] `dbt source freshness --target ci` executa
- [x] Gate full passa

**Tests**: dbt data tests
**Gate**: full
**Commit**: `feat(dbt): sources with original data quality checks and freshness`

---

### T13: Staging de domínios e Base dos Dados + macros de limpeza

**What**: macros `texto_ou_nulo`, `lpad_codigo`, `filtro_mes_referencia` (var `mes_referencia` → maior disponível) e modelos `stg_rfb__cnaes`, `stg_rfb__municipios`, `stg_rfb__naturezas`, `stg_rfb__motivos`, `stg_rfb__simples`, `stg_bd__municipios` (lat/long do `centroide`), `stg_bd__cnaes`, `stg_bd__populacao`, `stg_bd__pib`, com yml (descrições, testes, `meta.escopo`) e `unit_tests` para lpad, texto vazio → NULL e parse do centroide.
**Where**: `transform/models/staging/`
**Depends on**: T12
**Reuses**: fontes de T12
**Requirement**: STG-01
**Classificação**: M/NC

**Done when**:
- [x] Unit tests dbt passam; `stg_bd__municipios` de Fundão tem latitude −19.9687…, longitude −40.3557…
- [x] Gate full passa

**Tests**: dbt data tests + dbt unit tests
**Gate**: full
**Commit**: `feat(dbt): staging for domain tables and Base dos Dados`

---

### T14: Staging de empresas e estabelecimentos ★ crítica, grande

**What**: macros `data_rfb` (YYYYMMDD → DATE, inválidos/0/00000000 → NULL), `decimal_rfb` (vírgula → ponto); `stg_rfb__empresas` e `stg_rfb__estabelecimentos` conforme ARCHITECTURE §5.3 e ACs STG 9–15 (cnpj_completo, lista de CNAEs secundários, descarte de contatos, filtro de mês), yml com testes (unicidade `cnpj_completo`, formato 14 dígitos) e `unit_tests` de cada regra. Atenção a desempenho: ~65 M linhas no real (view sobre Parquet, sem funções não vetorizáveis).
**Where**: `transform/models/staging/rfb/stg_rfb__estabelecimentos.sql`
**Depends on**: T13
**Reuses**: macros de T13
**Requirement**: STG-01
**Classificação**: G/C

**Done when**:
- [x] Unit tests cobrem ACs STG 9–14; AC 14 verificado por teste que falha se colunas de contato existirem
- [x] Gate full passa

**Tests**: dbt data tests + dbt unit tests
**Gate**: full
**Commit**: `feat(dbt): typed staging for empresas and estabelecimentos`

---

### T15: `bh_empresas` com paridade ★ crítica

**What**: `models/marts/original/bh_empresas.sql` (+ yml com contrato, catálogo do notebook 3, `meta.escopo: original`, coluna `idade_atual` `adaptado`), `audit__bh_empresas_sql_original` (SQL do notebook 3 traduzido literalmente, `now()` → `data_referencia`), teste singular de paridade (diferença zero, error), teste de descartes do inner join (warn, fixtures = 3), teste idade ∈ [0,200], unit tests das regras ORI 3–6, teste de integração com os valores da spec (12 linhas; linha A).
**Where**: `transform/models/marts/original/bh_empresas.sql`
**Depends on**: T14
**Reuses**: `docs/referencia-original/3_Modelo_de_Dados.md`
**Requirement**: ORI-01, ORI-03
**Classificação**: M/C

**Done when**:
- [x] `tests/integration/test_bh_empresas.py` confirma 12 linhas e os valores de A e E da spec
- [x] Gate full passa

**Tests**: dbt data tests + dbt unit tests + integration
**Gate**: full
**Commit**: `feat(dbt): bh_empresas with parity test against original SQL`

---

### T16: `agg_empresas`

**What**: `models/marts/original/agg_empresas.sql` + yml (contrato, catálogo original), teste de reconciliação `sum(qtd_empresas) = count(bh_empresas)` (error), teste de integração com a resposta da spec (Fundão/4741500: ATIVA 1 MICRO 3.9; INATIVA 4).
**Where**: `transform/models/marts/original/agg_empresas.sql`
**Depends on**: T32
**Reuses**: notebook 3
**Requirement**: ORI-02
**Classificação**: M/NC

**Done when**:
- [x] Teste de integração e reconciliação passam
- [x] Gate full passa

**Tests**: dbt data tests + integration
**Gate**: full
**Commit**: `feat(dbt): agg_empresas with reconciliation test`

---

### T17: `dim_municipio`

**What**: `int_municipios__conformados` + `dim_municipio` (**`sk_municipio` inteira** determinística, ids IBGE/RFB, hierarquia em colunas: região → UF → mesorregião → microrregião → município e região intermediária → imediata, lat/long, população do último ano ou var `ano_populacao`, PIB) com membro `-1` "NÃO INFORMADO"; contrato; testes (ADR-0013).
**Where**: `transform/models/marts/core/dim_municipio.sql`
**Depends on**: T16
**Reuses**: `stg_bd__*`, `stg_rfb__municipios`
**Requirement**: CORE-01
**Classificação**: M/NC

**Done when**:
- [x] Fundão com população 20000 (ano 2024) nas fixtures; membro −1 existe; teste de unicidade de chave
- [x] Gate full passa

**Tests**: dbt data tests + dbt unit tests
**Gate**: full
**Commit**: `feat(dbt): dim_municipio with population and centroids`

---

### T18: `dim_cnae`, `dim_natureza_juridica`, seeds de domínio

**What**: seeds `dominio_porte`, `dominio_situacao_cadastral`, `dominio_matriz_filial`; `dim_cnae` (hierarquia seção → divisão → grupo → classe → subclasse, código e descrição em colunas separadas), `dim_natureza_juridica`, `dim_porte`, `dim_situacao_cadastral`, todos com **`sk_*` inteira** e membro `-1`; contratos (ADR-0013).
**Where**: `transform/models/marts/core/dim_cnae.sql`
**Depends on**: T16
**Reuses**: `stg_bd__cnaes`, `stg_rfb__naturezas`
**Requirement**: CORE-01
**Classificação**: M/NC

**Done when**:
- [x] Testes de unicidade/not_null nas chaves; seeds carregados; `0111301` presente em `dim_cnae`
- [x] Gate full passa

**Tests**: dbt data tests
**Gate**: full
**Commit**: `feat(dbt): cnae, natureza, porte and situacao dimensions`

---

### T37: Padronização de nomes conforme ADR-0014

**What**: aplicar a convenção de idioma do ADR-0014 em todo o repositório, conforme a tabela "Antes → Depois" do ADR: subpastas de `models/` (e chaves em `dbt_project.yml`); módulos Python e seus testes; subcomandos da CLI e alvos do Make; variáveis `RAIZ_DADOS`/`RAIZ_DADOS_LOCAL`; diretórios de dados `_manifestos`/`_baixados`; identificadores Python com palavras em inglês fora da lista de exceções; atualizar todas as referências em código, `.env.example`, profiles/sources, testes, ARCHITECTURE, ADRs, spec, tasks, PLANO, ESCOPO, README e guia; criar `tests/unit/test_convencao_nomes.py` que falha se surgir subpasta de `models/`, prefixo de modelo, módulo Python, subcomando da CLI ou alvo do Make fora da convenção.
**Where**: `tests/unit/test_convencao_nomes.py`
**Depends on**: T15
**Reuses**: ADR-0014 (lista fechada de exceções)
**Requirement**: DOC-01
**Classificação**: M/NC

**Done when**:
- [x] `git grep` não encontra nomes antigos fora de trechos históricos explicitamente marcados (ex.: tabela "Antes → Depois" do ADR-0014)
- [x] `test_convencao_nomes.py` passa e falha ao introduzir uma subpasta `analises` em `models/marts/` (demonstrado)
- [x] Gate build passa (`make lint && make ci`, pre-commit)

**Tests**: unit + integration
**Gate**: build
**Commit**: `refactor: apply naming language convention (ADR-0014)`

---

### T32: Segundo mês nas fixtures e testes por mês

**What**: estender `scripts/gerar_fixtures.py` para gerar também `rfb/2026-08/` conforme a spec ("Segundo mês": sem a linha O, nomes internos `D60810`); garantir que todos os testes de fonte/staging sejam por mês (unicidade com `_mes_referencia`) e que o `make ci` ingira os dois meses (2026-08 e depois 2026-09) mantendo todas as respostas de 2026-09.
**Where**: `scripts/gerar_fixtures.py`
**Depends on**: T37
**Reuses**: gerador existente; testes `tests/unit/test_gerar_fixtures.py`
**Requirement**: UPD-02
**Classificação**: M/NC

**Done when**:
- [x] Testes do gerador cobrem o mês 2026-08 (14 estabelecimentos, `D60810`, determinismo)
- [x] `make ci` verde com dois meses no raw; números de 2026-09 inalterados
- [x] Gate full passa

**Tests**: unit + integration
**Gate**: full
**Commit**: `test(fixtures): second reference month for update and history scenarios`

---

### T33: `dim_data` (calendário)

**What**: `dim_data` com uma linha por dia do menor dia referenciado pelas fatos até `data_referencia`, `sk_data = yyyymmdd` (INTEGER), `data, ano, semestre, trimestre, mes, nome_mes (pt-BR), ano_mes, dia_semana`, membro `-1`; contrato; testes (unicidade, contém `20000229`, contém `sk` de `data_referencia`).
**Where**: `transform/models/marts/core/dim_data.sql`
**Depends on**: T16
**Reuses**: `dbt_utils.date_spine` ou `generate_series` do DuckDB
**Requirement**: BI-01
**Classificação**: M/NC

**Done when**:
- [x] Testes dbt de unicidade/not_null da chave e presença das datas da spec
- [x] Gate full passa

**Tests**: dbt data tests + dbt unit tests
**Gate**: full
**Commit**: `feat(dbt): calendar dimension for BI`

---

### T19: `fct_estabelecimentos`

**What**: `int_estabelecimentos__enriquecidos` (left joins + flags de correspondência) e `fct_estabelecimentos` (grão `cnpj_completo` como dimensão degenerada; **só chaves inteiras** `sk_municipio, sk_cnae, sk_natureza_juridica, sk_porte, sk_situacao_cadastral, sk_data_inicio_atividade, sk_data_situacao` com −1 quando sem par; `idade_anos`, `opcao_simples`, `opcao_mei`, `capital_social`, `eh_matriz`, `eh_ativa`), contrato, `relationships` (error) para cada FK, incluindo `dim_data`.
**Where**: `transform/models/marts/core/fct_estabelecimentos.sql`
**Depends on**: T17, T18, T33
**Reuses**: dims de T17/T18
**Requirement**: CORE-01
**Classificação**: M/NC

**Done when**:
- [x] Integração: 15 linhas; K/L/M presentes com −1 na dimensão faltante; A e C com `opcao_mei = true`
- [x] Gate full passa

**Tests**: dbt data tests + integration
**Gate**: full
**Commit**: `feat(dbt): fct_estabelecimentos without silent drops`

---

### T20: Bridge de CNAEs secundários

**What**: `int_cnaes_secundarios__explodidos` + `bridge_estabelecimento_cnae_secundario` (FK para fato e `dim_cnae`).
**Where**: `transform/models/marts/core/bridge_estabelecimento_cnae_secundario.sql`
**Depends on**: T19
**Reuses**: `stg_rfb__estabelecimentos.cnaes_secundarios_lista`
**Requirement**: CORE-01
**Classificação**: M/NC

**Done when**:
- [x] H gera 2 linhas; lista vazia gera 0; relacionamentos passam
- [x] Gate full passa

**Tests**: dbt data tests + dbt unit tests
**Gate**: full
**Commit**: `feat(dbt): bridge for secondary CNAEs`

---

### T21: `mart_concorrencia_municipio`

**What**: CNAE × município → ativos, inativos, ativos por 10 mil hab. (NULL sem população), ranking na UF.
**Where**: `transform/models/marts/analytics/mart_concorrencia_municipio.sql`
**Depends on**: T20
**Reuses**: fato + dims
**Requirement**: ANA-01
**Classificação**: M/NC

**Done when**:
- [x] Integração: (4741500, Fundão) → 1 / 4 / 0.5
- [x] Gate full passa

**Tests**: dbt data tests + integration
**Gate**: full
**Commit**: `feat(analytics): competition density by municipality`

---

### T22: `mart_sobrevivencia_coorte`

**What**: coorte × CNAE × porte × UF → elegíveis e sobreviventes a 1/3/5 anos e taxas, pela definição da spec; teste singular de invariantes (taxas ∈ [0,1], monotonicidade).
**Where**: `transform/models/marts/analytics/mart_sobrevivencia_coorte.sql`
**Depends on**: T20
**Reuses**: fato
**Requirement**: ANA-02
**Classificação**: M/NC

**Done when**:
- [x] Integração: (4741500, ES) somado → 6/6, 5/4, 4/2
- [x] Unit test dbt da regra de elegibilidade/sobrevivência
- [x] Gate full passa

**Tests**: dbt data tests + dbt unit tests + integration
**Gate**: full
**Commit**: `feat(analytics): cohort survival analysis`

---

### T23: `mart_dinamica_mercado`

**What**: ano × CNAE × município → aberturas, encerramentos, saldo.
**Where**: `transform/models/marts/analytics/mart_dinamica_mercado.sql`
**Depends on**: T20
**Reuses**: fato
**Requirement**: ANA-03
**Classificação**: M/NC

**Done when**:
- [x] Integração: anos da spec para (4741500, Fundão)
- [x] Gate full passa

**Tests**: dbt data tests + integration
**Gate**: full
**Commit**: `feat(analytics): market dynamics by year`

---

### T24: `mart_fornecedores_proximos`

**What**: macro `haversine_km`; mart para o município/CNAEs do caso (vars) com fornecedores ativos por CNAE principal ou secundário dentro de `raio_fornecedores_km`, distância e via (principal/secundário); testes de distância (≥0; 0 no próprio município).
**Where**: `transform/models/marts/analytics/mart_fornecedores_proximos.sql`
**Depends on**: T20
**Reuses**: bridge, dim_municipio
**Requirement**: ANA-04
**Classificação**: M/NC

**Done when**:
- [x] Integração: exatamente F (18.66 ± 0.5 km, principal) e H (73.68 ± 0.5 km, secundário)
- [x] Unit test dbt da macro haversine
- [x] Gate full passa

**Tests**: dbt data tests + dbt unit tests + integration
**Gate**: full
**Commit**: `feat(analytics): nearby suppliers by distance`

---

### T25: Testes genéricos de DQ e governança de escopo

**What**: testes genéricos `cnpj_dv_valido` (warn, `error_if` > 0,1%) e `data_nao_futura` aplicados ao staging; `store_failures` para testes warn; `tests/integration/test_escopo_meta.py` lê `transform/target/manifest.json` e falha se algum nó do projeto (models, seeds, tests singulares/genéricos do projeto, macros) não tiver `meta.escopo` ou a tag correspondente.
**Where**: `transform/macros/tests/cnpj_dv_valido.sql`
**Depends on**: T20
**Reuses**: -
**Requirement**: DQ-01
**Classificação**: M/NC

**Done when**:
- [x] `cnpj_dv_valido` acusa exatamente 1 falha (L) nas fixtures; teste de escopo passa
- [x] Gate full passa

**Tests**: dbt data tests + integration
**Gate**: full
**Commit**: `feat(dq): CNPJ check-digit and future-date tests, scope governance`

---

### T26: Observabilidade de DQ e catálogo

**What**: macro `on-run-end` que grava resultados de testes em `dq_historico_testes` (incremental; invocation_id, nome, status, falhas, severidade, escopo, timestamp) e modelo `dq_resumo_execucao`; `docs/QUALIDADE_DADOS.md` com todos os checks por etapa (antes/depois), origem (notebook) e severidade.
**Where**: `transform/macros/registrar_resultados_testes.sql`
**Depends on**: T25
**Reuses**: `ARCHITECTURE.md` §6
**Requirement**: DQ-02
**Classificação**: M/NC

**Done when**:
- [x] Após `make ci`, `dq_historico_testes` tem uma linha por teste executado; duas execuções acumulam
- [x] Gate full passa

**Tests**: integration
**Gate**: full
**Commit**: `feat(dq): test results history and data quality catalog`

---

### T27: Estudo de caso e relatório

**What**: `transform/analyses/estudo_caso_q1..q4*.sql` reproduzindo cada consulta do notebook 4 (parametrizadas por vars `caso_*`) + análises das adições; `src/rfb_pipeline/relatorio.py` + `rfb relatorio` gerando `docs/RELATORIO_ESTUDO_CASO.md` (com seção de DQ da última execução).
**Where**: `src/rfb_pipeline/relatorio.py`
**Depends on**: T24
**Reuses**: `docs/referencia-original/4_An_lise_de_Dados.md`
**Requirement**: CASE-01
**Classificação**: M/NC

**Done when**:
- [x] Integração: relatório nas fixtures afirma 1 concorrente ativo e 4 inativos
- [x] Gate full passa

**Tests**: integration
**Gate**: full
**Commit**: `feat(report): case study analyses and generated report`

---

### T34: `fct_resumo_mensal` com histórico por partição

**What**: fato agregada para Power BI no grão (`sk_mes_referencia`, `sk_municipio`, `sk_cnae`, `sk_porte`, `sk_situacao_cadastral`, `opcao_mei`) com `qtd_estabelecimentos`, `qtd_ativos`, `soma_idade_anos`, `qtd_matrizes`, `soma_capital_social_matrizes` *(emenda R3-01/R3-02: sem `sk_natureza_juridica` e `ano_inicio_atividade`; capital só das matrizes)*; gravada como **uma partição Parquet por mês** em `gold/fct_resumo_mensal/mes_referencia=YYYY-MM/` (reprocessar substitui só a partição do mês; histórico sobrevive à remoção do `warehouse.duckdb`); visão/fonte que lê todas as partições para consumo; teste de reconciliação do mês corrente com `fct_estabelecimentos` (error).
**Where**: `transform/models/marts/core/fct_resumo_mensal.sql`
**Depends on**: T20
**Reuses**: fato e dimensões de T17–T19, T33
**Requirement**: BI-02, UPD-02
**Classificação**: M/NC

**Done when**:
- [x] Integração: após processar 2026-08 e 2026-09, duas partições; (Serra, 4741500, ATIVA) = 0/ausente em 2026-08 e 1 em 2026-09; soma de 2026-09 = 15
- [x] Apagar `warehouse.duckdb` e rodar 2026-09 de novo mantém a partição 2026-08
- [x] Gate full passa

**Tests**: dbt data tests + integration
**Gate**: full
**Commit**: `feat(dbt): monthly summary fact with partitioned history`

---

### T35: Guia Power BI e exposure

**What**: `docs/POWER_BI.md` (diagrama mermaid da estrela, tabela de relacionamentos 1:* direção única, conexão via conector Parquet do Power Query e via ODBC do DuckDB, atualização incremental por mês, ≥ 8 medidas DAX sugeridas — ex. Qtd Ativos, % Ativos, Idade Média, Ativos por 10 mil hab., Taxa de Sobrevivência 3a, Variação Mensal de Ativos) e `exposure` dbt tipo `dashboard` dependendo de todas as dims e fatos.
**Where**: `docs/POWER_BI.md`
**Depends on**: T34
**Reuses**: ADR-0013
**Requirement**: BI-02
**Classificação**: M/NC

**Done when**:
- [x] `dbt ls --resource-type exposure` lista a exposure; `dbt parse` ok
- [x] Documento cobre todos os itens do AC BI-7
- [x] Gate full passa

**Tests**: none
**Gate**: full
**Commit**: `docs(bi): Power BI guide and dashboard exposure`

---

### T28: Pipeline ponta a ponta com dados reais ★ crítica (E2E)

**What**: `rfb pipeline` / `make pipeline MES=2026-09` (ingest → freshness → build → report, exit ≠0 em erro); execução real completa sobre 2026-09; ajuste de desempenho (materializações, memória, threads, ordem); `make ci` < 120 s; registro de tempos, volumes e resultados (incluindo paridade = 0 diferenças) em `docs/EXECUCAO_REAL.md`; relatório real gerado.
**Where**: `src/rfb_pipeline/cli.py`
**Depends on**: T27, T41, T43
**Reuses**: tudo
**Requirement**: OPS-01
**Classificação**: M/C

**Done when**:
- [ ] Pipeline real conclui sem testes `error`; warns documentados
- [ ] `make ci` < 120 s
- [ ] Gate build passa

**Tests**: integration
**Gate**: build
**Commit**: `feat(pipeline): end-to-end run on real 2026-09 data`

---

### T38: Download da Base dos Dados pela API atual

**What**: trocar o download de todas as tabelas BD do caminho legado `one-click-download/…` (congelado em dez/2023) pela API `https://basedosdados.org/api/tables/downloadTable` (base64 de dataset, tabela, `true`, `free`); host permitido `basedosdados.org`; manter `--origem-local`, manifesto e erros; conferir que colunas de `populacao`/`pib`/`municipio`/`cnae_2` continuam compatíveis com o staging (ajustar se não).
**Where**: `src/rfb_pipeline/basedosdados.py`
**Depends on**: T35
**Reuses**: `basedosdados.py`, `configuracao.py`, `esquemas.TABELAS_BD`
**Requirement**: ENR-01
**Classificação**: M/NC
**Incremento**: enriquecimento BD (ADR-0015)

**Done when**:
- [x] Unit tests com `httpx.MockTransport` cobrem URL/base64, sucesso, erro HTTP e conteúdo não gzip
- [x] Nenhuma referência ao caminho legado no código
- [x] Gate full passa

**Tests**: unit
**Gate**: full
**Commit**: `fix(ingestao): download Base dos Dados via current downloadTable API`

---

### T39: Novas tabelas BD no raw + fixtures

**What**: ingerir `br_ibge_censo_2022.municipio`, `br_geobr_mapas.regiao_metropolitana_2017` e `br_bd_vizinhanca.municipio` (raw all-VARCHAR, manifesto); fixtures sintéticas determinísticas para os municípios do cenário (Fundão, Serra, Vitória, Linhares, Aracruz, Belo Horizonte…) com respostas conhecidas documentadas na spec; fontes dbt e staging (`stg_bd__censo_2022_municipio`, `stg_bd__regioes_metropolitanas`, `stg_bd__vizinhanca`) com testes.
**Where**: `src/rfb_pipeline/esquemas.py`, `scripts/gerar_fixtures.py`, `transform/models/staging/basedosdados/`
**Depends on**: T38
**Reuses**: padrão das tabelas BD existentes
**Requirement**: ENR-01
**Classificação**: M/NC
**Incremento**: enriquecimento BD (ADR-0015)

**Done when**:
- [x] `make ci` ingere as três tabelas; testes do gerador cobrem as linhas novas
- [x] Gate full passa

**Tests**: unit + dbt data tests + dbt unit tests
**Gate**: full
**Commit**: `feat(ingestao): census 2022, metropolitan regions and neighbourhood from Base dos Dados`

---

### T40: `dim_municipio` enriquecida + vizinhança conformada

**What**: colunas do Censo 2022 e `nome_regiao_metropolitana` em `dim_municipio` (contrato, descrições, testes); relação de vizinhança conformada por `sk_municipio` (simétrica, sem autopares, ano mais recente) com testes de unicidade e integridade.
**Where**: `transform/models/marts/core/dim_municipio.sql`
**Depends on**: T39
**Reuses**: `int_municipios__conformados`
**Requirement**: ENR-02
**Classificação**: M/NC
**Incremento**: enriquecimento BD (ADR-0015)

**Done when**:
- [x] Integração: atributos de Fundão iguais aos da fixture; vizinhos de Fundão = os da fixture
- [x] Gate full passa

**Tests**: dbt data tests + dbt unit tests + integration
**Gate**: full
**Commit**: `feat(dbt): census 2022 attributes, metropolitan region and neighbours in dim_municipio`

---

### T41: Concorrência na área de mercado + estudo de caso

**What**: `mart_concorrencia_area_mercado` (CNAE × município: ativos/inativos no município, nos vizinhos e na região metropolitana; ativos por mil domicílios e por km²); seção nova no relatório do estudo de caso; `docs/POWER_BI.md`, `ARCHITECTURE.md`, `docs/ESCOPO.md` e `docs/QUALIDADE_DADOS.md` atualizados.
**Where**: `transform/models/marts/analytics/mart_concorrencia_area_mercado.sql`
**Depends on**: T40
**Reuses**: `mart_concorrencia_municipio`, `relatorio.py`
**Requirement**: ENR-03
**Classificação**: M/NC
**Incremento**: enriquecimento BD (ADR-0015)

**Done when**:
- [x] Integração: indicadores de Fundão/4741500 iguais aos da tabela do cenário; relatório traz a área de mercado
- [x] Gate full passa

**Tests**: dbt data tests + integration
**Gate**: full
**Commit**: `feat(analytics): competition in the market area (neighbours and metropolitan region)`

---

### T42: `rfb publicar --destino motherduck`

**What**: módulo `src/rfb_pipeline/publicacao.py` + subcomando `rfb publicar --destino motherduck [--tabelas …]` + `make publicar`: só com `MOTHERDUCK_TOKEN` e `MOTHERDUCK_BANCO` definidos, `ATTACH 'md:<banco>'` e `CREATE OR REPLACE TABLE … AS SELECT * FROM read_parquet(…)` para cada dataset do gold (inclusive todas as partições de `fct_resumo_mensal`), com relatório de linhas; sem configuração, mensagem clara e saída 0; token nunca registrado; `.env.example` documentado. O destino é parametrizável para os testes (arquivo DuckDB local no lugar de `md:`).
**Where**: `src/rfb_pipeline/publicacao.py`
**Depends on**: T41
**Reuses**: `configuracao.py`, `cli.py`, layout do gold
**Requirement**: PUB-01
**Classificação**: M/NC

**Done when**:
- [ ] Unit: SQL gerado, seleção de tabelas, ausência de variáveis (sai 0, nada publicado), token ausente dos logs
- [ ] Integração: publicação das fixtures num destino DuckDB local com as mesmas contagens do gold
- [ ] Gate full passa

**Tests**: unit + integration
**Gate**: full
**Commit**: `feat(publicacao): optional publish of gold tables to MotherDuck`

---

### T43: Guia Power BI — como acessar os dados

**What**: seção nova em `docs/POWER_BI.md` "Como o Power BI acessa os dados": tabela comparando (1) Parquet em `gold/` (conector Parquet/Pasta; Import; sem driver), (2) arquivo DuckDB local (`warehouse.duckdb`, views sobre o gold; driver ODBC do DuckDB; Import; travas de arquivo durante o build), (3) MotherDuck após `rfb publicar` (conector PostgreSQL nativo pelo Postgres endpoint; Import ou DirectQuery; gateway no Service); passo a passo de cada um, atualização no Power BI Service e recomendação por cenário; links oficiais; `ARCHITECTURE.md` e `docs/ESCOPO.md` atualizados.
**Where**: `docs/POWER_BI.md`
**Depends on**: T42
**Reuses**: ADR-0016
**Requirement**: PUB-02
**Classificação**: M/NC

**Done when**:
- [ ] As três opções descritas com modo, instalação, atualização e limitações, com fontes oficiais
- [ ] Gate build passa

**Tests**: none
**Gate**: build
**Commit**: `docs(bi): how Power BI accesses the data (Parquet, DuckDB, MotherDuck)`

---

### T36: `rfb atualizar` — atualização mensal automática (E2E)

**What**: comando `rfb atualizar [--origem-local DIR]` + `make atualizar`: detecção do mês completo mais recente (todos os arquivos esperados presentes), comparação com `RAIZ_DADOS/_estado/ultima_execucao.json`, execução ingest → `dbt build --vars mes_referencia` → relatórios (→ sync se s3), gravação do estado só em sucesso, retenção (`RFB_MESES_RETIDOS`, `RFB_MANTER_ZIPS`), mensagem "nenhum mês novo"; `docs/OPERACAO.md` com receitas cron, launchd e GitHub Actions; validação real: executar contra o WebDAV após T28 e confirmar no-op para 2026-09.
**Where**: `src/rfb_pipeline/cli.py`
**Depends on**: T28, T34
**Reuses**: `rfb pipeline` (T28), manifesto (T9), cliente WebDAV (T6)
**Requirement**: UPD-01
**Classificação**: M/NC (roteado a Opus por ser E2E)

**Done when**:
- [ ] Integração com fixtures de dois meses cobre ACs UPD 1–5 e 8 (mês novo processado, no-op, mês incompleto ignorado, falha do dbt não grava estado, retenção)
- [ ] Execução real contra o WebDAV registrada em `docs/EXECUCAO_REAL.md`
- [ ] Gate build passa

**Tests**: integration
**Gate**: build
**Commit**: `feat(pipeline): monthly auto-update with completeness check and retention`

---

### T29: Guia dbt — parte 1 (fundamentos)

**What**: `docs/guia-dbt/01-fundamentos.md`: o que é o dbt; como funciona (compilação Jinja→SQL, DAG, adapters, execução); conceitos (models, sources, seeds, snapshots, tests, macros, packages, materializations, ref/source, vars, profiles/targets, docs, exposures, contracts, unit tests, selectors); estrutura típica de projeto; comandos (`deps, debug, parse, compile, run, test, build, seed, snapshot, source freshness, docs, ls, show, run-operation, retry, clone`, seleção de nós, `--target`, `--vars`, state/defer); dbt Core × Cloud × Fusion; links para docs oficiais.
**Where**: `docs/guia-dbt/01-fundamentos.md`
**Depends on**: None
**Reuses**: ARCHITECTURE.md (exemplos deste projeto)
**Requirement**: DOC-01
**Classificação**: M/NC

**Done when**:
- [x] Todos os tópicos listados cobertos com exemplos; links oficiais conferidos

**Tests**: none
**Gate**: build
**Commit**: `docs(guia): dbt fundamentals`

---

### T30: Guia dbt — parte 2 (fluxo, testes e qualidade neste projeto)

**What**: `docs/guia-dbt/02-fluxo-e-testes.md`: como os dados fluem em cada etapa deste projeto (raw → staging → intermediate → marts → gold, com exemplos reais de SQL compilado e contagens); como funcionam os testes (data tests genéricos/singulares, severidade, `warn_if/error_if`, `store_failures`, unit tests, contratos, freshness); checks recomendados **antes e depois de cada etapa** com exemplos em YAML/SQL deste projeto; link para `docs/QUALIDADE_DADOS.md`.
**Where**: `docs/guia-dbt/02-fluxo-e-testes.md`
**Depends on**: None
**Reuses**: código das fases 4–7
**Requirement**: DOC-01
**Classificação**: M/NC

**Done when**:
- [ ] Cada etapa com ao menos um check "antes" e um "depois" com exemplo real do projeto

**Tests**: none
**Gate**: build
**Commit**: `docs(guia): data flow, testing and data quality`

---

### T31: Guia dbt — parte 3 (bibliotecas e técnicas) + índice e README

**What**: `docs/guia-dbt/03-bibliotecas-e-tecnicas.md` (dbt_utils, dbt_expectations, dbt-audit-helper, elementary, dbt-project-evaluator, dbt-checkpoint, sqlfluff, codegen, re_data/Soda/Great Expectations como alternativas, dbt-duckdb plugins/external, incremental, snapshots, CI slim com state:modified, data diff); `docs/guia-dbt/README.md` (índice); `README.md` final (uso, pitch, links); `docs/ESCOPO.md` final.
**Where**: `docs/guia-dbt/03-bibliotecas-e-tecnicas.md`
**Depends on**: T30
**Reuses**: -
**Requirement**: DOC-01
**Classificação**: M/NC

**Done when**:
- [ ] Índice liga todas as partes, ARCHITECTURE, ADRs, QUALIDADE_DADOS, ESCOPO

**Tests**: none
**Gate**: build
**Commit**: `docs(guia): libraries, techniques and index`

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1–T3 | 1 arquivo de config principal cada (+ arquivos de apoio triviais) | ⚠️ OK (coeso) |
| T4–T11 | 1 módulo Python + seu teste | ✅ Granular |
| T12 | 1 camada de fontes (2 yml, mesma responsabilidade) | ⚠️ OK (coeso) |
| T13 | staging de 9 tabelas pequenas 1:1 + 3 macros | ⚠️ OK (coeso, padrão repetitivo) |
| T14–T24 | 1 modelo (ou modelo + seu intermediário direto) | ✅ Granular |
| T25–T27 | 1 capacidade de DQ/relatório | ✅ Granular |
| T28 | orquestração + execução real | ⚠️ OK (E2E indivisível) |
| T29–T31 | 1 documento | ✅ Granular |

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | início Phase 1 | ✅ |
| T2 | T1 | T1 → T2 | ✅ |
| T3 | T2 | T2 → T3 | ✅ |
| T4 | T1 (fase anterior) | início Phase 2 | ✅ |
| T5 | T4 | T4 → T5 | ✅ |
| T6 | T5 | T5 → T6 | ✅ |
| T7 | T6 | T6 → T7 | ✅ |
| T8 | T7 (fase anterior) | Phase 3 | ✅ |
| T9 | T8 (fase anterior) | início Phase 4 | ✅ |
| T10 | T9 | T9 → T10 | ✅ |
| T11 | T10 | T10 → T11 | ✅ |
| T12 | T10 | T10 → T12 | ✅ |
| T13 | T12 | T12 → T13 | ✅ |
| T14 | T13 (fase anterior) | início Phase 5 | ✅ |
| T15 | T14 | T14 → T15 | ✅ |
| T16 | T15 (fase anterior) | Phase 6 | ✅ |
| T17 | T16 (mesma fase, sem aresta — sequencial) | T17 → T19 | ⚠️ ver nota |
| T18 | T16 (mesma fase, sem aresta — sequencial) | T18 → T19 | ⚠️ ver nota |
| T19 | T17, T18 | T17 → T19, T18 → T19 | ✅ |
| T20 | T19 | T19 → T20 | ✅ |
| T21–T25 | T20 (fase anterior) | Phase 7 | ✅ |
| T26 | T25 | T25 → T26 | ✅ |
| T27 | T24 (mesma fase, sequencial) | Phase 7 | ⚠️ ver nota |
| T28 | T27 (fase anterior) | Phase 8 | ✅ |
| T29 | None | Phase 9 (trilha paralela) | ✅ |
| T30 | None (conteúdo depende das Fases 4–7 concluídas) | Phase 9 | ✅ |
| T31 | T30 | T30 → T31 | ✅ |
| T38 | T35 (fase anterior) | T35 → T38 | ✅ |
| T39 | T38 | T38 → T39 | ✅ |
| T40 | T39 | T39 → T40 | ✅ |
| T41 | T40 | T40 → T41 | ✅ |
| T42 | T41 (fase anterior) | T41 → T42 | ✅ |
| T43 | T42 | T42 → T43 | ✅ |

Nota: execução dentro da fase é estritamente sequencial na ordem numérica; dependências intra-fase não desenhadas são satisfeitas pela ordem.

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1–T3 | Config/tooling | none | none | ✅ |
| T4 | Fixtures | unit | unit | ✅ |
| T5–T9, T11 | Python EL | unit | unit | ✅ |
| T10 | CLI + fluxo | integration | integration | ✅ |
| T12 | dbt sources | dbt data tests | dbt data tests | ✅ |
| T13, T14 | dbt staging | dbt data + unit tests | dbt data + unit tests | ✅ |
| T15–T24 | dbt marts | dbt data/unit tests (+ integração nos ACs numéricos) | idem | ✅ |
| T25 | dbt tests + governança | dbt data tests + integration | idem | ✅ |
| T26, T27 | observabilidade/relatório | integration | integration | ✅ |
| T28 | CLI + fluxo real | integration | integration | ✅ |
| T29–T31 | Documentação | none | none | ✅ |
| T38, T39 | Python EL + fixtures + dbt staging | unit + dbt tests | idem | ✅ |
| T40, T41 | dbt marts + relatório | dbt data/unit tests + integration | idem | ✅ |
