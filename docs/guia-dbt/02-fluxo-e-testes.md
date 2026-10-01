# Guia dbt — Parte 2: Fluxo de Dados e Testes

> **Público-alvo:** engenheiro(a) de dados aprendendo dbt e arquiteturas modernas de analytics engineering.
> Todos os exemplos de código SQL compilado, fixtures e contagens de linhas foram extraídos **diretamente deste repositório** (executados com DuckDB 1.5 e dbt-core 1.12).
>
> **Parte 2 de 5** — ver também `01-fundamentos.md`, `03-qualidade-antes-e-depois.md`, `04-bibliotecas-e-tecnicas.md` e `05-boas-praticas-e-usos.md`.

---

## Sumário

- [1. Visão Geral do Fluxo de Dados](#1-visão-geral-do-fluxo-de-dados)
- [2. O Fluxo Camada por Camada com SQL Compilado e Contagens Reais](#2-o-fluxo-camada-por-camada-com-sql-compilado-e-contagens-reais)
  - [2.1 Camada Raw (Ingestão Python)](#21-camada-raw-ingestão-python)
  - [2.2 Camada Staging (Views 1:1, Limpeza e Tipagem)](#22-camada-staging-views-11-limpeza-e-tipagem)
  - [2.3 Camada Intermediate (Tabelas Físicas e Enriquecimento)](#23-camada-intermediate-tabelas-físicas-e-enriquecimento)
  - [2.4 Camada Marts Original (Paridade com o MVP Spark)](#24-camada-marts-original-paridade-com-o-mvp-spark)
  - [2.5 Camada Marts Core (Modelo Estrela Dimensional Kimball)](#25-camada-marts-core-modelo-estrela-dimensional-kimball)
  - [2.6 Camada Marts Analytics (Estudos de Caso e Inteligência)](#26-camada-marts-analytics-estudos-de-caso-e-inteligência)
  - [2.7 Auditoria e Observabilidade](#27-auditoria-e-observabilidade)
- [3. Anatomia Completa dos Testes no dbt](#3-anatomia-completa-dos-testes-no-dbt)
  - [3.1 Testes Genéricos e Validações de Domínio](#31-testes-genéricos-e-validações-de-domínio)
  - [3.2 Testes Singulares (SQL Puro)](#32-testes-singulares-sql-puro)
  - [3.3 Severidade, Limiares (warn_if/error_if) e store_failures](#33-severidade-limiares-warn_iferror_if-e-store_failures)
  - [3.4 Unit Tests com format: sql sobre Fontes Externas (P8)](#34-unit-tests-com-format-sql-sobre-fontes-externas-p8)
  - [3.5 Contratos de Esquema (Model Contracts)](#35-contratos-de-esquema-model-contracts)
  - [3.6 Testes de Freshness (Atualidade das Fontes)](#36-testes-de-freshness-atualidade-das-fontes)
  - [3.7 Testes de Reconciliação e Paridade](#37-testes-de-reconciliação-e-paridade)

---

## 1. Visão Geral do Fluxo de Dados

O pipeline implementa o padrão **Medalhão (Bronze/Raw → Silver/Staging & Intermediate → Gold/Marts)** em combinação com a modelagem dimensional **Kimball** (Fatos e Dimensões) sobre arquivos Parquet e DuckDB local ou remoto (ADR-0001, ADR-0007, ADR-0013).

Abaixo, a comparação de volume real nas **fixtures sintéticas** (geradas por `make fixtures` em `tests/fixtures/generated/`, e executadas no pipeline de validação `make ci` sob `.tmp/ci/fixtures/` para o mês de teste `2026-09`):

| Camada | Modelo/Tabela | Materialização | Linhas (CI) | Papel no Pipeline |
|---|---|---|---|---|
| **Raw (Fontes)** | `source('rfb', 'estabelecimentos')` | Parquet externo | 15 | Extrato bruto all-VARCHAR |
| **Raw (Fontes)** | `source('rfb', 'empresas')` | Parquet externo | 14 | Razão social, porte e capital social |
| **Raw (Fontes)** | `source('rfb', 'simples')` | Parquet externo | 14 | Opções Simples Nacional e MEI |
| **Raw (Fontes)** | `source('rfb', 'cnaes')` | Parquet externo | 8 | Tabela de domínio CNAE da RFB |
| **Raw (Fontes)** | `source('rfb', 'municipios')` | Parquet externo | 10 | Tabela de municípios da RFB |
| **Raw (Fontes)** | `source('rfb', 'naturezas')` | Parquet externo | 5 | Naturezas jurídicas da RFB |
| **Raw (Fontes)** | `source('basedosdados', 'municipio')` | Parquet externo | 8 | Diretórios IBGE, UF e coordenadas |
| **Raw (Fontes)** | `source('basedosdados', 'cnae_2')` | Parquet externo | 7 | Hierarquia CNAE da Base dos Dados |
| **Seeds** | `dominio_porte`, `dominio_situacao_cadastral`, etc. | Tabela física | 2 a 5 | Domínios estáticos versionados em CSV |
| **Staging** | `stg_rfb__estabelecimentos` | View | 15 | Limpeza, tipagem e lpad (sem joins) |
| **Staging** | `stg_rfb__empresas` | View | 14 | Filtro do mês e conversão de capital |
| **Intermediate** | `int_municipios__conformados` | Table | 8 | Join RFB + IBGE com centróides geodésicos |
| **Intermediate** | `int_estabelecimentos__enriquecidos` | Table | 15 | Left join amplo com flags `tem_*` (zero descartes) |
| **Intermediate** | `int_cnaes_secundarios__explodidos` | Table | 2 | Unnest de CNAEs secundários por CNPJ |
| **Marts Original** | `bh_empresas` | External (Parquet) | 12 | **Notebook 3**: 3 descartados pelos inner joins |
| **Marts Original** | `agg_empresas` | External (Parquet) | 12 | Agregações do caso de uso de tintas |
| **Marts Core** | `dim_cnae` | External (Parquet) | 8 | 7 subclasses BD + membro `-1` ("NÃO INFORMADO") |
| **Marts Core** | `dim_municipio` | External (Parquet) | 9 | 8 municípios conformados + membro `-1` |
| **Marts Core** | `dim_data` | External (Parquet) | 9.753 | Calendário contínuo com atributos em português |
| **Marts Core** | `dim_porte`, `dim_situacao_cadastral` | External (Parquet) | 5 e 6 | Domínios do negócio + membro `-1` |
| **Marts Core** | `fct_estabelecimentos` | External (Parquet) | 15 | Fato granular: **100% conservada** (zero descartes) |
| **Marts Core** | `fct_resumo_mensal` | External (Parquet) | 29 | Fato agregada mensal para Power BI |
| **Marts Core** | `bridge_estabelecimento_cnae_secundario`| External (Parquet) | 2 | Tabela ponte para relacionamentos N:N |
| **Marts Analytics**| `mart_concorrencia_municipio` | External (Parquet) | 10 | Densidade de mercado por 10k habitantes |
| **Marts Analytics**| `mart_fornecedores_proximos` | External (Parquet) | 2 | Distância geodésica (Haversine) |
| **Marts Analytics**| `mart_sobrevivencia_coorte` | External (Parquet) | 15 | Sobrevivência de coortes em 1, 3 e 5 anos |
| **Marts Analytics**| `mart_dinamica_mercado` | External (Parquet) | 20 | Aberturas, encerramentos e saldos |
| **Auditoria** | `audit__bh_empresas_sql_original` | Ephemeral (CTE) | — | Tradução literal PySpark para teste de paridade |
| **Observabilidade**| `dq_historico_testes` | Table (Hook) | 242 | Histórico cumulativo de testes no CI |

---

## 2. O Fluxo Camada por Camada com SQL Compilado e Contagens Reais

### 2.1 Camada Raw (Ingestão Python)

- **O que entra**: Arquivos ZIP do WebDAV oficial da Receita Federal (`Estabelecimentos*.zip`, `Empresas*.zip`, `Simples.zip`, tabelas de domínio) e arquivos `csv.gz` da Base dos Dados no Google Cloud Storage (diretórios de municípios, CNAEs, PIB e população).
- **Como é processado**: O módulo Python `src/rfb_pipeline/` faz streaming da rede e converte os dados diretamente para Parquet particionado sob a pasta `dados/raw/` (ou bucket S3/Tigris).
- **Decisões arquiteturais fundamentais (ADR-0002, ADR-0008)**:
  - **All-VARCHAR**: Para evitar descartes silenciosos ou conversões corrompidas durante o carregamento de CSVs legados, todas as colunas de dados são gravadas como texto puro (`VARCHAR`). A tipagem forte e higienização são delegadas integralmente à camada de transformação dbt.
  - **Minimização de Dados Pessoais (LGPD)**: Arquivos de Sócios (`Socios*.zip`) e colunas com nomes de pessoas físicas ou dados de contato são descartados no momento da ingestão e jamais entram no warehouse. O teste singular `transform/tests/sem_colunas_de_contato.sql` valida continuamente essa barreira.
  - **Metadados Técnicos**: A ingestão anexa quatro colunas de rastreabilidade a cada linha: `_arquivo_origem`, `_mes_referencia`, `_data_referencia` e `_ingerido_em`.
- **Contagem nas fixtures**: 15 estabelecimentos e 14 empresas no extrato de `2026-09`.

---

### 2.2 Camada Staging (Views 1:1, Limpeza e Tipagem)

- **Responsabilidade**: Limpeza de caracteres, padronização de zeros à esquerda (`lpad`), conversão de tipos estritos (`DATE`, `INTEGER`, `DECIMAL`) e filtro de partição do mês.
- **Regra de ouro dbt**: **Zero Joins**. Cada modelo staging lê exclusivamente uma tabela da fonte correspondente (`1:1`).
- **Materialização**: `view` (custo computacional zero de armazenamento; executada sob demanda pelo DuckDB).
- **Arquivo de origem**: `transform/models/staging/rfb/stg_rfb__estabelecimentos.sql`.

#### Exemplo Real de SQL Compilado (`stg_rfb__estabelecimentos`)
Localizado em `transform/target/compiled/rfb/models/staging/rfb/stg_rfb__estabelecimentos.sql`:

```sql
with fonte as (
  select * from read_parquet(
    '/Users/llrt/.../dados/raw/rfb/estabelecimentos/mes_referencia=*/*.parquet',
    hive_partitioning=false
  )
  where _mes_referencia = (
    select max(_mes_referencia) from read_parquet(
      '/Users/llrt/.../dados/raw/rfb/estabelecimentos/mes_referencia=*/*.parquet',
      hive_partitioning=false
    )
  )
)

select
  lpad(cnpj_raiz, 8, '0') as cnpj_raiz,
  concat(
    lpad(cnpj_raiz, 8, '0'),
    lpad(cnpj_ordem, 4, '0'),
    lpad(cnpj_dv, 2, '0')
  ) as cnpj_completo,
  try_cast(matriz_filial as integer) as matriz_filial_codigo,
  case when trim(nome_fantasia) = '' then null else trim(nome_fantasia) end as nome_fantasia,
  try_cast(situacao_cadastral as integer) as situacao_codigo,
  case
    when data_situacao_cadastral is null or trim(data_situacao_cadastral) in ('', '0', '00000000') then null
    else try_strptime(trim(data_situacao_cadastral), '%Y%m%d')::date
  end as dat_situacao,
  case
    when data_inicio_atividade is null or trim(data_inicio_atividade) in ('', '0', '00000000') then null
    else try_strptime(trim(data_inicio_atividade), '%Y%m%d')::date
  end as dat_inicio_atividade,
  lpad(cnae_fiscal_principal, 7, '0') as cnae_principal,
  case when trim(cnae_fiscal_secundaria) = '' then null else trim(cnae_fiscal_secundaria) end as cnaes_secundarios,
  str_split(cnae_fiscal_secundaria, ',') as cnaes_secundarios_lista,
  lpad(municipio, 4, '0') as municipio_rfb_codigo,
  _mes_referencia,
  _data_referencia
from fonte
```

- **Contagem nas fixtures**: 15 registros preservados integralmente. Nenhuma linha é filtrada na camada Staging.

---

### 2.3 Camada Intermediate (Tabelas Físicas e Enriquecimento)

- **Responsabilidade**: Realizar os joins entre entidades, combinar fontes heterogêneas (RFB com Base dos Dados) e normalizar atributos multivalorados (como a lista de CNAEs secundários).
- **Materialização**: `table` física no arquivo `warehouse.duckdb`. Isso permite que modelos pesados de marts leiam o resultado intermediário pronto sem recalcular os mesmos joins repetidamente.
- **Modelos implementados**:
  1. `int_municipios__conformados`: Faz o crosswalk entre o código de 4 dígitos da Receita Federal e o ID IBGE de 7 dígitos, adicionando dados de PIB, população e centróides geodésicos (`st_point(longitude, latitude)`).
  2. `int_estabelecimentos__enriquecidos`: Combina os dados de estabelecimentos com os dados da empresa matriz (`stg_rfb__empresas`), regime tributário (`stg_rfb__simples`) e domínios de referência.
  3. `int_cnaes_secundarios__explodidos`: Aplica a função `unnest(cnaes_secundarios_lista)` para transformar a string separada por vírgulas em linhas individuais com unicidade `(cnpj_completo, codigo_cnae_secundario)`.

#### Decisão Crucial: Left Joins com Flags (Zero Descartes)
Diferente da lógica dos notebooks legados, `int_estabelecimentos__enriquecidos` não utiliza `INNER JOIN`. Ela executa `LEFT JOIN` e gera flags booleanas de diagnóstico:
- `tem_empresa`: indica se o estabelecimento encontrou seu par cadastral em empresas.
- `tem_natureza`: se a natureza jurídica informada existe na tabela oficial.
- `tem_cnae_bd`: se o código CNAE existe na taxonomia da Base dos Dados.
- `tem_municipio_bd`: se o município RFB mapeou para um município IBGE válido.

- **Contagens nas fixtures**:
  - `int_estabelecimentos__enriquecidos`: 15 linhas (100% dos estabelecimentos mantidos).
  - `int_municipios__conformados`: 8 municípios conformados.
  - `int_cnaes_secundarios__explodidos`: 2 linhas explodidas.

---

### 2.4 Camada Marts Original (Paridade com o MVP Spark)

- **Responsabilidade**: Entregar a reprodução estrita das regras dos notebooks Databricks/Spark de origem (Notebook 3: flat table `bh_empresas`; Notebook 4: agregações `agg_empresas`).
- **Materialização**: `external` (`gold/bh_empresas.parquet` e `gold/agg_empresas.parquet`).
- **O Fenômeno dos Descartes Silenciosos (Inner Joins Legados)**:
  O código PySpark original realizava `INNER JOIN` entre estabelecimentos e as tabelas de domínio. Se um estabelecimento possuía um município antigo sem correspondente na Base dos Dados ou código com digitação inválida, **o registro era simplesmente descartado** da base final sem qualquer aviso.

#### Exemplo Real de SQL Compilado (`bh_empresas`)
Localizado em `transform/target/compiled/rfb/models/marts/original/bh_empresas.sql`:

```sql
with estabelecimentos as (
  select * from "warehouse"."main"."stg_rfb__estabelecimentos"
),
empresas as (
  select * from "warehouse"."main"."stg_rfb__empresas"
),
naturezas as (
  select * from "warehouse"."main"."stg_rfb__naturezas"
),
cnaes_bd as (
  select * from "warehouse"."main"."stg_bd__cnaes"
),
municipios_bd as (
  select * from "warehouse"."main"."stg_bd__municipios"
)

select
  est.cnpj_raiz,
  est.cnpj_completo,
  upper(coalesce(est.nome_fantasia, emp.razao_social)) as nome,
  upper(nat.descricao) as natureza_juridica,
  case emp.porte_codigo
    when 0 then 'N/A'
    when 1 then 'MICRO'
    when 3 then 'PEQUENA'
    when 5 then 'DEMAIS'
  end as porte,
  est.cnae_principal,
  upper(cnae.descricao_subclasse) as desc_cnae_principal,
  upper(cnae.descricao_grupo) as grupo_cnae_principal,
  est.cnaes_secundarios,
  upper(mun.nome) as municipio,
  upper(mun.nome_microrregiao) as microrregiao_municipio,
  upper(mun.nome_mesorregiao) as mesorregiao_municipio,
  upper(mun.sigla_uf) as uf,
  case est.situacao_codigo when 2 then 'ATIVA' else 'INATIVA' end as situacao,
  case est.situacao_codigo
    when 2
      then round(
        datediff(
          'day', est.dat_inicio_atividade,
          (select max(_data_referencia) from "warehouse"."main"."stg_rfb__estabelecimentos")
        ) / 365.25,
        1
      )
  end as idade_atual
from empresas as emp
inner join estabelecimentos as est on emp.cnpj_raiz = est.cnpj_raiz
inner join naturezas as nat on emp.natureza_juridica_codigo = nat.codigo
inner join cnaes_bd as cnae on est.cnae_principal = cnae.subclasse
inner join municipios_bd as mun on est.municipio_rfb_codigo = mun.id_municipio_rf
```

- **Contagem nas fixtures**: De 15 estabelecimentos originais, **apenas 12 linhas chegam em `bh_empresas`**. Três estabelecimentos foram descartados pelos inner joins devido à falta de correspondência exata nos domínios. Esse comportamento é monitorado e alertado pelo teste singular `transform/tests/bh_empresas_descartes_inner_join.sql`.

---

### 2.5 Camada Marts Core (Modelo Estrela Dimensional Kimball)

- **Responsabilidade**: Modelagem dimensional corporativa voltada para ferramentas analíticas de BI (Power BI, Tableau, DuckDB CLI), seguindo rigorosamente as boas práticas de Kimball ([ADR-0013](../../docs/adr/0013-modelo-estrela-bi.md)).
- **Materialização**: `external` em arquivos Parquet individuais em `gold/`.
- **Arquitetura Estrela**:
  - **Dimensões Conformadas**: `dim_municipio`, `dim_cnae`, `dim_data`, `dim_natureza_juridica`, `dim_porte`, `dim_situacao_cadastral`.
  - **Tabela Fato Granular**: `fct_estabelecimentos` (1 linha por CNPJ completo de 14 dígitos).
  - **Tabela Fato Agregada Mensal**: `fct_resumo_mensal` (série histórica pronta para carregamento ultrarrápido em modo Import no Power BI).
  - **Tabela Ponte (Bridge)**: `bridge_estabelecimento_cnae_secundario` (permite relacionar as dimensões CNAE com os múltiplos CNAEs secundários de cada empresa sem desnormalizar a fato).

#### Padrão de Chave Surrogada Inteira e Resolução do Membro `-1`
Para assegurar integridade referencial estrita e desempenho máximo em ferramentas analíticas, todas as dimensões utilizam **chaves inteiras (BIGINT/INTEGER)** e incluem explicitamente o membro sentinela:
- `sk = -1`: **"NÃO INFORMADO"** (quando um estabelecimento não possui município ou CNAE válido).
- `sk = -2`: **"DATA INVÁLIDA"** *(após F3a)* para datas anteriores a 1900 encontradas em extratos antigos da RFB (ex.: anos 1194, 1601).

Na tabela fato `fct_estabelecimentos`:
```sql
coalesce(mun.sk_municipio, -1) as sk_municipio,
coalesce(cnae.sk_cnae, -1) as sk_cnae,
coalesce(nat.sk_natureza_juridica, -1) as sk_natureza_juridica,
coalesce(por.sk_porte, -1) as sk_porte,
coalesce(sit.sk_situacao_cadastral, -1) as sk_situacao_cadastral
```
Graças a essa técnica, **a tabela fato preserva 100% dos 15 estabelecimentos das fixtures** (zero perda de dados), garantindo reconciliação perfeita contra o extrato bruto.

---

### 2.6 Camada Marts Analytics (Estudos de Caso e Inteligência)

- **Responsabilidade**: Modelos analíticos de valor agregado que respondem diretamente às perguntas de negócio do estudo de caso de tintas no município de Fundão/ES:
  1. `mart_concorrencia_municipio`: Densidade competitiva (empresas ativas e inativas por 10 mil habitantes, agrupadas por município e porte).
  2. `mart_fornecedores_proximos`: Análise geoespacial que calcula a distância em quilômetros via fórmula de **Haversine** entre o centróide de Fundão e todos os potenciais fornecedores (fabricantes e atacadistas de tintas) na mesorregião e microrregião.
  3. `mart_sobrevivencia_coorte`: Análise de sobrevivência empresarial por coorte de abertura (taxa de sobrevivência após 1, 3 e 5 anos para empresas do setor).
  4. `mart_dinamica_mercado`: Série histórica de aberturas, encerramentos e saldo líquido anual de empresas ativas.

#### Trecho Compilado de Haversine (`mart_fornecedores_proximos`)
```sql
round(
  2 * 6371.0 * asin(sqrt(
    power(sin(radians(abs(forn.latitude - fundao.latitude)) / 2), 2) +
    cos(radians(fundao.latitude)) *
    cos(radians(forn.latitude)) *
    power(sin(radians(abs(forn.longitude - fundao.longitude)) / 2), 2)
  )),
  2
) as distancia_km
```

- **Contagens nas fixtures**:
  - `mart_concorrencia_municipio`: 10 linhas.
  - `mart_fornecedores_proximos`: 2 fornecedores mapeados no raio definido.
  - `mart_sobrevivencia_coorte`: 15 linhas de coortes.
  - `mart_dinamica_mercado`: 20 linhas de evolução anual.

---

### 2.7 Auditoria e Observabilidade

- **`models/audit/audit__bh_empresas_sql_original.sql`**: Materializado como `ephemeral`. É uma tradução estrita e literal do SQL do notebook Spark para DuckDB, servindo de gabarito contra o qual o modelo refatorado `bh_empresas` é testado via `EXCEPT ALL`.
- **`dq_historico_testes`**: Tabela acumulativa mantida no banco `warehouse.duckdb`. A cada execução de `dbt test` ou `dbt build`, o hook `on-run-end` extrai o status de cada teste e insere uma linha com `invocation_id`, nome do nó, severidade, contagem de falhas e tempo de execução.
- **`models/observability/dq_resumo_execucao.sql`**: View agregada que sumariza as taxas de sucesso e avisos por execução dbt.

---

## 3. Anatomia Completa dos Testes no dbt

O dbt trata a qualidade de dados como um cidadão de primeira classe. Neste projeto, a estratégia de testes ([ADR-0009](../../docs/adr/0009-estrategia-testes.md) e [QUALIDADE_DADOS.md](../QUALIDADE_DADOS.md)) combina 189 data tests automatizados e 33 unit tests cobrindo desde regras de formatação até integridade financeira e geoespacial.

### 3.1 Testes Genéricos e Validações de Domínio

Testes genéricos são asserções reutilizáveis parametrizadas diretamente nos arquivos YAML (`models/**/*.yml`). O dbt compila cada asserção em uma consulta SQL que seleciona os registros violadores. **Se a consulta retornar qualquer registro, o teste falha.**

#### 1. Testes Nativos do dbt Core
- **`not_null`**: Garante ausência de nulos em colunas obrigatórias ou chaves surrogadas.
- **`unique`**: Valida a unicidade da chave primária (ex.: `cnpj_completo`).
- **`accepted_values`**: Assegura que os valores pertençam a uma lista fechada (ex.: situação cadastral ∈ `['1', '2', '3', '4', '8']`).
- **`relationships`**: Valida integridade referencial entre modelos (ex.: toda `sk_cnae` em `fct_estabelecimentos` deve existir em `dim_cnae`).

#### 2. Testes Avançados de Pacotes (`dbt_utils` e `dbt_expectations`)
Exemplos reais extraídos de `transform/models/marts/core/_core__models.yml` e `transform/models/marts/original/_original__models.yml`:

```yaml
# transform/models/marts/core/_core__models.yml (int_cnaes_secundarios__explodidos)
# Garante unicidade da chave composta na tabela explodida
- name: int_cnaes_secundarios__explodidos
  data_tests:
    - dbt_utils.unique_combination_of_columns:
        combination_of_columns:
          - cnpj_completo
          - codigo_cnae_secundario

# transform/models/marts/original/_original__models.yml (bh_empresas)
# Valida intervalo aceitável de idade (0 a 200 anos): avisa com qualquer violação, falha acima de 100
- name: bh_empresas
  columns:
    - name: idade_atual
      data_tests:
        - dbt_utils.accepted_range:
            arguments:
              min_value: 0
              max_value: 200
            config:
              warn_if: "!=0"
              error_if: ">100"
              store_failures: true
```

#### 3. Testes Customizados de Domínio Brasileiro (`transform/macros/`)
O projeto implementa testes customizados via macros Jinja que são invocados de forma declarativa nos YAMLs:
- **`tamanho_exato(tamanho)`**: Garante que códigos textuais tenham tamanho fixo (ex.: CNPJ raiz com 8 dígitos, CNAE com 7 dígitos).
- **`cnpj_dv_valido()`**: Aplica o algoritmo de Módulo 11 da Receita Federal sobre os 12 primeiros dígitos e valida se os dígitos verificadores (DV) batem com os 2 últimos dígitos.
- **`data_nao_futura()`**: Garante que datas de abertura ou situação não sejam posteriores à data do extrato (`_data_referencia`).

---

### 3.2 Testes Singulares (SQL Puro)

Testes singulares são arquivos `.sql` independentes localizados em `transform/tests/`. Eles são ideais para validações de regras de negócio complexas, joins multi-tabelas ou reconciliações contábeis.

**Contrato**: O SQL de um teste singular deve ser uma query que retorne as **linhas que violam a regra**. Se retornar 0 linhas, o teste passa (PASS); se retornar ≥ 1 linha, o teste falha (FAIL ou WARN).

#### Exemplo 1: Teste de Paridade com EXCEPT ALL (`transform/tests/paridade_bh_empresas.sql`)
Valida se a tabela refatorada `bh_empresas` é 100% idêntica, linha por linha (com multiplicidade), à execução literal do SQL do notebook original:

```sql
with bh as (
  select cnpj_completo, hash(*columns(*)) as hash_linha from {{ ref('bh_empresas') }}
),
original as (
  select cnpj_completo, hash(*columns(*)) as hash_linha from {{ ref('audit__bh_empresas_sql_original') }}
),
somente_bh as (
  select * from bh except all select * from original
),
somente_original as (
  select * from original except all select * from bh
)

select 'somente_bh_empresas' as lado, cnpj_completo, hash_linha from somente_bh
union all
select 'somente_sql_original' as lado, cnpj_completo, hash_linha from somente_original
```

#### Exemplo 2: Reconciliação Fato vs. Staging (`transform/tests/fct_estabelecimentos_reconciliacao.sql`)
Garante que a tabela fato preserve exatamente a mesma contagem de estabelecimentos do staging e que as chaves `-1` correspondam perfeitamente às flags `tem_*` do intermediate:

```sql
with fato as (
  select
    count(*) as linhas,
    count(*) filter (where sk_municipio = -1) as sem_municipio,
    count(*) filter (where sk_cnae = -1) as sem_cnae,
    count(*) filter (where sk_natureza_juridica = -1) as sem_natureza
  from {{ ref('fct_estabelecimentos') }}
),
staging as (
  select count(*) as linhas from {{ ref('stg_rfb__estabelecimentos') }}
),
flags as (
  select
    count(*) filter (where not tem_municipio_bd) as sem_municipio,
    count(*) filter (where not tem_cnae_bd) as sem_cnae,
    count(*) filter (where not tem_natureza) as sem_natureza
  from {{ ref('int_estabelecimentos__enriquecidos') }}
)

select 'linhas da fato != linhas do staging' as violacao, fato.linhas as na_fato, staging.linhas as esperado
from fato cross join staging where fato.linhas != staging.linhas
union all
select 'sk_municipio = -1 != sem município BD', fato.sem_municipio, flags.sem_municipio
from fato cross join flags where fato.sem_municipio != flags.sem_municipio
```

---

### 3.3 Severidade, Limiares (`warn_if`/`error_if`) e `store_failures`

Por padrão, qualquer linha retornada por um teste no dbt resulta em erro (`ERROR`) e aborta o pipeline. No entanto, certas regras são informativas ou toleram pequenas anomalias conhecidas dos dados públicos.

#### Configuração de Severidade e Limiares
```yaml
- name: cnpj_completo
  data_tests:
    - cnpj_dv_valido:
        config:
          severity: warn              # Não quebra o pipeline; emite apenas WARNING
          warn_if: "> 0"
          error_if: "> 10"            # Quebra apenas se ultrapassar 10 ocorrências
```

> **A Armadilha de Configuração (`severity: warn` vs. `error_if`)**:
> No dbt Core, a diretiva `severity: warn` define o teto da severidade do teste. Se um teste estiver explicitamente configurado com `severity: warn`, **o dbt ignora qualquer bloco `error_if`**! O teste jamais produzirá status de `ERROR`, emitindo no máximo `WARN` independentemente da contagem de linhas retornadas. Para ter comportamento duplo (avisar em pequenas quantidades e falhar em grandes), configure `severity: error` e combine `warn_if: "> 0"` com `error_if: "> 10"`.

#### Armazenamento de Linhas com Falha (`store_failures`)
Ao executar testes com a flag `--store-failures` (ou configurar `store_failures: true` no YAML), o dbt cria tabelas físicas sob o schema de auditoria `main_dbt_test__audit` contendo exatamente os registros que violaram a regra.

Para inspecionar as falhas diretamente pelo DuckDB:
```sql
-- Consultar os CNPJs com dígito verificador inválido que dispararam aviso:
SELECT * FROM "warehouse"."main_dbt_test__audit"."cnpj_dv_valido_stg_rfb__estabelecimentos_cnpj_completo";

-- Consultar os 3 estabelecimentos descartados pelos inner joins originais:
SELECT * FROM "warehouse"."main_dbt_test__audit"."bh_empresas_descartes_inner_join";
```

---

### 3.4 Unit Tests com `format: sql` sobre Fontes Externas (P8)

Unit tests permitem testar a lógica pura de um modelo fornecendo dados de mock controlados antes que o modelo seja executado contra a base de dados real.

No entanto, no ecossistema **dbt-duckdb**, ocorre uma particularidade técnica crítica com fontes `source()` que utilizam `external_location` (arquivos Parquet apontados por `read_parquet(...)`):

#### O Problema da Introspecção de Schema
Ao declarar dados de mock usando dicionários YAML (`rows:` com pares chave-valor):
```yaml
# FORMA INCORRETA (FALHA EM DUCKDB COM EXTERNAL_LOCATION):
given:
  - input: source('rfb', 'cnaes')
    rows:
      - {codigo: "0111301", descricao: "Cultivo de arroz"}
```
O dbt tenta introspeccionar o catálogo do banco para descobrir os tipos de dados das colunas da fonte a fim de fazer o casting correto dos valores do dicionário. Como a fonte é um arquivo Parquet externo e ainda não existe uma tabela relacional criada no catálogo do DuckDB, **o teste falha com erro de compilação**.

#### A Solução Oficial: `format: sql` (P8)
Para contornar essa limitação e viabilizar unit tests determinísticos, declara-se `format: sql` e fornece-se uma consulta `SELECT ... UNION ALL` literal com os tipos explícitos:

```yaml
# transform/models/staging/rfb/_rfb__staging.yml
unit_tests:
  - name: test_stg_rfb__cnaes_lpad_e_texto_vazio
    description: "`lpad_codigo` preenche até 7 dígitos; `texto_ou_nulo` converte descrição vazia em NULL."
    model: stg_rfb__cnaes
    given:
      - input: source('rfb', 'cnaes')
        format: sql
        rows: |
          select '111301' as codigo, 'Cultivo de arroz' as descricao, '2026-09' as _mes_referencia
          union all
          select '4741500' as codigo, '' as descricao, '2026-09' as _mes_referencia
    expect:
      rows:
        - { codigo: "0111301", descricao: "Cultivo de arroz" }
        - { codigo: "4741500", descricao: null }
```

Executando apenas os testes unitários:
```bash
uv run dbt test --select "test_type:unit"
```

---

### 3.5 Contratos de Esquema (Model Contracts)

Enquanto data tests verificam a qualidade dos **dados**, contratos garantem a integridade da **estrutura** (nomes, ordens e tipos das colunas).

Com `contract: {enforced: true}` no modelo, o dbt valida durante a compilação e criação física se a consulta SQL produz rigorosamente as colunas contratadas:

```yaml
# transform/models/marts/original/_original__models.yml
models:
  - name: bh_empresas
    config:
      contract:
        enforced: true
    columns:
      - name: cnpj_raiz
        data_type: varchar
      - name: cnpj_completo
        data_type: varchar
      - name: nome
        data_type: varchar
      - name: natureza_juridica
        data_type: varchar
      - name: porte
        data_type: varchar
      - name: cnae_principal
        data_type: varchar
      - name: desc_cnae_principal
        data_type: varchar
      - name: grupo_cnae_principal
        data_type: varchar
      - name: cnaes_secundarios
        data_type: varchar
      - name: municipio
        data_type: varchar
      - name: microrregiao_municipio
        data_type: varchar
      - name: mesorregiao_municipio
        data_type: varchar
      - name: uf
        data_type: varchar
      - name: situacao
        data_type: varchar
      - name: idade_atual
        data_type: double precision
```

Se um desenvolvedor renomear `idade_atual` para `idade` ou alterar o tipo para `integer`, o build falha imediatamente com uma mensagem detalhada de violação de contrato antes de persistir o arquivo em disco.

---

### 3.6 Testes de Freshness (Atualidade das Fontes)

Garantem que os dados brutos depositados pelo módulo de ingestão não estejam obsoletos antes do processamento das transformações analíticas:

```yaml
# transform/models/staging/rfb/_rfb__sources.yml
sources:
  - name: rfb
    loaded_at_field: _ingerido_em
    freshness:
      warn_after: {count: 35, period: day}
      error_after: {count: 65, period: day}
```

Execução dedicada:
```bash
uv run dbt source freshness
```
Gera o artefato `target/sources.json` detalhando a data do último lote carregado versus a data corrente.

---

### 3.7 Testes de Reconciliação e Paridade

Garantem a confiabilidade corporativa entre todas as camadas do warehouse:

| Categoria | Teste Real no Projeto | O que assegura |
|---|---|---|
| **Paridade Estrita** | `transform/tests/paridade_bh_empresas.sql` | `bh_empresas` possui exatamente as mesmas linhas da tradução PySpark original |
| **Conservação de Linhas** | `transform/tests/fct_estabelecimentos_reconciliacao.sql` | `count(*)` de `fct_estabelecimentos` == `count(*)` de `stg_rfb__estabelecimentos` |
| **Reconciliação de Agregações** | `transform/tests/agg_empresas_reconciliacao.sql` | Soma de empresas em `agg_empresas` bate com a soma de registros de `bh_empresas` |
| **Integridade de Coortes** | `transform/tests/sobrevivencia_invariantes.sql` | Taxa de sobrevivência de 5 anos é sempre ≤ taxa de 3 anos e ≤ taxa de 1 ano |
| **Cobertura Geográfica** | `transform/tests/cobertura_municipio_rfb_bd.sql` | Municípios presentes no cadastro RFB possuem correspondente no IBGE/BD |
