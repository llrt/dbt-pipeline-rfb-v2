# Port RFB/CNPJ para dbt + DuckDB Validation

**Date**: 2026-10-01
**Spec**: `.specs/features/rfb-dbt-port/spec.md`
**Diff range**: feature inteira até `e84a0a2` (`main`); revisão de código focada em `16fb77b..e84a0a2` (B10, B11, FBPa, B8)
**Verifier**: R4, agente independente (Claude Opus, Traycer). Não escreveu nenhum código do projeto (autor ≠ verificador)
**Relatório de revisão**: [`docs/revisoes/R4.md`](../../../docs/revisoes/R4.md)

**Veredito: FAIL ⚠️ (Issues).** O produto está pronto para entrega com ressalvas (R4.md), mas a regra do
Verifier exige zero mutante sobrevivente e todo AC batendo com o texto da spec. Restam 2 mutantes
sobreviventes (D04 → Fix 1; D08 → Fix 7), 1 AC reprovado no texto (OPS AC 1, < 120 s), 6 lacunas de precisão da
spec e 1 Success Criterion sem evidência (Power BI). Todos os 107 ACs têm evidência citável (100 %);
100 deles (93 %) afirmam exatamente o resultado da spec.

Legenda: ✅ PASS (o teste afirma o resultado da spec) · ⚠️ lacuna de precisão (evidência existe, mas a
spec diz outra coisa ou o AC está só em parte) · ❌ GAP (sem evidência ou reprovado) · 📄 evidência por
arquivo ou execução (AC de documentação ou operação, sem teste automatizado). Caminhos de teste são
relativos à raiz. "dbt:" indica teste dbt executado pelo `make ci` (`dbt build --target ci`).

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1–T29, T32–T43 | ✅ Done | Integrados e verificados pelo líder (`docs/PLANO.md`); gates reexecutados nesta validação (`make ci` verde) |
| T30 | ⚠️ Partial (bookkeeping) | Conteúdo existe (`docs/guia-dbt/02-fluxo-e-testes.md`, `03-qualidade-antes-e-depois.md`), mas o "Done when" de `tasks.md:956` não foi marcado |
| T31 | ⚠️ Partial (bookkeeping) | Índice `docs/guia-dbt/README.md` liga as partes, ARCHITECTURE, ADRs, QUALIDADE_DADOS e ESCOPO (17 referências), mas `tasks.md:974` não foi marcado |

---

## Spec-Anchored Acceptance Criteria

### P1: Ingestão reprodutível (ING-01..06)

