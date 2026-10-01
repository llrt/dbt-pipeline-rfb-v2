# Guia dbt — Parte 3: Qualidade Antes e Depois por Etapa

> **Público-alvo:** engenheiro(a) de dados e analytics engineers desenhando suítes de testes defensivas e confiáveis.
> Este documento detalha a matriz prática de **Pré-condições ("Antes")** e **Pós-condições ("Depois")** implementada em cada fase deste pipeline, com referências exatas aos arquivos de código do projeto.
>
> **Parte 3 de 5** — ver também `01-fundamentos.md`, `02-fluxo-e-testes.md`, `04-bibliotecas-e-tecnicas.md` e `05-boas-praticas-e-usos.md`.

---

## Sumário

- [1. Filosofia: Por que Validar Antes e Depois?](#1-filosofia-por-que-validar-antes-e-depois)
- [2. Matriz Antes × Depois por Etapa do Pipeline](#2-matriz-antes--depois-por-etapa-do-pipeline)
  - [2.1 Ingestão e EL Python](#21-ingestão-e-el-python)
  - [2.2 Fontes Raw (Entrada do dbt)](#22-fontes-raw-entrada-do-dbt)
  - [2.3 Camada Staging (Views 1:1)](#23-camada-staging-views-11)
  - [2.4 Camada Intermediate (Tabelas Físicas)](#24-camada-intermediate-tabelas-físicas)
  - [2.5 Camada Marts Original (bh_empresas e agg_empresas)](#25-camada-marts-original-bh_empresas-e-agg_empresas)
  - [2.6 Camada Marts Core (Modelo Estrela Kimball)](#26-camada-marts-core-modelo-estrela-kimball)
  - [2.7 Camada Marts Analytics (Indicadores de Negócio)](#27-camada-marts-analytics-indicadores-de-negócio)
  - [2.8 Camada Gold e Consumo Power BI](#28-camada-gold-e-consumo-power-bi)
  - [2.9 Rotina de Atualização Mensal](#29-rotina-de-atualização-mensal)
- [3. Padrões Gerais de Data Quality](#3-padrões-gerais-de-data-quality)
  - [3.1 Reconciliação e Conservação de Massa](#31-reconciliação-e-conservação-de-massa)
  - [3.2 Data Diff e Paridade Estrita](#32-data-diff-e-paridade-estrita)
  - [3.3 Quarentena e store_failures](#33-quarentena-e-store_failures)
  - [3.4 Testes de Mutação (Mutation Testing)](#34-testes-de-mutação-mutation-testing)
  - [3.5 O Princípio "Shift-Left" na Engenharia de Dados](#35-o-princípio-shift-left-na-engenharia-de-dados)
- [4. Checklist Copiável de Qualidade](#4-checklist-copiável-de-qualidade)

---

## 1. Filosofia: Por que Validar Antes e Depois?

Em pipelines analíticos tradicionais, é comum encontrar validações apenas no final do processo (relatórios ou dashboards que quebram quando um usuário final percebe um valor nulo ou contagem zerada). Essa abordagem "tardia" é frágil, cara de corrigir e corrompe a confiança nos dados.

Neste projeto, adotamos uma abordagem de **design por contrato**:
- **Antes (Pré-condições)**: O que precisa ser comprovadamente verdadeiro **antes** de executar uma etapa. Se a pré-condição falhar, a transformação sequer deve iniciar. Isso previne que dados corrompidos se propaguem para a linhagem downstream (evitando poluição do warehouse e consumo inútil de computação).
- **Depois (Pós-condições)**: O que precisa ser garantido **após** a conclusão da transformação. Se a pós-condição falhar, o artefato gerado não pode ser publicado para consumo e o pipeline é abortado.

### Severidades no Pipeline
- **`error`**: Violação de integridade crítica (ex.: duplicação de chave primária, drop não intencional de linhas, tipos incompatíveis). Aborta o build imediatamente (`fail-fast`).
- **`warn`**: Anomalia documentada ou limitação conhecida da fonte pública (ex.: CNPJ ativo com dígito verificador incorreto, datas arcaicas). Registra a anomalia em `dq_historico_testes` e persiste as linhas com falha em tabelas de auditoria sem interromper a carga.

---

## 2. Matriz Antes × Depois por Etapa do Pipeline

### 2.1 Ingestão e EL Python

Responsável por extrair zips da Receita Federal e CSVs da Base dos Dados e convertê-los para Parquet bruto.

| Momento | O que valida | Ferramenta | Severidade | Arquivo Implementador |
|---|---|---|---|---|
| **Antes** | Existência do diretório/mês no WebDAV remoto | Python PROPFIND (`ClienteRFB.listar_meses`) | `error` | `src/rfb_pipeline/cliente_rfb.py` (L284) e `src/rfb_pipeline/erros.py` (L12, `MesInexistenteErro`) |
| **Antes** | Tamanho anunciado (`getcontentlength`) no XML PROPFIND | Python XML parsing (`ClienteRFB.listar_arquivos`) | `error` | `src/rfb_pipeline/cliente_rfb.py` (L303) |
| **Antes** | Ausência de path traversal (`..`, `/` absoluto) no ZIP | Python (`extrair_zip_seguro` / `_entrada_insegura`) | `error` | `src/rfb_pipeline/conversao.py` (L79) e `src/rfb_pipeline/erros.py` (L77, `ZipInseguroErro`) |
| **Antes** | Integridade estrutural do arquivo ZIP baixado | Python (extração com captura de `zipfile.BadZipFile`/`zlib.error`; sem `testzip` separado) | `error` | `src/rfb_pipeline/conversao.py` (L115) e `src/rfb_pipeline/erros.py` (L86, `ZipCorrompidoErro`) |
| **Antes** | Bloqueio de arquivos pessoais (`Socios*`) e colunas LGPD | Python (`ClienteRFB.listar_arquivos` e `src/rfb_pipeline/esquemas.py`) | `error` | `src/rfb_pipeline/cliente_rfb.py` (L318) e `src/rfb_pipeline/esquemas.py` (L114) |
| **Depois** | Tamanho baixado confere com o anunciado pelo WebDAV | Python (`baixar_com_retentativas`) | `error` | `src/rfb_pipeline/cliente_rfb.py` (L242) e `src/rfb_pipeline/erros.py` (L59, `TamanhoDivergenteErro`) |
| **Depois** | Hash SHA-256 gravado no manifesto atômico do mês | Python (`sha256_arquivo` / `escrever_manifesto`) | `error` | `src/rfb_pipeline/manifesto.py` (L38, L141) |
| **Depois** | Taxa de rejeito de linhas CSV ≤ limite configurado | Python (`converter_entidade_rfb`) | `error` | `src/rfb_pipeline/conversao.py` (L375) e `src/rfb_pipeline/erros.py` (L94, `TaxaRejeitoExcedidaErro`) |
| **Depois** | Contagem total de linhas gravadas > 0 (não vazia) | Python (`converter_entidade_rfb`) | `error` | `src/rfb_pipeline/conversao.py` (L379) e `tests/integration/test_ingerir_cli.py` |
| **Depois** | Download atômico (`.part` → rename) e Parquet atômico | Python (`Path.replace` e `_publicar`) | `error` | `src/rfb_pipeline/cliente_rfb.py` (L244) e `src/rfb_pipeline/conversao.py` (L169) |

---

### 2.2 Fontes Raw (Entrada do dbt)

Garante que os arquivos Parquet brutos em `dados/raw/` atendem aos requisitos estruturais antes que qualquer view de staging seja compilada.

| Momento | O que valida | Ferramenta | Severidade | Arquivo Implementador |
|---|---|---|---|---|
| **Antes** | Unicidade de CNPJ raiz + mês em empresas | dbt test genérico (`unique_combination_of_columns`) | `error` | `transform/models/staging/rfb/_rfb__sources.yml` |
| **Antes** | Unicidade de CNPJ completo + mês em estabelecimentos | dbt test genérico (`unique_combination_of_columns`) | `error` | `transform/models/staging/rfb/_rfb__sources.yml` |
| **Antes** | Não-nulo no campo de data de referência (`_data_referencia`) | dbt test genérico (`not_null`) | `error` | `transform/models/staging/rfb/_rfb__sources.yml` |
| **Antes** | Valores de domínio de porte bruto (`00`, `01`, `03`, `05`) | dbt test genérico (`accepted_values`) | `error` | `transform/models/staging/rfb/_rfb__sources.yml` |
| **Antes** | Valores de situação cadastral bruta (`01` a `08`) | dbt test genérico (`accepted_values`) | `error` | `transform/models/staging/rfb/_rfb__sources.yml` |
| **Antes** | Códigos de município RFB sem par na Base dos Dados | dbt test singular | `error` | `transform/tests/cobertura_municipio_rfb_bd.sql` |
| **Antes** | Unicidade de município + ano em PIB e População | dbt test genérico (`unique_combination_of_columns`) | `error` | `transform/models/staging/basedosdados/_bd__sources.yml` |
| **Depois** | Frescor da ingestão (último lote há menos de 35 dias) | dbt CLI (`dbt source freshness`) | `warn` / `error` | `transform/models/staging/rfb/_rfb__sources.yml` |

---

### 2.3 Camada Staging (Views 1:1)

Limpeza de strings, preenchimento de zeros à esquerda (`lpad`) e tipagem estrita de colunas.

| Momento | O que valida | Ferramenta | Severidade | Arquivo Implementador |
|---|---|---|---|---|
| **Antes** | Fontes raw disponíveis e resolvidas no catálogo DuckDB | dbt engine (`source()`) | `error` | `transform/models/staging/rfb/stg_rfb__*.sql` |
| **Depois** | Unicidade e não-nulo de `cnpj_completo` (14 dígitos) | dbt test (`unique`, `not_null`) | `error` | `transform/models/staging/rfb/_rfb__staging.yml` |
| **Depois** | Comprimento exato de 14 dígitos no CNPJ completo | Macro customizada (`tamanho_exato`) | `error` | `transform/models/staging/rfb/_rfb__staging.yml` |
| **Depois** | Dígito verificador do CNPJ (Módulo 11 da RFB) | Macro customizada (`cnpj_dv_valido`) | `warn` | `transform/models/staging/rfb/_rfb__staging.yml` |
| **Depois** | Comprimento exato de 8 dígitos no CNPJ raiz | Macro customizada (`tamanho_exato`) | `error` | `transform/models/staging/rfb/_rfb__staging.yml` |
| **Depois** | Comprimento exato de 7 dígitos no CNAE principal | Macro customizada (`tamanho_exato`) | `error` | `transform/models/staging/rfb/_rfb__staging.yml` |
| **Depois** | Comprimento exato de 4 dígitos no código do município | Macro customizada (`tamanho_exato`) | `error` | `transform/models/staging/rfb/_rfb__staging.yml` |
| **Depois** | Data de início de atividade não futura | Macro customizada (`data_nao_futura`) | `warn` | `transform/models/staging/rfb/_rfb__staging.yml` |
| **Depois** | Data de início de atividade ≥ 1900-01-01 (datas anteriores viram `sk = -2` na fato) | dbt_utils (`accepted_range`) | `warn` | `transform/models/staging/rfb/_rfb__staging.yml` |
| **Depois** | Datas de exclusão/opção do Simples não futuras | Macro customizada (`data_nao_futura`) | `warn` | `transform/models/staging/rfb/_rfb__staging.yml` |
| **Depois** | Ausência total de colunas de contato ou pessoais (LGPD) | dbt test singular | `error` | `transform/tests/sem_colunas_de_contato.sql` |
| **Depois** | Unit tests de lpad, nulos e parse com dados mockados | dbt unit tests (`format: sql`) | `error` | `transform/models/staging/rfb/_rfb__staging.yml` |

---

### 2.4 Camada Intermediate (Tabelas Físicas)

Enriquecimento entre estabelecimentos, empresas, Simples e dados geográficos dos municípios.

| Momento | O que valida | Ferramenta | Severidade | Arquivo Implementador |
|---|---|---|---|---|
| **Antes** | Views de staging compiladas e validadas | dbt DAG (`ref()`) | `error` | `transform/models/intermediate/*.sql` |
| **Depois** | Unicidade de `cnpj_completo` na base enriquecida | dbt test (`unique`) | `error` | `transform/models/marts/core/_core__models.yml` |
| **Depois** | Não-nulo de `cnpj_completo` | dbt test (`not_null`) | `error` | `transform/models/marts/core/_core__models.yml` |
| **Depois** | Integridade referencial do código matriz/filial | dbt test (`relationships`) | `error` | `transform/models/marts/core/_core__models.yml` |
| **Depois** | Unicidade da chave composta de CNAEs explodidos | dbt_utils (`unique_combination_of_columns`) | `error` | `transform/models/marts/core/_core__models.yml` |
| **Depois** | Unicidade e não-nulo da surrogate key de município | dbt test (`unique`, `not_null`) | `error` | `transform/models/marts/core/_core__models.yml` |
| **Depois** | Unicidade do código RFB de município | dbt test (`unique`) | `warn` | `transform/models/marts/core/_core__models.yml` |
| **Depois** | Unit test de conservação de massa (flags e zero descartes) | dbt unit test (`test_int_estabelecimentos_enriquecidos_flags_e_nada_descartado`) | `error` | `transform/models/marts/core/_core__models.yml` |
| **Depois** | Unit test de explosão de CNAEs secundários (unnest) | dbt unit test (`test_int_cnaes_secundarios_explodidos`) | `error` | `transform/models/marts/core/_core__models.yml` |
| **Depois** | Unit tests de resolução de ano mais recente e variável de população | dbt unit tests (`test_int_municipios_conformados_*`) | `error` | `transform/models/marts/core/_core__models.yml` |

---

### 2.5 Camada Marts Original (`bh_empresas` e `agg_empresas`)

Reprodução das regras de negócio do MVP original com verificação de paridade estrita.

| Momento | O que valida | Ferramenta | Severidade | Arquivo Implementador |
|---|---|---|---|---|
| **Antes** | Tabelas intermediárias enriquecidas e conformadas | dbt DAG (`ref()`) | `error` | `transform/models/marts/original/*.sql` |
| **Antes** | Validação de tipos do contrato durante DDL | dbt contracts (`contract.enforced: true`) | `error` | `transform/models/marts/original/_original__models.yml` |
| **Depois** | Paridade linha a linha (com multiplicidade) vs. Spark via `EXCEPT ALL` | dbt test singular | `error` | `transform/tests/paridade_bh_empresas.sql` |
| **Depois** | Quantificação e monitoramento dos descartes por `INNER JOIN` | dbt test singular | `warn` | `transform/tests/bh_empresas_descartes_inner_join.sql` |
| **Depois** | Reconciliação: soma de `qtd_empresas` em `agg_empresas` == total em `bh_empresas` | dbt test singular | `error` | `transform/tests/agg_empresas_reconciliacao.sql` |
| **Depois** | Faixa aceitável de idade calculada (entre 0 e 200 anos): avisa com qualquer violação e falha acima de 100 linhas (`warn_if: "!=0"`, `error_if: ">100"`, `store_failures`) | dbt_utils (`accepted_range`) | `warn` / `error` | `transform/models/marts/original/_original__models.yml` |
| **Depois** | Categorias canônicas de porte (`N/A`, `MICRO`, `PEQUENA`, `DEMAIS`) | dbt test (`accepted_values`) | `error` | `transform/models/marts/original/_original__models.yml` |
| **Depois** | Situação cadastral binária (`ATIVA`, `INATIVA`) | dbt test (`accepted_values`) | `error` | `transform/models/marts/original/_original__models.yml` |
| **Depois** | Efeito colateral do `trim` de nomes na paridade | dbt test singular | `warn` | `transform/tests/bh_empresas_nome_alterado_por_trim.sql` |
| **Depois** | Unit tests de porte, idade determinística e agrupamentos | dbt unit tests | `error` | `transform/models/marts/original/_original__models.yml` |

---

### 2.6 Camada Marts Core (Modelo Estrela Kimball)

Garante que o data warehouse corporativo preserve 100% dos dados para BI e analytics governado.

| Momento | O que valida | Ferramenta | Severidade | Arquivo Implementador |
|---|---|---|---|---|
| **Antes** | Dimensões contêm membro sentinela `-1` ("NÃO INFORMADO") e `-2` ("DATA INVÁLIDA", após F3a) | dbt unit tests | `error` | `transform/models/marts/core/_core__models.yml` |
| **Antes** | Calendário cobre rigorosamente o mês de referência sem lacunas | dbt test singular | `error` | `transform/tests/dim_data_cobre_data_referencia.sql` |
| **Depois** | Conservação de linhas: `count(fato)` == `count(staging)` (zero descartes) | dbt test singular | `error` | `transform/tests/fct_estabelecimentos_reconciliacao.sql` |
| **Depois** | Chaves `-1` na fato batem exatamente com as flags `tem_* = false` | dbt test singular | `error` | `transform/tests/fct_estabelecimentos_reconciliacao.sql` |
| **Depois** | Integridade referencial: `fct_estabelecimentos.sk_cnae` → `dim_cnae.sk_cnae` | dbt test (`relationships`) | `error` | `transform/models/marts/core/_core__models.yml` |
| **Depois** | Integridade referencial: `fct_estabelecimentos.sk_municipio` → `dim_municipio.sk_municipio` | dbt test (`relationships`) | `error` | `transform/models/marts/core/_core__models.yml` |
| **Depois** | Integridade referencial: `fct_estabelecimentos.sk_porte` → `dim_porte.sk_porte` | dbt test (`relationships`) | `error` | `transform/models/marts/core/_core__models.yml` |
| **Depois** | Integridade referencial: `fct_estabelecimentos.sk_natureza_juridica` → dimensão | dbt test (`relationships`) | `error` | `transform/models/marts/core/_core__models.yml` |
| **Depois** | Integridade referencial: datas de abertura e situação → `dim_data.sk_data` | dbt test (`relationships`) | `error` | `transform/models/marts/core/_core__models.yml` |
| **Depois** | Reconciliação da fato agregada mensal contra a fato granular | dbt test singular | `error` | `transform/tests/fct_resumo_mensal_reconciliacao.sql` |
| **Depois** | Unicidade da chave primária composta na tabela de resumo mensal | dbt_utils (`unique_combination_of_columns`) | `error` | `transform/models/marts/core/_core__models.yml` |
| **Depois** | Integridade referencial bidirecional na tabela ponte (bridge) de CNAEs | dbt test (`relationships`) | `error` | `transform/models/marts/core/_core__models.yml` |
| **Depois** | Contratos de schema ativos em todas as dimensões e fatos | dbt contracts (`contract.enforced: true`) | `error` | `transform/models/marts/core/_core__models.yml` |

---

### 2.7 Camada Marts Analytics (Indicadores de Negócio)

Validações estatísticas, numéricas e invariantes de regras de negócio.

| Momento | O que valida | Ferramenta | Severidade | Arquivo Implementador |
|---|---|---|---|---|
| **Antes** | Fato e dimensões core materializadas e testadas | dbt DAG (`ref()`) | `error` | `transform/models/marts/analytics/*.sql` |
| **Depois** | Invariante matemática de sobrevivência: $S_{5a} \le S_{3a} \le S_{1a}$ | dbt test singular | `error` | `transform/tests/sobrevivencia_invariantes.sql` |
| **Depois** | Distâncias geodésicas (Haversine) são não-negativas e plausíveis | dbt test singular | `error` | `transform/tests/distancias_fornecedores_validas.sql` |
| **Depois** | Via de fornecimento aceita exclusivamente `principal` ou `secundario` | dbt test (`accepted_values`) | `error` | `transform/models/marts/analytics/_analytics__models.yml` |
| **Depois** | Densidade de concorrência por 10k habitantes não-negativa | dbt_utils (`accepted_range`) | `error` | `transform/models/marts/analytics/_analytics__models.yml` |
| **Depois** | Unicidade por município + CNAE alvo no mart de concorrência | dbt_utils (`unique_combination_of_columns`) | `error` | `transform/models/marts/analytics/_analytics__models.yml` |
| **Depois** | Unicidade de CNPJ no mart de fornecedores mapeados | dbt test (`unique`) | `error` | `transform/models/marts/analytics/_analytics__models.yml` |
| **Depois** | Saldo anual de dinâmica = `aberturas - encerramentos` | dbt test singular | `error` | `transform/models/marts/analytics/_analytics__models.yml` |
| **Depois** | Unit tests de cálculo geodésico Haversine e coortes de sobrevivência | dbt unit tests | `error` | `transform/models/marts/analytics/_analytics__models.yml` |

---

### 2.8 Camada Gold e Consumo Power BI

Garantias físicas de entrega e integridade para as ferramentas de visualização.

| Momento | O que valida | Ferramenta | Severidade | Arquivo Implementador |
|---|---|---|---|---|
| **Antes** | Criação prévia do diretório físico de destino (`mkdir -p $(RAIZ_DADOS)/gold`) | Makefile / Python | `error` | `Makefile` (alvos `ci` e `lint`) |
| **Antes** | Permissão de escrita e memória disponível no DuckDB | DuckDB engine | `error` | `transform/profiles.yml` |
| **Depois** | Arquivos Parquet gravados com sucesso sem corrupção | Python (`duckdb.read_parquet`) | `error` | `tests/integration/test_bh_empresas.py` e `tests/integration/test_core.py` |
| **Depois** | Tipos de data compatíveis com Power BI (coluna de data contínua sem vazios) | dbt test / contrato | `error` | `transform/models/marts/core/_core__models.yml` |
| **Depois** | Mapeamento explícito de dependências downstream (exposures) | dbt exposures | `error` | `transform/models/marts/core/_core__exposures.yml` |

---

### 2.9 Rotina de Atualização Mensal

Garante a estabilidade e o comportamento determinístico entre cargas de meses subsequentes.

| Momento | O que valida | Ferramenta | Severidade | Arquivo Implementador |
|---|---|---|---|---|
| **Antes** | Verificação de disponibilidade e completude do novo mês no WebDAV | Python (`esquemas.arquivos_faltantes`) | `error` | `src/rfb_pipeline/cli.py` e `src/rfb_pipeline/esquemas.py` (`MesIncompletoErro`) |
| **Antes** | Detecção de execução no-op (se hash do lote for idêntico ao já processado) | Python (`precisa_reconverter`) | `error` | `src/rfb_pipeline/manifesto.py` (L175) |
| **Antes** | Lote parcial/incompleto é ignorado a menos que explicitamente autorizado | Python (`--permitir-incompleto`) | `error` | `src/rfb_pipeline/cli.py` |
| **Depois** | Ordem estrita de compilação: mês antigo materializado antes do novo (P22) | Python / Makefile | `error` | `Makefile` e `src/rfb_pipeline/cli.py` |
| **Depois** | Gravação atômica do manifesto do novo mês | Python (`escrever_manifesto`) | `error` | `src/rfb_pipeline/manifesto.py` (L141) |
| **Depois** | Política de retenção de meses históricos respeitada | Python (`pathlib`) | `error` | `src/rfb_pipeline/cli.py` |
| **Depois** | Registro da execução gravado em `dq_historico_testes` via hook `on-run-end` | dbt macro (`registrar_resultados_testes`) | `error` | `transform/macros/observability/registrar_resultados_testes.sql` |

---

## 3. Padrões Gerais de Data Quality

### 3.1 Reconciliação e Conservação de Massa

Em engenharia de dados corporativa, a **reconciliação** assegura que nenhum registro seja inadvertidamente criado ou descartado ao longo de sucessivos joins e filtros.

Neste projeto, implementamos testes singulares de conservação:
1. **Reconciliação de Contagem (`transform/tests/fct_estabelecimentos_reconciliacao.sql`)**:
   Verifica se `SELECT count(*) FROM fct_estabelecimentos` coincide perfeitamente com `stg_rfb__estabelecimentos`. Se houver 1 estabelecimento a mais ou a menos, o teste aponta a violação.
2. **Reconciliação Financeira (`transform/tests/fct_resumo_mensal_reconciliacao.sql`)**:
   Garante que as métricas agregadas da fato mensal (estabelecimentos, ativos e capital social) coincidam com as somas da base granular de estabelecimentos.
3. **Reconciliação de Agregações (`transform/tests/agg_empresas_reconciliacao.sql`)**:
   Garante que a soma das contagens agrupadas por município e situação bata exatamente com a contagem da base analítica granular `bh_empresas`.

---

### 3.2 Data Diff e Paridade Estrita

Quando se refatora um pipeline analítico legado (como a migração de PySpark para dbt + DuckDB realizada neste projeto), a técnica recomendada é o **Data Diff** (diferença estrita de dados).

O teste singular `transform/tests/paridade_bh_empresas.sql` compara `bh_empresas` com a tradução literal do SQL do notebook 3 (`audit__bh_empresas_sql_original`) usando `EXCEPT ALL` nos dois sentidos sobre `(cnpj_completo, hash(*columns(*)))` — o hash de cada linha inteira, função nativa do DuckDB:
```sql
with bh as (
  select cnpj_completo, hash(*columns(*)) as hash_linha from {{ ref('bh_empresas') }}
),
original as (
  select cnpj_completo, hash(*columns(*)) as hash_linha
  from {{ ref('audit__bh_empresas_sql_original') }}
),
somente_bh as (select * from bh except all select * from original),
somente_original as (select * from original except all select * from bh)
-- o select final devolve o lado ('bh' ou 'original') e o cnpj_completo de cada divergência
```
Comparar o hash em vez das 15 colunas dá o mesmo resultado e foi ~3,4× mais rápido no dado real (R2-12).
Se a consulta retornar qualquer linha, significa que há linhas sobrando em um dos lados ou campos com divergência de cálculo. Este teste garantiu 100% de paridade sobre 62,6 milhões de registros reais da RFB no extrato de fev/2025.

---

### 3.3 Quarentena e `store_failures`

A abordagem ingênua de abortar o pipeline para qualquer imperfeição pode paralisar a empresa por anomalias triviais em cadastros públicos legados (como um estabelecimento aberto em 1970 com CEP ou CNPJ DV com erro de digitação original).

Nossa arquitetura resolve isso com **quarentena seletiva**:
1. O teste de dados é configurado como `severity: warn` e `store_failures: true`.
2. Ao rodar `dbt build`, o teste emite um aviso no console e grava as linhas que violaram a regra física em uma tabela dedicada no schema `main_dbt_test__audit` (ex.: `cnpj_dv_valido_stg_rfb__estabelecimentos_cnpj_completo`).
3. O pipeline principal segue para as camadas downstream sem ser bloqueado.
4. Engenheiros de dados e analistas podem consultar as tabelas de auditoria para diagnóstico, relatórios de governança ou comunicação com a área de negócios.

---

### 3.4 Testes de Mutação (Mutation Testing)

Como saber se os seus testes de qualidade são realmente eficazes ou se estão passando apenas porque foram escritos de forma frouxa?

No processo de revisão deste projeto ([ADR-0011](../../docs/adr/0011-processo-equipe-agentes.md)), adotamos **testes de mutação**:
1. O revisor introduz deliberadamente um defeito no SQL (um "mutante"), como alterar um `LEFT JOIN` para `INNER JOIN`, inverter um operador `>`, ou trocar um membro sentinela `-1` por `NULL`.
2. Executa-se a suíte de testes (`dbt test`).
3. **Critério de eficácia**: O mutante **deve ser capturado** (o teste correspondente deve falhar). Se todos os testes passarem mesmo com o mutante ativo, o teste é considerado deficiente e deve ser reescrito com asserções mais estritas.

---

### 3.5 O Princípio "Shift-Left" na Engenharia de Dados

O princípio de **Shift-Left** preconiza antecipar a detecção de erros para o momento mais inicial possível do ciclo de vida dos dados:

```
[ Ingestão Python ]  --->  [ Staging ]  --->  [ Intermediate ]  --->  [ Marts Gold ]
       |                         |                    |                     |
  (Tipagem raw,             (Tamanho fixo,       (Zero descartes,       (Invariantes,
   LGPD, hashes)              Módulo 11)           chaves -1)            contratos)
       |                         |                    |                     |
       +-------------------------+--------------------+---------------------+
                                 Detectar e barrar AQUI
```

Em vez de descobrir que um código de município possui 5 dígitos na hora de gerar o dashboard no Power BI, barramos a anomalia já no teste `tamanho_exato` do staging. Isso reduz o custo de depuração em ordens de magnitude.

---

## 4. Checklist Copiável de Qualidade

Ao criar um novo modelo no dbt para este ou novos projetos, utilize este checklist de garantia de qualidade:

```markdown
### Checklist de Qualidade para Novos Modelos dbt

#### 1. Camada Staging
- [ ] O modelo lê de uma única fonte (zero joins)?
- [ ] Chaves textuais usam preenchimento com zeros à esquerda (`lpad_codigo`)?
- [ ] Strings vazias são normalizadas para `NULL` (`texto_ou_nulo`)?
- [ ] Chave primária possui testes `not_null` e `unique`?
- [ ] Códigos de domínio possuem teste `tamanho_exato`?
- [ ] Datas possuem teste `data_nao_futura`?
- [ ] Dados sensíveis/pessoais foram descartados (LGPD)?
- [ ] Possui ao menos um unit test cobrindo regras de negócio com `format: sql`?

#### 2. Camada Intermediate
- [ ] Joins foram desenhados como `LEFT JOIN` para evitar descartes silenciosos de registros?
- [ ] Foram criadas flags diagnósticas (`tem_*`) para monitorar entidades órfãs?
- [ ] Unicidade da chave primária (simples ou composta) foi mantida após os joins?

#### 3. Camada Marts (Core / Dimensional)
- [ ] O modelo possui contrato ativado (`contract.enforced: true`) com tipos declarados?
- [ ] Registros órfãos foram tratados com membro sentinela `-1` ("NÃO INFORMADO")?
- [ ] Todas as chaves estrangeiras possuem testes de `relationships` apontando para as dimensões?
- [ ] Existe teste de reconciliação de volume contra a camada staging (`count(*)`)?
- [ ] Metadados de governança (`meta.escopo` e `tags`) foram declarados no YAML?
- [ ] O modelo foi documentado com `description` a nível de tabela e coluna?
```
