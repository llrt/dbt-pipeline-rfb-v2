# Guia dbt — Parte 4: Bibliotecas, Ferramentas e Técnicas Avançadas

> **Público-alvo:** engenheiro(a) de dados buscando dominar o ecossistema estendido do dbt, pacotes da comunidade e técnicas avançadas de operação.
> Cada ferramenta é analisada sob a ótica prática: o que é, quando usar, exemplo de sintaxe e status de adoção neste projeto.
>
> **Parte 4 de 5** — ver também `01-fundamentos.md`, `02-fluxo-e-testes.md`, `03-qualidade-antes-e-depois.md` e `05-boas-praticas-e-usos.md`.

---

## Sumário

- [1. Panorama do Ecossistema dbt](#1-panorama-do-ecossistema-dbt)
- [2. Pacotes dbt (dbt Packages)](#2-pacotes-dbt-dbt-packages)
  - [2.1 dbt_utils](#21-dbt_utils)
  - [2.2 dbt_expectations](#22-dbt_expectations)
  - [2.3 dbt-audit-helper](#23-dbt-audit-helper)
  - [2.4 Elementary](#24-elementary)
  - [2.5 dbt-project-evaluator](#25-dbt-project-evaluator)
  - [2.6 codegen](#26-codegen)
- [3. Qualidade de Código e Alternativas de Observabilidade](#3-qualidade-de-código-e-alternativas-de-observabilidade)
  - [3.1 sqlfluff e dbt-templater](#31-sqlfluff-e-dbt-templater)
  - [3.2 dbt-checkpoint (Git Pre-commit Hooks)](#32-dbt-checkpoint-git-pre-commit-hooks)
  - [3.3 Alternativas: Great Expectations, Soda Core e re_data](#33-alternativas-great-expectations-soda-core-e-re_data)
- [4. Recursos Avançados do dbt-duckdb](#4-recursos-avançados-do-dbt-duckdb)
  - [4.1 Materialização external e external_location](#41-materialização-external-e-external_location)
  - [4.2 Extensões e Conectividade (httpfs, s3, spatial)](#42-extensões-e-conectividade-httpfs-s3-spatial)
- [5. Técnicas Avançadas de Engenharia de Dados](#5-técnicas-avançadas-de-engenharia-de-dados)
  - [5.1 Modelos Incrementais e Estratégias de Carga](#51-modelos-incrementais-e-estratégias-de-carga)
  - [5.2 Snapshots (SCD Tipo 2)](#52-snapshots-scd-tipo-2)
  - [5.3 CI Slim com state:modified e --defer](#53-ci-slim-com-statemodified-e---defer)
  - [5.4 Produtividade Operacional: dbt retry e dbt clone](#54-produtividade-operacional-dbt-retry-e-dbt-clone)
  - [5.5 Data Diff (Auditoria Semântica de Migração)](#55-data-diff-auditoria-semântica-de-migração)
- [6. Matriz de Adoção de Ferramentas no Projeto](#6-matriz-de-adoção-de-ferramentas-no-projeto)

---

## 1. Panorama do Ecossistema dbt

O dbt Core fornece o motor essencial de compilação de SQL e orquestração do DAG. No entanto, o verdadeiro poder da engenharia analítica moderna reside no **ecossistema de pacotes e ferramentas satélites** mantidos pela dbt Labs e pela comunidade open-source no [dbt Hub](https://hub.getdbt.com/).

Um projeto maduro combina:
1. **Packages de macros e testes**: ampliam o vocabulário analítico do YAML.
2. **Linters e analisadores estáticos**: garantem conformidade com convenções de código antes do commit.
3. **Adaptadores especializados**: exploram otimizações nativas do motor subjacente (como DuckDB, Snowflake ou BigQuery).
4. **Estratégias avançadas de CI**: aceleram deploys reduzindo tempo e custos de computação.

---

## 2. Pacotes dbt (dbt Packages)

Instalados via arquivo `transform/packages.yml` executando o comando `uv run dbt deps`.

### 2.1 dbt_utils
- **O que é**: O pacote canônico mais popular do ecossistema, mantido diretamente pela dbt Labs. Funciona como uma "biblioteca padrão" de utilitários SQL, testes genéricos e macros para geração de código.
- **Quando usar**: Em praticamente 100% dos projetos dbt. É essencial para testes de chaves compostas, intervalos de valores, geração de surrogate keys e pivoteamento dinâmico de colunas.
- **Exemplo de uso**:
  ```yaml
  # transform/models/intermediate/_intermediate__models.yml
  models:
    - name: int_cnaes_secundarios__explodidos
      data_tests:
        - dbt_utils.unique_combination_of_columns:
            combination_of_columns:
              - cnpj_completo
              - codigo_cnae_secundario
  ```
- **Uso neste projeto**: **SIM** (versão 1.4.1 instalada). Usado extensivamente para `unique_combination_of_columns`, `accepted_range` e `expression_is_true`.
- **Documentação oficial**: https://hub.getdbt.com/dbt-labs/dbt_utils/latest/

---

### 2.2 dbt_expectations
- **O que é**: Extensão criada pela Metaplane inspirada no framework [Great Expectations](https://greatexpectations.io/). Fornece mais de 50 testes estatísticos avançados, asserções de formato de dados e métricas de distribuição.
- **Quando usar**: Quando testes básicos de não-nulo e unicidade são insuficientes para garantir a saúde dos dados (ex.: validar desvio-padrão de valores monetários, proporção de nulos em uma coluna, formatos regex de e-mails/telefones).
- **Exemplo de uso**:
  ```yaml
  models:
    - name: fct_resumo_mensal
      columns:
        - name: qtd_estabelecimentos
          data_tests:
            - dbt_expectations.expect_column_values_to_be_between:
                min_value: 1
                max_value: 1000000
  ```
- **Uso neste projeto**: **SIM** (versão 0.10.10 instalada).
- **Documentação oficial**: https://hub.getdbt.com/metaplane/dbt_expectations/latest/

---

### 2.3 dbt-audit-helper
- **O que é**: Pacote da dbt Labs projetado para comparar dados entre duas relações (duas tabelas, ou uma tabela e uma view). Gera consultas de comparação coluna a coluna, diferenças percentuais e detecção de drift de valores.
- **Quando usar**: Excelente durante grandes refatorações ou migrações de sistemas legados para comparar saídas lado a lado no console.
- **Exemplo de uso**:
  ```sql
  -- Comparação interativa no console via dbt show
  {{ audit_helper.compare_relation_columns(
      a_relation=ref('bh_empresas'),
      b_relation=ref('audit__bh_empresas_sql_original')
  ) }}
  ```
- **Uso neste projeto**: **NÃO**. Por quê? No ambiente DuckDB local, o teste singular customizado com `hash(*columns(*))` e `EXCEPT ALL` (`tests/paridade_bh_empresas.sql`) é ordens de magnitude mais rápido (~3,4× mais veloz em 60M+ linhas reais) e não exige macros intermediárias de comparação estática.
- **Documentação oficial**: https://hub.getdbt.com/dbt-labs/audit_helper/latest/

---

### 2.4 Elementary
- **O que é**: Plataforma open-source de observabilidade de dados nativa do dbt. Instala modelos incrementais que capturam artefatos de cada execução, anomalias de volume e frescor, além de gerar um relatório HTML estático autossuficiente e alertas em Slack/Teams.
- **Quando usar**: Equipes médias/grandes que precisam de um painel visual consolidado de Data Quality e monitoramento de falhas em produção sem pagar por um SaaS caro de observabilidade.
- **Exemplo de uso**: Adicionar o pacote `elementary-data/elementary` em `packages.yml` e rodar `edr monitor` na esteira de CI/CD.
- **Uso neste projeto**: **NÃO**. O projeto optou por uma arquitetura zero-dependência externa: implementamos nossa própria camada leve de telemetria nativa com a macro `registrar_resultados_testes` (hook `on-run-end`) gravando em `main.dq_historico_testes` e a view analítica `dq_resumo_execucao`.
- **Documentação oficial**: https://docs.elementary-data.com/

---

### 2.5 dbt-project-evaluator
- **O que é**: Pacote desenvolvido pela dbt Labs que atua como um "linter de arquitetura dbt". Avalia o projeto em relação às convenções recomendadas pela dbt Labs (ex.: modelos sem documentação, staging fazendo joins indevidos, dependências circulares, modelos órfãos que ninguém consome).
- **Quando usar**: Em code reviews e auditorias periódicas de governança em codebases em crescimento.
- **Exemplo de uso**: Adicionar em `packages.yml` e rodar `dbt build --select package:dbt_project_evaluator`.
- **Uso neste projeto**: **NÃO como pacote dbt**, mas **SIM como suíte de testes de integração Python** (`tests/integration/test_escopo_meta.py` e `test_convencao_nomes.py`), que impõem regras estritas de nomenclatura, escopo, ausência de colunas pessoais e estrutura de camadas via pytest em menos de 2 segundos.
- **Documentação oficial**: https://hub.getdbt.com/dbt-labs/dbt_project_evaluator/latest/

---

### 2.6 codegen
- **O que é**: Pacote utilitário para geração automática de código boilerplate (criação automática de YAML de fontes a partir do catálogo, geração de staging models base e scaffolding de documentação).
- **Quando usar**: Na inicialização de novos projetos ou ao ingerir dezenas de novas tabelas de uma só vez, economizando horas de digitação manual de YAMLs.
- **Exemplo de uso**:
  ```bash
  uv run dbt run-operation generate_source --args '{"schema_name": "raw", "table_names": ["estabelecimentos", "empresas"]}'
  ```
- **Uso neste projeto**: **NÃO no runtime de produção**. Foi útil apenas durante a fase preliminar de exploração das fontes.
- **Documentação oficial**: https://hub.getdbt.com/dbt-labs/codegen/latest/

---

## 3. Qualidade de Código e Alternativas de Observabilidade

### 3.1 sqlfluff e dbt-templater
- **O que é**: O linter e auto-formatter padrão da indústria para SQL com suporte a Jinja e dbt. O plugin `sqlfluff-templater-dbt` compila o Jinja em tempo de análise estática antes de verificar o SQL contra as regras de estilo.
- **Quando usar**: Em todo projeto sério de engenharia analítica. Impede que inconsistências de estilo (maiúsculas vs. minúsculas, indentação de CTEs, trailing commas, aliases implícitos) cheguem ao repositório git.
- **Exemplo de configuração**:
  ```ini
  # .sqlfluff (na raiz do projeto)
  [sqlfluff]
  dialect = duckdb
  templater = dbt

  [sqlfluff:templater:dbt]
  project_dir = ./transform
  profiles_dir = ./transform
  ```
- **Uso neste projeto**: **SIM**. Integrado aos comandos `make lint` e configurado no git pre-commit hook (`uv run sqlfluff lint transform/models`). Note que o `Makefile` cria `mkdir -p $(RAIZ_DADOS)` antes do lint porque o dbt-templater inicializa a conexão com o DuckDB para compilar as macros e checar schemas.
- **Documentação oficial**: https://docs.sqlfluff.com/

---

### 3.2 dbt-checkpoint (Git Pre-commit Hooks)
- **O que é**: Coleção de hooks de pre-commit para projetos dbt (antigo `pre-commit-dbt`). Verifica se os modelos possuem documentação, se colunas têm testes, se há referências a fontes não declaradas e se os nomes de arquivos seguem convenções regex.
- **Quando usar**: Para equipes distribuídas onde múltiplos engenheiros contribuem simultaneamente, assegurando padrões estritos de governança antes do `git commit`.
- **Exemplo de uso no `.pre-commit-config.yaml`**:
  ```yaml
  - repo: https://github.com/dbt-checkpoint/dbt-checkpoint
    rev: v2.0.6
    hooks:
      - id: check-model-has-tests
      - id: check-model-has-description
  ```
- **Uso neste projeto**: **NÃO**. Por quê? Substituímos o overhead de dependências externas de hook por **guardas nativas em Python/pytest** (`tests/integration/test_escopo_meta.py`, `test_convencao_nomes.py` e `test_pipeline_e2e.py`). Nossos testes rodam mais rápido e validam requisitos específicos do projeto (como checar se `meta.escopo` e `tags` coincidem, e se nenhuma coluna de contato pessoal foi exposta).
- **Documentação oficial**: https://github.com/dbt-checkpoint/dbt-checkpoint

---

### 3.3 Alternativas: Great Expectations, Soda Core e re_data

| Ferramenta | Arquitetura | Vantagens | Desvantagens | Quando preferir ao dbt test puro |
|---|---|---|---|---|
| **Great Expectations (GX)** | Python-first; suítes declarativas em JSON/YAML com renderização de Data Docs | Riquíssimo em profiling estatístico, relatórios visuais elegantes e validações de distribuição | Complexo de configurar e manter; desacoplado do DAG do dbt | Quando equipes de Data Science ou Data Governance precisam auditar datasets fora do dbt |
| **Soda Core / SodaCL** | Motor leve em Python com linguagem natural declarativa (SodaCL) | Sintaxe expressiva para SLAs e monitoramento de frescor e anomalias métricas | Exige infraestrutura adicional ou agente de execução externo | Quando há múltiplos motores além do dbt (Airflow, Spark, Kafka) que precisam do mesmo padrão de DQ |
| **re_data** | dbt-native observabilidade e alertas de anomalias | Roda diretamente dentro do dbt com métricas de drift estatístico | Menor adoção da comunidade em comparação a Elementary e Soda | Projetos legados que querem gráficos rápidos sem sair do dbt |

**Conclusão arquitetural**: Para projetos sobre DuckDB/Parquet, a combinação de **`dbt tests` (genéricos e singulares) + `dbt_utils` + `dbt_expectations`** oferece o melhor custo-benefício de simplicidade, velocidade e governança, sem a necessidade de manter serviços ou agentes adicionais.

---

## 4. Recursos Avançados do dbt-duckdb

O adaptador `dbt-duckdb` não é apenas um conector relacional comum; ele foi arquitetado para habilitar o paradigma **Data Lakehouse Local ou Serverless sobre Parquet/S3** (ADR-0001 e ADR-0007).

### 4.1 Materialização `external` e `external_location`
- **`external_location` em Fontes**: Permite que uma fonte declarada em YAML aponte diretamente para globs de arquivos Parquet sem carregar nada antecipadamente para o banco:
  ```yaml
  sources:
    - name: rfb
      meta:
        external_location: "{{ env_var('RAIZ_DADOS') }}/raw/rfb/{name}/mes_referencia=*/*.parquet"
  ```
- **Materialização `external` em Modelos**: Grava o resultado do `SELECT` diretamente em um arquivo externo (Parquet, CSV ou JSON) sem inflar o arquivo `.duckdb`:
  ```sql
  {{ config(materialized='external', location="dados/gold/bh_empresas.parquet") }}
  ```
  Isso transforma o DuckDB em um motor de computação puramente analítico e descartável. O verdadeiro repositório corporativo persistente é a camada Gold em Parquet.

### 4.2 Extensões e Conectividade (httpfs, s3, spatial)
O DuckDB suporta carregamento dinâmico de extensões compiladas em C++:
- **`httpfs` / S3 Secrets**: Habilita a leitura e gravação transparente em buckets S3, Cloudflare R2 ou Tigris com autenticação nativa:
  ```yaml
  # transform/profiles.yml
  s3:
    type: duckdb
    extensions:
      - httpfs
    secrets:
      - type: s3
        key_id: "{{ env_var('AWS_ACCESS_KEY_ID') }}"
        secret: "{{ env_var('AWS_SECRET_ACCESS_KEY') }}"
        endpoint: "{{ env_var('AWS_ENDPOINT_URL_S3') | replace('https://', '') }}"
        region: auto
  ```
- **`spatial`**: Suporte a dados geoespaciais e geometrias (usado em análises de satélite e polígonos municipais). Para a fórmula de Haversine pura, o projeto optou por implementar a matemática trigonométrica diretamente na macro `haversine_km` sem criar dependência externa de binários nativos.

---

## 5. Técnicas Avançadas de Engenharia de Dados

### 5.1 Modelos Incrementais e Estratégias de Carga
Em datasets massivos, recalcular tabelas inteiras a cada execução torna-se inviável. O dbt suporta `materialized='incremental'`, onde a macro `is_incremental()` filtra apenas os registros mais recentes nas execuções subsequentes.

#### Estratégias de Incrementalidade no dbt
1. **`append`**: Apenas insere as novas linhas no final da tabela. Ideal para logs imutáveis e telemetria (ex.: eventos de cliques).
2. **`delete+insert`**: Exclui os registros existentes na tabela de destino que coincidem com a chave primária dos novos dados e insere as linhas atualizadas.
3. **`merge`**: Executa um `MERGE INTO` SQL padrão atualizando (`UPDATE`) registros que mudaram e inserindo (`INSERT`) registros inéditos.
4. **`microbatch`** (introduzido no dbt 1.9+): Divide o carregamento incremental em lotes temporais menores e independentes (ex.: dia a dia ou hora a hora), garantindo reprocessamentos parciais automáticos em caso de falha transitória.

Exemplo de modelo incremental clássico:
```sql
{{ config(
    materialized='incremental',
    unique_key='cnpj_completo',
    incremental_strategy='delete+insert'
) }}

select * from {{ ref('stg_rfb__estabelecimentos') }}
{% if is_incremental() %}
  where _ingerido_em > (select max(_ingerido_em) from {{ this }})
{% endif %}
```

- **Uso neste projeto**: No pipeline de transformações corporativas deste port, os modelos da camada Gold são materializados como `external` (Parquet completo por mês), enquanto o histórico cumulativo de auditoria `main.dq_historico_testes` utiliza a estratégia de append direto gerenciada via hooks de ciclo de vida.

---

### 5.2 Snapshots (SCD Tipo 2)
- **O que é**: O recurso de `snapshot` do dbt implementa automaticamente a técnica de **Slowly Changing Dimension Tipo 2 (SCD2)**. Ele detecta alterações de atributos em tabelas dimensionais e cria novas versões do registro, mantendo as colunas técnicas `dbt_valid_from` e `dbt_valid_to`.
- **Estratégias de detecção**:
  - `timestamp`: monitora uma coluna de última atualização (`updated_at`).
  - `check`: compara hashes de colunas específicas (`check_cols=['endereco', 'telefone']`).
- **Por que este projeto NÃO usa snapshots**: O extrato público da Receita Federal já é publicado mensalmente como um retrato estático (*snapshot* em lote) de todos os CNPJs ativos e inativos do Brasil. Criar uma camada SCD2 no DuckDB multiplicaria 64 milhões de linhas mensalmente sem responder às perguntas analíticas de sobrevivência e dinâmica de mercado do projeto (ADR-0004 e ADR-0012).

---

### 5.3 CI Slim com `state:modified` e `--defer`
Em repositórios analíticos com centenas de modelos, executar `dbt build` em todo o projeto a cada Pull Request é inviável (pode levar horas e custar centenas de dólares em warehouses em nuvem).

O dbt resolve isso com o padrão **CI Slim**:
1. Baixa o `manifest.json` da última execução bem-sucedida em produção (`--state prod/`).
2. Compara o grafo atual com o grafo anterior para identificar apenas os nós alterados (`state:modified`).
3. Com a flag `--defer`, os nós upstream que não foram modificados **não são reconstruídos**: suas referências `{{ ref(...) }}` resolvem automaticamente para as tabelas físicas já existentes no schema de produção!

```bash
# Executa apenas os modelos modificados ou com testes novos, lendo os demais de produção
uv run dbt build --select state:modified+ --defer --state prod/target/
```
No ambiente de CI local deste projeto, o comando `make ci` roda em menos de 15 segundos sobre fixtures sintéticas garantindo feedback instantâneo.

---

### 5.4 Produtividade Operacional: `dbt retry` e `dbt clone`
- **`dbt retry`**: Se uma execução de 200 modelos falhar no modelo 150 devido a um erro transitório de rede ou sintaxe, você corrige o erro e roda `dbt retry`. O dbt consulta o `target/run_results.json` anterior e recomeça a execução **exatamente a partir dos nós que falharam**, sem reprocessar os 149 modelos anteriores.
- **`dbt clone`**: Clona modelos de um ambiente/schema para outro sem copiar fisicamente os dados (utilizando *zero-copy clone* em Snowflake, Databricks ou BigQuery). No DuckDB, a técnica análoga é copiar os arquivos `.parquet` diretamente no sistema de arquivos.

---

### 5.5 Data Diff (Auditoria Semântica de Migração)
Data Diffing é a disciplina de auditar mudanças comparando o conteúdo dos dados linha a linha.

Durante a migração deste projeto (do ambiente Spark/Databricks para DuckDB/dbt), o data diff foi fundamental para comprovar que as regras de negócio de `bh_empresas` (notebook 3) foram reproduzidas com exatidão matemática:
- Testamos a tradução literal com `tests/paridade_bh_empresas.sql`.
- Comparamos o comportamento de inner joins e quantificamos exatamente os 3 estabelecimentos das fixtures que eram descartados pela abordagem legada.
- Essa técnica assegura que mudanças estruturais de arquitetura ou engenharia ocorram com risco zero de corrupção semântica para analistas e tomadores de decisão.

---

## 6. Matriz de Adoção de Ferramentas no Projeto

| Ferramenta / Técnica | Adotada no Projeto? | Como é usada ou Por que não |
|---|---|---|
| **dbt_utils** | **SIM** | Testes genéricos de chaves compostas e intervalos aceitáveis. |
| **dbt_expectations** | **SIM** | Validações estatísticas adicionais e distribuições de métricas. |
| **dbt_date** | **SIM** | Funções utilitárias de manipulação e enriquecimento de datas. |
| **dbt-duckdb (external)**| **SIM** | Materialização de arquivos Parquet diretamente em `gold/`. |
| **sqlfluff** | **SIM** | Linting e formatação de SQL via pre-commit e `make lint`. |
| **dbt-audit-helper** | **NÃO** | Substituído por teste singular de `EXCEPT ALL` com hash, ~3,4× mais veloz no DuckDB. |
| **Elementary** | **NÃO** | Substituído por observabilidade nativa leve (`main.dq_historico_testes` + hooks). |
| **dbt-project-evaluator** | **NÃO** | Substituído por testes de integração Python com pytest (executam em < 2s). |
| **dbt-checkpoint** | **NÃO** | Substituído por pre-commit padrão com ruff, sqlfluff e guardas pytest. |
| **Snapshots (SCD2)** | **NÃO** | Desnecessário: o extrato mensal da RFB já é particionado como snapshot temporal. |
| **CI Slim (`--defer`)** | **SIM** | Documentado e suportado para execuções parciais aceleradas. |
| **dbt retry** | **SIM** | Suportado nativamente pelo dbt Core para recuperação de falhas operacionais. |
| **Data Diff** | **SIM** | Implementado no teste singular de paridade estrita (`paridade_bh_empresas.sql`). |