| AC | Resultado definido na spec | `file:line` + asserção | Result |
|---|---|---|---|
| 1 sem `--mes` → mês mais recente | pasta YYYY-MM mais recente | `tests/unit/test_cliente_rfb.py:75` (último ordenado); `tests/unit/test_resolver_mes.py:61` escolhe o mais recente **completo** e `:89` o mais recente com `--permitir-incompleto` | ⚠️ spec: ADR-0012/UPD AC 3 mudou para "mais recente completo"; ING AC 1 não foi emendado |
| 2 um dataset por entidade em `raw/rfb/<entidade>/mes_referencia=2026-09/` (9 entidades) | 9 diretórios | `tests/integration/test_ingerir_cli.py:46`: `assert particao.is_dir()` e parquet presente para cada uma de `ENTIDADES_RFB` | ✅ |
| 3 todas as colunas VARCHAR com os nomes da ARCHITECTURE §4.2 + 4 técnicas | lista literal | `tests/unit/test_esquemas.py:23`, `:29` (listas literais); `tests/unit/test_conversao.py:259` (contrato por entidade, tipo VARCHAR) | ✅ |
| 4 `\"` antes da aspa de fechamento (K) | valor termina em `\`, sem rejeito | `tests/unit/test_conversao.py:130` | ✅ |
| 5 campo multilinha (O) | um único registro | `tests/unit/test_conversao.py:139` | ✅ |
| 6 contagens | 15 empresas, 16 estabelecimentos, 0 rejeitos | `tests/unit/test_conversao.py:96`; `tests/integration/test_ingerir_cli.py:58` (manifesto) | ✅ |
| 7 `D60912` → `_data_referencia` | 2026-09-12 | `tests/unit/test_conversao.py:335` (parametrizado) | ✅ |
| 8 rejeito > limiar | sai ≠ 0 e grava em `raw/_rejeitos/` | `tests/unit/test_conversao.py:342`; `tests/integration/test_ingerir_cli.py:84` (código 1) | ✅ |
| 9 tamanho ≠ `getcontentlength` | apaga e sai ≠ 0 sem gravar raw | `tests/unit/test_cliente_rfb.py:143` | ✅ |
| 10 erro de rede após 3 tentativas | sai ≠ 0 citando o arquivo | `tests/unit/test_cliente_rfb.py:166` | ✅ |
| 11 mês inexistente | sai ≠ 0 listando os disponíveis | `tests/integration/test_ingerir_cli.py:70`; `tests/unit/test_cliente_rfb.py:89` | ✅ |
| 12 mesmos checksums | pula a conversão, Parquet intacto | `tests/integration/test_ingerir_cli.py:270`; `tests/unit/test_manifesto.py:108` | ✅ |
| 13 nunca Parquet parcial | temp + rename atômico | `tests/unit/test_conversao.py:408`, `:429`, `:448`, `:490` | ✅ |
| 14 manifesto | tamanho, sha256, lidas e rejeitadas por arquivo | `tests/unit/test_manifesto.py:53`, `:163`; `tests/integration/test_ingerir_cli.py:290` | ✅ |
| 15 4 tabelas BD em `raw/bd/<tabela>/` | municipio, cnae_2, populacao, pib | `tests/integration/test_ingerir_cli.py:53` (todas as `TABELAS_BD`, hoje 7); `tests/unit/test_basedosdados.py:24` | ✅ |
| 16 zip-slip | recusa e sai ≠ 0 | `tests/unit/test_conversao.py:627`, `:644` | ✅ |
| 17 nunca `Socios*` | não baixado | `tests/unit/test_cliente_rfb.py:103`; `tests/unit/test_esquemas.py:55`; real: nenhum arquivo `Socios*` em `real-2026-09/` (consulta R4) | ✅ |

### P1: Staging e fontes (SRC-01, STG-01)

| AC | Resultado definido na spec | `file:line` + asserção | Result |
|---|---|---|---|
| 1 fontes com `external_location` de `env_var('RAIZ_DADOS')` | todas as fontes | `transform/models/staging/rfb/_rfb__sources.yml:21` (e as demais 8); `_bd__sources.yml:18`; exercitado por `tests/integration/test_dbt_s3.py:40` (`external_root: s3://bucket/x/gold`) | ✅ |
| 2 `unique`+`not_null` em `codigo` de cnaes, municipios, naturezas, motivos | error | dbt: `_rfb__sources.yml:216/224`, `:248/256`, `:278/286`, `:308/316` | ✅ |
| 3 unicidade de `empresas.cnpj_raiz` e `cnpj_completo` | error | dbt: `_rfb__staging.yml:153` (`unique` error no staging) e `:220-222` (`cnpj_completo`); na fonte, `_rfb__sources.yml:29-32` virou **warn** (B8) | ⚠️ o check do notebook 2.2 sobre o raw é warn; o error passou para o staging deduplicado (R4-05) |
| 4 FKs natureza, CNAE e município nos domínios RFB | error | dbt: `transform/tests/relacionamentos_fontes_por_mes.sql` | ✅ |
| 5 `porte ∈ {00,01,03,05}` e `situacao ∈ {01,02,03,04,08}` | accepted_values | dbt: `_rfb__sources.yml:53`, `:111` | ✅ |
| 6 municípios sem par = seed de exceções (9707, 1182) | error para outros | dbt: `transform/tests/cobertura_municipio_rfb_bd.sql`, `excecoes_municipio_obsoletas.sql` | ✅ |
| 7 CNAEs sem par | warn com contagem (1) | dbt: `transform/tests/cnaes_sem_par_bd.sql`; CI: `dq_historico_testes` → `('cnaes_sem_par_bd','warn',1)` | ✅ |
| 8 freshness 35/65 dias + `extrato_desatualizado` | warn/error | `tests/integration/test_freshness.py:44`, `:50` (40 dias avisa), `:56` (70 dias erro), `:62` | ✅ |
| 9 `cnpj_completo` com 14 dígitos | lpad 8+4+2 | dbt unit: `_rfb__staging.yml:537` (`test_stg_rfb__estabelecimentos_cnpj_e_codigos`); `tamanho_exato` `:224` | ✅ |
| 10 data inválida → NULL | `0`, `00000000`, inválida | dbt unit: `_rfb__staging.yml:574`, `:395` | ✅ |
| 11 `1000,50` → 1000.50 | DECIMAL | dbt unit: `_rfb__staging.yml:459` | ✅ |
| 12 texto vazio → NULL | NULL | dbt unit: `_rfb__staging.yml:345`, `:459`, `:537` | ✅ |
| 13 CNAE 7 dígitos, município 4 | lpad | dbt unit: `_rfb__staging.yml:345`, `:380`, `:537` | ✅ |
| 14 sem colunas de contato | nenhuma em staging ou a jusante | dbt: `transform/tests/sem_colunas_de_contato.sql` (regex, error); real: 0 colunas de contato nos 15 datasets do gold (consulta R4) | ✅ |
| 15 var nula → maior `_mes_referencia` | maior mês | dbt unit: `_rfb__staging.yml:492`, `:643`, `:672` | ✅ |

### P1: Modelos originais (ORI-01..03)

| AC | Resultado definido na spec | `file:line` + asserção | Result |
|---|---|---|---|
| 1 15 colunas, contrato enforced | lista exata | `transform/models/marts/original/_original__models.yml:15` (`enforced: true`) | ✅ |
| 2 13 linhas (sem K, L, M) | 13 | `tests/integration/test_bh_empresas.py:51` | ✅ |
| 3 mapa de porte (E → NULL) | N/A, MICRO, PEQUENA, DEMAIS, NULL | dbt unit `_original__models.yml:209`; `tests/integration/test_bh_empresas.py:71` | ✅ |
| 4 situação 2 → ATIVA, senão INATIVA | — | dbt unit `_original__models.yml:261` | ✅ |
| 5 idade (A → 3.9; inativa NULL) | 3.9 | `tests/integration/test_bh_empresas.py:57`; dbt unit `:261`, `:291` | ✅ |
| 6 `nome = upper(coalesce(fantasia, razão))` | `TINTAS FUNDÃO`, `TINTAS CAPIXABA` | `tests/integration/test_bh_empresas.py:57`, `:71`, `:104` | ✅ |
| 7 domínios em maiúsculas (A → FUNDÃO, LINHARES, LITORAL NORTE…, ES) | valores literais | `tests/integration/test_bh_empresas.py:57`; dbt unit `_original__models.yml:311` | ✅ |
| 8 `agg_empresas` por 10 dimensões, count e avg | — | dbt unit `_original__models.yml:351`; `tests/integration/test_agg_empresas.py:52`, `:60` | ✅ |
| 9 soma de `qtd_empresas` = count(bh) | error | dbt: `transform/tests/agg_empresas_reconciliacao.sql`; `tests/integration/test_agg_empresas.py:66` | ✅ |
| 10 paridade com o SQL do notebook 3 | error, diferença 0 | dbt: `transform/tests/paridade_bh_empresas.sql`; real: `run_results-8x8.json` e `run_results-2025-02.json` com `paridade_bh_empresas` failures = 0 | ✅ |
| 11 descartes do inner join | warn = 3 (K, L, M) | `tests/integration/test_bh_empresas.py:146` | ✅ |
| 12 idade fora de [0,200] | warn; error > 100 | `tests/integration/test_bh_empresas.py:126` | ✅ |
| 13 regras 3–6 por unit tests | dbt unit tests | `_original__models.yml:209`, `:261`, `:291`, `:311` | ✅ |

### P2: Star schema (CORE-01)

| AC | Resultado definido na spec | `file:line` + asserção | Result |
|---|---|---|---|
| 1 fato com 1 linha por CNPJ, contrato | **15** linhas | `tests/integration/test_core.py:149`: `== [(16, 16)]`; contrato `_core__models.yml:459` | ⚠️ spec diz 15; a fixture P (R3-04) levou a 16, e o teste está certo |
| 2 membro −1 em vez de descarte | K, L, M com −1 | `tests/integration/test_core.py:155` | ✅ |
| 3 `dim_municipio` (Fundão → 20000) | 20000 | `tests/integration/test_core.py:33` | ✅ |
| 4 `dim_cnae` com hierarquia | seção…subclasse | `tests/integration/test_core.py:57` | ✅ |
| 5 bridge (H → 2) | 2 linhas | `tests/integration/test_core.py:214` | ✅ |
| 6 `opcao_mei` (A e C → true) | {A, C} | `tests/integration/test_core.py:181`: `mei == {CNPJ_A, CNPJ_O, CNPJ_C}` | ⚠️ spec omite O (filial de A; a opção é da empresa) |
| 7 `relationships` de toda FK, error | error | dbt: `_core__models.yml:480–540` (7 FKs) | ✅ |

### P2: Análises novas (ANA-01..04)

| AC | Resultado definido na spec | `file:line` + asserção | Result |
|---|---|---|---|
| 1 concorrência (4741500, Fundão) | ativos 1, inativos 4, 0,5/10k | `tests/integration/test_analises.py:20` | ✅ |
| 2 sobrevivência (4741500, ES) | 6/6, 5/4, 4/2 | `tests/integration/test_analises.py:47` | ✅ |
| 3 taxas em [0,1] e monotônicas | error | dbt: `transform/tests/sobrevivencia_invariantes.sql` | ✅ |
| 4 dinâmica (Fundão) | aberturas 2010, 2015, 2018, 2020, 2022; encerramentos 2019, 2021, 2023, 2024 | `tests/integration/test_analises.py:57` | ✅ |
| 5 fornecedores ≤ 100 km | F (18,66), P, H (73,68) | `tests/integration/test_analises.py:75`: lista exata e `approx(…, abs=0.5)` | ✅ |
| 6 exclui inativo (I) e fora do raio (G, J) | ausentes | `tests/integration/test_analises.py:75` (igualdade exata da lista) | ✅ |
| 7 distância ≥ 0 e 0 para si mesmo | error | dbt: `transform/tests/distancias_fornecedores_validas.sql` | ✅ |

### P2: Qualidade e observabilidade (DQ-01, DQ-02)

| AC | Resultado definido na spec | `file:line` + asserção | Result |
|---|---|---|---|
| 1 `cnpj_dv_valido` | 1 falha (L), warn | `tests/integration/test_qualidade_dados.py:27`; dbt: `transform/tests/cnpj_dv_valido_casos.sql` | ✅ |
| 2 `data_nao_futura` em toda data do staging, exceto exclusões do Simples/MEI | aplicado | dbt: `_rfb__staging.yml:98`, `:122`, `:256`, `:281`, `:326`; `transform/tests/data_nao_futura_casos.sql`; `tests/integration/test_qualidade_dados.py:33` | ✅ |
| 3 `store_failures` nos warn | todos | `tests/integration/test_store_failures.py:61` (guarda) e `:46` | ✅ |
| 4 uma linha por teste em `dq_historico_testes` | invocation, nome, status, falhas, severidade, escopo | `tests/integration/test_observabilidade_dq.py:43`, `:57`, `:75` (export ao gold, RBP-12) | ✅ |
| 5 `docs/QUALIDADE_DADOS.md` por etapa, original × adição | catálogo | `tests/integration/test_catalogo_dq.py:28` (bate com o manifesto); `tests/unit/test_gerar_qualidade_dados.py:25` | ✅ |
| 6 CI falha sem `meta.escopo` | falha | `tests/integration/test_escopo_meta.py:75`, `:117` | ✅ |

### P2: Estudo de caso (CASE-01)

| AC | Resultado definido na spec | `file:line` + asserção | Result |
|---|---|---|---|
| 1 `analyses/` por pergunta, vars `caso_*` | 1 SQL por pergunta | `transform/analyses/estudo_caso_*.sql` (10 arquivos); `transform/tests/caso_resolve_um_municipio.sql` | ✅ 📄 |
| 2 `rfb relatorio` escreve o relatório | arquivo com as respostas | `tests/integration/test_relatorio.py:25`, `:40`; real: `docs/RELATORIO_ESTUDO_CASO.md` (2026-09) | ✅ |
| 3 fixtures: 1 ativo, 4 inativos | texto | `tests/unit/test_relatorio.py:51`; `tests/integration/test_relatorio.py:25` | ✅ |

### P1: Operação (OPS-01, OPS-02)

| AC | Resultado definido na spec | `file:line` + asserção | Result |
|---|---|---|---|
| 1 `make ci` completo | **< 120 s** | execução R4: verde em **130,8 s** (`real 2m10.781s`) | ❌ reprovado no texto; o Success Criterion emendado (AD-026, < 180 s) é atendido. Emendar a spec (R4-07) |
| 2 `make pipeline MES=…` | ingest → freshness → build → relatório; ≠ 0 em erro | `tests/unit/test_orquestracao.py:84`, `:104`; real: `EXECUCAO_REAL.md` §1 e `run_results-8x8.json` (ERROR=0) | ✅ |
| 3 `s3://` via httpfs com as 3 variáveis | — | `tests/integration/test_dbt_s3.py:40`; `tests/unit/test_armazenamento.py:196`; `tests/unit/test_relatorio_s3.py:82` | ✅ |
| 4 falta variável com `s3://` | sai ≠ 0 nomeando-as | `tests/unit/test_configuracao.py:62`, `:114`; `tests/integration/test_dbt_s3.py:64` | ✅ |
| 5 `rfb sincronizar` pula objeto idêntico | tamanho + checksum | `tests/unit/test_armazenamento.py:88`, `:112`, `:126`, `:148` | ✅ |
| 6 gold em Parquet sob `RAIZ_DADOS/gold/` | Parquet | `tests/integration/test_atualizar.py:65` (lê `gold/*.parquet`); listagem do gold no CI e no real | ✅ |

### P2: Documentação (DOC-01)

| AC | Resultado definido na spec | Evidência | Result |
|---|---|---|---|
| 1 guia cobre os tópicos listados | 15 conceitos + estrutura, comandos, fluxo, testes, bibliotecas, checks | `docs/guia-dbt/01-fundamentos.md` … `05-boas-praticas-e-usos.md`; revisado na RBP (43 itens corrigidos no FBPg) | ✅ 📄 (ver R4-08: exemplo de `temp_directory` desatualizado) |
| 2 links para arquivos do projeto e docs oficiais | — | script do líder no FBPg: 0 caminhos ausentes (`docs/PLANO.md:116`) | ✅ 📄 |
| 3 `docs/ESCOPO.md` mapeia modelo/check → original/adição | — | `docs/ESCOPO.md`; guarda `tests/integration/test_escopo_meta.py:117` | ✅ 📄 |

### P2: Atualização mensal (UPD-01, UPD-02)

| AC | Resultado definido na spec | `file:line` + asserção | Result |
|---|---|---|---|
| 1 mês novo → ingest/build/relatório + estado em `RAIZ_DADOS/_estado/` | estado gravado | `tests/integration/test_atualizar.py:52`; `tests/unit/test_orquestracao.py:275` | ⚠️ com `s3://` o estado fica em `RAIZ_DADOS_LOCAL`, fora do bucket (R4-06) |
| 2 mesmo mês → exit 0, nada baixado, "nenhum mês novo" | texto e no-op | `tests/integration/test_atualizar.py:59`; `tests/unit/test_orquestracao.py:289`; real: `atualizar-real-noop.log` (exit 0, 0,56 s) | ✅ |
| 3 mês incompleto → anterior completo | mês anterior | `tests/unit/test_orquestracao.py:301`; `tests/unit/test_resolver_mes.py:65` | ✅ |
| 4 falha do dbt → ≠ 0, sem estado | estado intacto | `tests/integration/test_atualizar.py:142`; `tests/unit/test_orquestracao.py:104`, `:317` | ✅ |
| 5 retenção (2 meses) e zips | — | `tests/integration/test_atualizar.py:150`, `:162`; `tests/unit/test_orquestracao.py:358`, `:366` | ✅ (só disco local; R4-06) |
| 6 uma partição por mês, sobrevive ao `.duckdb` | — | `tests/integration/test_resumo_mensal.py:35`, `:88` | ✅ |
| 7 reprocessar substitui só a partição do mês | — | `tests/integration/test_resumo_mensal.py:88` (2026-08 intacta byte a byte; 2026-09 = 16, não 32) | ✅ |
| 8 2026-08 então 2026-09 | Serra/4741500/ATIVA 0 ou ausente em 08, 1 em 09 | `tests/integration/test_resumo_mensal.py:40` | ✅ |
| 9 receitas cron, launchd, GitHub Actions | documentadas | `docs/OPERACAO.md:108-180` | ✅ 📄 |

### P2: Modelo estrela BI (BI-01, BI-02)

| AC | Resultado definido na spec | `file:line` + asserção | Result |
|---|---|---|---|
| 1 `sk_*` inteira, única, não nula e membro −1 | toda dimensão | `tests/integration/test_core.py:79` (parametrizado) | ✅ |
| 2 `dim_data` de 1900 até o máximo, −1 e −2 com datas sentinela | 1899-12-31 / 1899-12-30 | `tests/integration/test_core.py:107`, `:118`, `:127`; dbt unit `_core__models.yml:822` | ✅ |
| 3 fato só com chaves inteiras + `cnpj_completo` | 7 `sk_*` | dbt unit `_core__models.yml:885`; contrato `:459` | ✅ |
| 4 hierarquias de município e CNAE | colunas | contratos `_core__models.yml:63`, `:215`; `tests/integration/test_core.py:57` | ✅ |
| 5 grão e medidas aditivas do resumo | grão sem natureza e ano | `tests/integration/test_resumo_mensal.py:81`, `:58`, `:70`; dbt unit `_core__models.yml:961` | ✅ |
| 6 soma do resumo do mês = count da fato | error | dbt: `transform/tests/fct_resumo_mensal_reconciliacao.sql`; `tests/integration/test_resumo_mensal.py:50` | ✅ |
| 7 `docs/POWER_BI.md` (diagrama, 1:*, conexão, incremental, ≥ 8 DAX) | ≥ 8 medidas | `docs/POWER_BI.md:211-266` (16 medidas DAX) | ✅ 📄 |
| 8 exposure `dashboard` sobre o modelo estrela | depende de todas | `tests/integration/test_resumo_mensal.py:156`; `transform/models/marts/core/_core__exposures.yml:6` | ✅ |

### P2: Enriquecimento Base dos Dados (ENR-01..03)

| AC | Resultado definido na spec | `file:line` + asserção | Result |
|---|---|---|---|
| 1 `downloadTable` com parâmetros base64; sem `one-click-download` | URL | `tests/unit/test_basedosdados.py:51`, `:87` | ✅ |
| 2 3 tabelas novas no raw; `--origem-local` lê de `<origem>/bd/` | raw | `tests/integration/test_ingerir_cli.py:53`; `tests/unit/test_basedosdados.py:108` | ✅ |
| 3 atributos do Censo + RM (`NÃO PERTENCE`/`NÃO INFORMADO`) | valores da fixture | `tests/integration/test_enriquecimento_bd.py:18`, `:28`, `:43` | ✅ |
| 4 vizinhança simétrica, sem autopar, ano mais recente, única e com RI | — | `tests/integration/test_enriquecimento_bd.py:52`, `:62`; dbt: `transform/tests/vizinhanca_simetrica.sql` | ✅ |
| 5 `mart_concorrencia_area_mercado` com indicadores (NULL sem denominador) | valores do cenário | `tests/integration/test_enriquecimento_bd.py:72`, `:85`, `:95` | ✅ |
| 6 relatório com área de mercado | seção | `tests/unit/test_relatorio.py:126`, `:146`, `:153` | ✅ |
| 7 `meta.incremento` + tag, guarda de coerência | falha se divergem | `tests/integration/test_escopo_meta.py:96` | ✅ |
| 8 respostas de Fundão na tabela do cenário e afirmadas | 62,55 hab/km², 0,1489/mil dom., 0,003484/km² | `tests/integration/test_enriquecimento_bd.py:18`, `:72` | ✅ |

### P2: Publicação MotherDuck (PUB-01, PUB-02)

| AC | Resultado definido na spec | `file:line` + asserção | Result |
|---|---|---|---|
| 1 recria uma tabela por dataset do gold e reporta linhas | contagens iguais | `tests/unit/test_publicacao.py:65`; `tests/integration/test_publicar_gold.py:18` (destino DuckDB local) | ⚠️ o caminho `md:` real nunca foi executado (P25: espera OK do usuário) |
| 2 sem variáveis → nada publicado, exit 0 | — | `tests/unit/test_publicacao.py:91`, `:110` | ✅ |
| 3 `--tabelas` e idempotência | substitui | `tests/unit/test_publicacao.py:76`, `:83` | ✅ |
| 4 token nunca em log, arquivo ou commit | — | `tests/unit/test_publicacao.py:135`, `:172`; mutação R4-M10 morta | ✅ |
| 5 `POWER_BI.md` com as opções de acesso | Parquet, ODBC, MotherDuck/PG | `docs/POWER_BI.md` ("Como o Power BI acessa os dados") | ✅ 📄 |

**Status**: ❌ gaps presentes (OPS AC 1) e ⚠️ 6 lacunas de precisão (ING AC 1, SRC AC 3, CORE AC 1, CORE AC 6, UPD AC 1, PUB AC 1).

---

## Edge Cases

- [x] WebDAV fora do ar → ≠ 0 com a URL: `tests/integration/test_ingerir_cli.py:112`
- [x] Falha do download BD → ≠ 0 sem Parquet parcial: `tests/unit/test_basedosdados.py:92`
- [x] Lista de CNAEs secundários vazia → nenhuma linha na bridge: `tests/integration/test_core.py:214`
- [ ] `dat_inicio_atividade` NULL → idade NULL e fora das coortes: só código (`transform/models/marts/analytics/mart_sobrevivencia_coorte.sql:29`, `where ini.sk_data > 0`). Sem fixture nem unit test com início NULL ⚠️
- [x] Município sem população → densidade NULL: `tests/integration/test_analises.py:29`

---

## Success Criteria

| Critério | Evidência | Result |
|---|---|---|
| `make ci` verde em < 180 s com os números do cenário | execução R4: 130,8 s; 240 unit + 114 integração; lint limpo | ✅ |
| `make pipeline MES=2026-09` sem `error` nos dados reais | `run_results-8x8.json`: 339 PASS / 14 WARN / 0 ERROR | ✅ |
| Paridade com diferença zero nos dados reais | `paridade_bh_empresas` failures = 0 em 2026-09 (71,4 M) e fev/2025 (62,6 M) | ✅ |
| Relatório gerado com dados reais de 2026-09 | `docs/RELATORIO_ESTUDO_CASO.md` (mês 2026-09, extrato 2026-09-12); Fundão 0 + 5 conferido no gold real | ✅ |
| Guia revisado por revisor independente sem erros pendentes | RBP revisou; FBPg corrigiu G01–G43 sem nova revisão independente; R4-08 acha uma receita desatualizada | ⚠️ |
| `rfb atualizar` processa mês novo e é no-op sem novidade | no-op real (0,56 s); mês novo só nas fixtures (2026-10 ainda não publicado) | ⚠️ |
| Modelo estrela carregável no Power BI | nenhuma execução no Power BI registrada | ❌ sem evidência |

---

## Discrimination Sensor

Isolamento: `git worktree add --detach <scratch> HEAD` (`e84a0a2`); `git status --porcelain` do worktree
real vazio antes e depois (baseline = vazio). Mutações Python medidas com `pytest` do módulo; mutações dbt
pelo fluxo do `make ci` sem unit e lint (fixtures → pipeline 2026-08 → atualizar → no-op → backfill →
114 testes de integração). Detalhe por mutação em `docs/revisoes/R4.md` (seção Mutações).

| Mutation | File:line | Description | Killed? |
|---|---|---|---|
| M01 | `src/rfb_pipeline/orquestracao.py:312` | backfill `<` → `<=` | ✅ |
| M02 | `src/rfb_pipeline/orquestracao.py:301` | meses sem ordenação | ✅ |
| M03 | `src/rfb_pipeline/orquestracao.py:149` | só código > 1 é falha | ✅ |
| M04 | `src/rfb_pipeline/orquestracao.py:341` | retenção +1 mês | ✅ |
| M05 | `src/rfb_pipeline/orquestracao.py:380` | `atualizar` `<=` → `<` | ✅ |
| M06 | `src/rfb_pipeline/orquestracao.py:245` | backfill sem `RFB_EXTERNAL_ROOT` | ✅ |
| M07 | `src/rfb_pipeline/orquestracao.py:219` | publicação removida | ✅ |
| M08 | `src/rfb_pipeline/orquestracao.py:278` | publica com `s3://` | ✅ |
| M09 | `src/rfb_pipeline/orquestracao.py:351` | ignora `RFB_MANTER_ZIPS` | ✅ |
| M10 | `src/rfb_pipeline/publicacao.py:156` | sem máscara do token | ✅ |
| M11 | `src/rfb_pipeline/publicacao.py:101` | nome de tabela sem validação | ✅ |
| M12 | `src/rfb_pipeline/publicacao.py:103` | sem `hive_partitioning` | ✅ |
| M13 | `src/rfb_pipeline/relatorio.py:117` | relatório s3 sem secret | ✅ |
| M14 | `src/rfb_pipeline/relatorio.py:415` | relatório s3 sem target `s3` | ✅ |
| M15 | `src/rfb_pipeline/relatorio.py:141` | preparo s3 sem máscara | ✅ |
| M16 | `src/rfb_pipeline/conversao.py:234` | fallback UTF-8 nunca acionado | ✅ |
| M17 | `src/rfb_pipeline/conversao.py:295` | relê o CSV original | ✅ |
| M18 | `src/rfb_pipeline/conversao.py:244` | transcodifica como cp1252 | ✅ |
| M19 | `src/rfb_pipeline/conversao.py:299` | não apaga o `.utf8` | equivalente (diretório de extração removido depois) |
| D01 | `transform/macros/staging/empresa_preferida_por_raiz.sql:12` | prefere a linha "fantasma" | ✅ |
| D02 | `transform/models/staging/rfb/stg_rfb__empresas.sql:14` | staging sem dedup | ✅ |
| D03 | `transform/macros/staging/inferschema_inteiro_ou_texto.sql:10` | `bool_and` → `bool_or` | ✅ |
| D04 | `transform/models/marts/core/fct_resumo_mensal.sql:2` | resumo segue o `external_root` (backfill perde a partição) | ❌ Survived → Fix 1 |
| D05 | `transform/tests/fct_resumo_mensal_gold_corrente.sql:27` | teste de gold corrente invertido | ✅ |
| D06 | `transform/macros/observability/registrar_resultados_testes.sql:34` | não exporta o histórico ao gold | ✅ |
| D07 | `transform/macros/gold/raiz_gold.sql:6` | `raiz_gold` segue o `external_root` | ✅ |
| D08 | `transform/models/audit/audit__bh_empresas_sql_original.sql:26` | paridade sem a emulação da dedup | ❌ Survived (cobertura: fixtures sem raiz duplicada; o dado real acusaria na paridade) → Fix 7 |
| D09 | `transform/selectors.yml:14` | backfill sem os pais do resumo | ✅ |

**Sensor depth**: P0 (caminhos críticos: integridade da série, publicação, credenciais) — 28 mutações manuais
**Result**: 25/28 killed (2 survived: D04, D08; 1 equivalente: M19) — FAIL ❌

---

## Code Quality

| Principle | Status |
|---|---|
| Minimum code | ✅ |
| Surgical changes | ✅ (B8 tocou só o necessário para os dados reais; decisões registradas em ESCOPO/EXECUCAO_REAL) |
| No scope creep | ✅ (adições declaradas como `adicao`/`adaptado`) |
| Matches patterns | ✅ |
| Spec-anchored outcome check (asserted values match spec) | ⚠️ 6 lacunas de precisão + OPS AC 1 |
| Per-layer Coverage Expectation met | ⚠️ falta o caso de borda `dat_inicio` NULL na sobrevivência; backfill sem afirmação de regravação (D04) |
| Every test maps to a spec requirement | ✅ (testes de P/R-achados mapeiam para pendências registradas) |
| Documented guidelines followed: `docs/adr/0009-estrategia-testes.md`, `tasks.md` (Gate Check Commands) | ✅ |

---

## Gate Check

- **Gate command**: `make setup && caffeinate -i make ci` (Full/Build gate de `tasks.md:45-46`)
- **Result**: 240 unit passed, 114 integration passed, 0 failed, 0 skipped; `dbt build` 2026-08 e 2026-09 com 311 testes cada (307 aprovados, 4 avisos, 0 erros); backfill 24 nós + 17 testes aprovados; ruff, ruff format e sqlfluff limpos; 130,8 s
- **Test count before feature**: 0 (projeto novo); antes do B8: 208 unit + 105 integração (FBPa)
- **Test count after feature**: 240 unit + 114 integração (+32 / +9 desde o FBPa)
- **Skipped tests**: nenhum
- **Failures**: nenhuma

---

## Fix Plans

### Fix 1: backfill sem afirmação de regravação (D04 sobreviveu)
- **Root cause**: no `make ci`, a partição 2026-08 já existe antes do backfill; `test_atualizar.py:65-79` só checa a existência.
- **Fix task**: no `Makefile` (`ci`), apagar `gold/fct_resumo_mensal/mes_referencia=2026-08` antes do passo de backfill; em `test_ac8_…`, afirmar `sum(qtd_estabelecimentos) = 15` na partição 2026-08 e que a fato detalhada segue com 16.
- **Verify**: a mutação D04 passa a falhar o `make ci`.
- **Priority**: Major

### Fix 2: backfill publica a partição sem gate de qualidade (R4-02)
- **Root cause**: `selectors.yml:6-20` exclui testes dos pais; o COPY grava direto no gold real antes do `dbt test`.
- **Fix task**: build do backfill com os testes de `+fct_resumo_mensal`, partição gravada na raiz temporária e movida ao gold (`rename`) só após sucesso.
- **Verify**: teste de integração em que um teste error do staging falha no backfill e a partição do gold fica intacta.
- **Priority**: Major

### Fix 3: gold misto após falha do build corrente (R4-03)
- **Fix task**: marcador `_estado/em_andamento.json` (relatório e publicação recusam) e documentação no `OPERACAO.md`; idealmente build numa raiz temporária com troca atômica; publicação em transação.
- **Priority**: Major

### Fix 4: CPF no `nome` do gold (R4-01)
- **Fix task**: decisão do usuário (ADR-0008 emendado): mascarar o sufixo de CPF em `bh_empresas`/`mart_fornecedores_proximos` como adaptação declarada, com teste error, ou aceitar o risco e excluir `bh_empresas` da publicação padrão.
- **Priority**: Major

### Fix 5: spec e tarefas desatualizadas (R4-07)
- **Fix task**: emendar OPS AC 1 (180 s), CORE AC 1 e BI (16), CORE AC 6 ({A, O, C}), ING AC 1 (mais recente completo); marcar `tasks.md:956`, `:974`; atualizar a rastreabilidade (tabela abaixo).
- **Priority**: Minor

### Fix 7: dedup de raiz sem exercício nas fixtures (D08 sobreviveu)
- **Fix task**: acrescentar às fixtures (`scripts/gerar_fixtures.py`) uma linha "fantasma" duplicando a raiz de um estabelecimento existente (sem razão social, natureza 0000), sem mudar as respostas da spec; teste de integração afirmando uma linha por raiz em `stg_rfb__empresas` e a paridade verde.
- **Verify**: D08 passa a falhar o `make ci`.
- **Priority**: Minor

### Fix 6: caso de borda sem teste
- **Fix task**: unit test de `mart_sobrevivencia_coorte` com estabelecimento sem `dat_inicio_atividade` (fora de toda coorte).
- **Priority**: Minor

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
|---|---|---|
| ING-01 | In Tasks | ⚠️ Verified (spec AC 1 a emendar) |
| ING-02 .. ING-06 | In Tasks | ✅ Verified |
| SRC-01 | In Tasks | ✅ Verified (AC 3 com check do raw em warn; R4-05) |
| STG-01 | In Tasks | ✅ Verified |
| ORI-01 .. ORI-03 | In Tasks | ✅ Verified |
| CORE-01 | In Tasks | ⚠️ Verified (spec AC 1 e 6 a emendar) |
| ANA-01 .. ANA-04 | In Tasks | ✅ Verified |
| DQ-01, DQ-02 | In Tasks | ✅ Verified |
| CASE-01 | In Tasks | ✅ Verified |
| OPS-01 | In Tasks | ❌ Needs Fix (AC 1: 130,8 s > 120 s; emendar para 180 s) |
| OPS-02 | In Tasks | ✅ Verified |
| DOC-01 | In Tasks | ✅ Verified (R4-08: receita de `temp_directory`) |
| UPD-01 | In Tasks | ⚠️ Verified (modo s3: estado e retenção locais, R4-06) |
| UPD-02 | In Tasks | ❌ Needs Fix (D04: regravação do backfill não afirmada; R4-02) |
| BI-01, BI-02 | In Tasks | ✅ Verified |
| ENR-01 .. ENR-03 | In Tasks | ✅ Verified |
| PUB-01 | In Tasks | ⚠️ Verified (só destino local; MotherDuck real pendente de OK, P25; R4-01) |
| PUB-02 | In Tasks | ✅ Verified |

---

## Summary

**Overall**: ⚠️ Issues

**Spec-anchored check**: 100/107 ACs batem com o resultado da spec; 6 lacunas de precisão; 1 reprovado no texto (OPS AC 1). 107/107 com evidência citável.
**Sensor**: 25/28 killed (sobreviventes D04 e D08; M19 equivalente)
**Gate**: 240 unit + 114 integração passed, 0 failed; `make ci` 130,8 s

**What works**: ingestão real e idempotente; paridade 0 nos dois meses reais; orquestração com ordem, backfill e no-op provados por mutação; publicação e relatório s3 sem vazamento de segredo; fallback UTF-8 e deduplicação de raiz cobertos.

**Issues found**: D04 sobrevivente (Fix 1); D08 sobrevivente (Fix 7); backfill sem gate (Fix 2); gold misto em falha (Fix 3); CPF no gold (Fix 4); spec desatualizada (Fix 5).

**Next steps**: Fix 1–3 por agente novo no nível do B8 (Claude Opus médio); Fix 4 depende de decisão do usuário; Fix 5 pelo líder. Depois, reverificação (máximo de 3 iterações).
