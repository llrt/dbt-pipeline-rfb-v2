# Guia dbt — Parte 5: Boas Práticas, Performance e Usos Interessantes

> **Público-alvo:** engenheiro(a) de dados sênior, tech leads e arquitetos(as) de analytics engineering.
> Reúne padrões consolidados de engenharia de software aplicados a pipelines analíticos, otimizações de performance no motor DuckDB e casos de uso avançados extraídos deste repositório.
>
> **Parte 5 de 5** — ver também `01-fundamentos.md`, `02-fluxo-e-testes.md`, `03-qualidade-antes-e-depois.md` e `04-bibliotecas-e-tecnicas.md`.

---

## Sumário

- [1. Melhores Práticas de Engenharia e Arquitetura](#1-melhores-práticas-de-engenharia-e-arquitetura)
  - [1.1 Estrutura e Convenção de Nomenclatura (ADR-0014)](#11-estrutura-e-convenção-de-nomenclatura-adr-0014)
  - [1.2 Padrão de Estilo SQL e CTEs Funcionais](#12-padrão-de-estilo-sql-e-ctes-funcionais)
  - [1.3 Escolha Racional de Materializações](#13-escolha-racional-de-materializações)
  - [1.4 Contratos de Esquema e Versionamento](#14-contratos-de-esquema-e-versionamento)
  - [1.5 Governança: meta, tags, groups e access](#15-governança-meta-tags-groups-e-access)
  - [1.6 Segurança de Credenciais e Isolamento de Segredos](#16-segurança-de-credenciais-e-isolamento-de-segredos)
- [2. Otimização de Performance no DuckDB](#2-otimização-de-performance-no-duckdb)
  - [2.1 Gestão de Memória e Spill to Disk](#21-gestão-de-memória-e-spill-to-disk)
  - [2.2 Concorrência: DBT_THREADS versus DUCKDB_THREADS](#22-concorrência-dbt_threads-versus-duckdb_threads)
  - [2.3 Formato Parquet e Particionamento Inteligente](#23-formato-parquet-e-particionamento-inteligente)
  - [2.4 Operação: O Mito da Primeira Execução Lenta (P9)](#24-operação-o-mito-da-primeira-execução-lenta-p9)
- [3. Usos Interessantes e Casos Avançados](#3-usos-interessantes-e-casos-avançados)
  - [3.1 dbt como Camada Semântica para BI](#31-dbt-como-camada-semântica-para-bi)
  - [3.2 Mapeamento de Linhagem Downstream com Exposures](#32-mapeamento-de-linhagem-downstream-com-exposures)
  - [3.3 Prototipação Rápida com dbt show](#33-prototipação-rápida-com-dbt-show)
  - [3.4 Estudos de Caso Versionados no analyses/](#34-estudos-de-caso-versionados-no-analyses)
  - [3.5 Manutenção com run-operation e Macros de Hook](#35-manutenção-com-run-operation-e-macros-de-hook)
  - [3.6 Reprocessamento Histórico Parametrizado via vars](#36-reprocessamento-histórico-parametrizado-via-vars)
  - [3.7 Telemetria Persistente de Testes via Hooks](#37-telemetria-persistente-de-testes-via-hooks)
  - [3.8 Geração Automatizada de Catálogo a partir do Manifest](#38-geração-automatizada-de-catálogo-a-partir-do-manifest)

---

## 1. Melhores Práticas de Engenharia e Arquitetura

### 1.1 Estrutura e Convenção de Nomenclatura (ADR-0014)

Um dos maiores desafios em projetos que lidam com dados públicos brasileiros (como a Receita Federal) é a mistura caótica de idiomas: termos técnicos de analytics engineering em inglês misturados a jargões fiscais em português.

Neste projeto, adotamos a regra canônica do [ADR-0014](../../docs/adr/0014-convencao-idioma.md):
- **Vocabulário estrutural do dbt em INGLÊS**: nomes de pastas (`staging`, `intermediate`, `marts/core`, `marts/analytics`, `audit`, `observability`), comandos da CLI, materializações (`view`, `table`, `external`) e configurações de meta (`escopo: original`, conforme ADR-0006).
- **Vocabulário de domínio de negócio em PORTUGUÊS**: nomes de entidades e colunas que refletem a legislação e conceitos tributários brasileiros (`estabelecimentos`, `naturezas`, `simples`, `municipios`, `cnpj_raiz`, `capital_social`, `situacao_cadastral`).
- **Prefixos claros por propósito**:
  - `stg_<fonte>__<entidade>`: views de higienização 1:1 (`stg_rfb__estabelecimentos`).
  - `int_<entidade>__<verbo>`: tabelas físicas de enriquecimento (`int_estabelecimentos__enriquecidos`).
  - `dim_<entidade>`: dimensões conformadas Kimball (`dim_municipio`, `dim_cnae`).
  - `fct_<evento_ou_grão>`: tabelas fato (`fct_estabelecimentos`, `fct_resumo_mensal`).
  - `bridge_<entidade_a>_<entidade_b>`: tabelas ponte para relações N:N (`bridge_estabelecimento_cnae_secundario`).
  - `mart_<pergunta_negocio>`: modelos de inteligência de mercado (`mart_concorrencia_municipio`).

---

### 1.2 Padrão de Estilo SQL e CTEs Funcionais

Todo script SQL deve seguir o padrão de **CTEs Funcionais** estruturado em 3 blocos:
1. **Import CTEs**: lê exclusivamente os modelos upstream via `{{ ref(...) }}` ou `{{ source(...) }}` sem transformações pesadas.
2. **Logic CTEs**: executa joins, agregações, filtros e regras de negócio.
3. **Final Select**: projeta o resultado limpo e tipado.

Exemplo real de arquitetura limpa de modelo (`transform/models/intermediate/int_cnaes_secundarios__explodidos.sql`):

```sql
-- Uma linha por (estabelecimento, CNAE secundário): explode `cnaes_secundarios_lista` (lista já
-- normalizada para 7 dígitos no staging). Lista vazia não gera linhas; códigos repetidos no mesmo
-- estabelecimento contam uma vez.
select distinct
  cnpj_completo,
  unnest(cnaes_secundarios_lista) as codigo_cnae_secundario
from {{ ref('int_estabelecimentos__enriquecidos') }}
```
**Regras de estilo**:
- Palavras-chave SQL em **minúsculas** (`select`, `from`, `where`, `join`).
- Vírgulas no final das linhas (não no início).
- CTEs sempre nomeadas com substantivos ou verbos no particípio.
- Zero uso de `SELECT *` no bloco `final` sem antes limitar ou nomear explicitamente colunas no select.

---

### 1.3 Escolha Racional de Materializações

A escolha incorreta da materialização pode degradar o tempo de execução ou consumir gigabytes de armazenamento desnecessário:

| Camada | Materialização Escolhida | Por que esta escolha? |
|---|---|---|
| **Staging** | `view` | Camada leve de limpeza e tipagem. Como o DuckDB possui taxa de varredura ultrarrápida em Parquet, manter views evita duplicar gigabytes do raw em disco. |
| **Intermediate** | `table` | Concentra joins complexos e explosões (`unnest`). Persistir como tabela física no DuckDB evita que 10 modelos downstream recalculem os mesmos joins repetidamente. |
| **Marts** | `external` (Parquet) | Escreve via `COPY TO ... (FORMAT PARQUET)` diretamente na pasta `gold/`. Desacopla o arquivo `.duckdb` dos consumidores finais (BI, Python, DuckDB CLI). |
| **Auditoria** | `ephemeral` | Não cria objeto no banco; o SQL é injetado inline no teste de paridade via CTE, economizando tempo de DDL. |

---

### 1.4 Contratos de Esquema e Versionamento

- **Contratos (`contract: {enforced: true}`)**:
  Adote contratos obrigatórios em **todos os modelos das camadas Marts e Core**. Um pipeline analítico profissional não pode quebrar dashboards executivos por alterações silenciosas de tipos de colunas. Ao forçar o contrato, o dbt garante a imutabilidade da interface.
- **Versionamento de Modelos (`versions`)**:
  Quando uma evolução estrutural quebra a compatibilidade retroativa (ex.: mudança de granularidade em `fct_resumo_mensal`), declare versões no YAML (`v1`, `v2`) mantendo a versão anterior ativa temporariamente durante a transição dos relatórios.

---

### 1.5 Governança: `meta`, `tags`, `groups` e `access`

- **`meta.escopo` e `tags`**:
  Permitem segmentar execuções de testes e compilações (`dbt build --select tag:escopo_original` vs. `dbt build --select tag:escopo_adicao`).
- **`access: public | protected | private`** (dbt Mesh):
  - `private`: modelos internos de um grupo que só podem ser referenciados dentro do mesmo grupo (`group`).
  - `protected` (padrão): modelos que podem ser referenciados por qualquer modelo dentro do mesmo projeto dbt.
  - `public`: modelos que formam contratos públicos consumíveis por outros projetos/times dbt.

---

### 1.6 Segurança de Credenciais e Isolamento de Segredos

- **Zero credenciais no Git**: Nenhuma senha, chave AWS ou token deve constar em arquivos `.yml` ou `.sql`.
- **Injeção via `env_var()`**:
  ```yaml
  key_id: "{{ env_var('AWS_ACCESS_KEY_ID') }}"
  secret: "{{ env_var('AWS_SECRET_ACCESS_KEY') }}"
  ```
- **Falta de valor padrão nas credenciais**: No arquivo `profiles.yml`, não forneça valores default para credenciais S3 (`AWS_ACCESS_KEY_ID`). Se uma variável faltar, o dbt deve falhar imediatamente nomeando explicitamente qual variável de ambiente está ausente.

---

## 2. Otimização de Performance no DuckDB

O DuckDB é um dos motores analíticos in-process mais rápidos do mundo. No entanto, ao processar os mais de **64,5 milhões de estabelecimentos** da Receita Federal em hardware modesto ou instâncias de CI, o conhecimento de seus mecanismos internos é mandatório para evitar travamentos.

### 2.1 Gestão de Memória e Spill to Disk

Por padrão, o DuckDB tenta alocar a maior parte da memória física disponível para buffers de leitura e hash tables de joins. Em consultas analíticas densas (como o `EXCEPT ALL` de paridade com 15 colunas ou joins multi-milhões de linhas):
- **O Limite de Memória (`memory_limit`)**:
  Configure no `profiles.yml` o teto máximo (ex.: `24GB` para máquinas com 32GB de RAM, ou `2GB` no CI). Esse limite restringe o buffer pool interno do banco.
- **Diretório Temporário (`temp_directory`)**:
  Se o consumo ultrapassar o `memory_limit`, o DuckDB faz **spill to disk** (grava blocos intermediários de hash join em disco). Por padrão, o DuckDB já utiliza `<banco>.tmp` como diretório temporário, mas no `dbt-duckdb` é recomendável configurar `settings.temp_directory` apontando para um volume SSD rápido (`_tmp/`). Atenção: no profile do dbt-duckdb, o campo deve ir dentro de `settings:` (se colocado no topo do profile, é ignorado). Lembre-se também de que `memory_limit` limita o buffer pool do banco, mas não o RSS total do processo (que inclui buffers de rede e threads).

---

### 2.2 Concorrência: `DBT_THREADS` versus `DUCKDB_THREADS` (após F3a)

Um ponto sutil de afinação em dbt-duckdb é a separação entre o paralelismo do grafo e o paralelismo da query:
1. **`DBT_THREADS`**: Controla o número de modelos independentes do DAG que o dbt tenta compilar e rodar simultaneamente. Em pipelines pesados sobre um único arquivo DuckDB, elevar muito `DBT_THREADS` pode causar contenção de escrita no catálogo. O ideal é manter entre **2 e 4**.
2. **`DUCKDB_THREADS`**: Controla quantas threads de CPU o DuckDB utiliza internamente para vetorizar **cada consulta individual** (varredura de blocos Parquet, projeções e agregações). Em máquinas multicore, defina `DUCKDB_THREADS=8` ou o número de cores físicos da CPU.

Essa segregação garante que uma query pesada utilize toda a capacidade da CPU sem que múltiplas tarefas concorrentes disputem travas de escrita de catálogo.

---

### 2.3 Formato Parquet e Particionamento Inteligente

- **Hive Partitioning**:
  O módulo de ingestão grava os arquivos brutos organizados por pasta: `raw/rfb/estabelecimentos/mes_referencia=2026-09/*.parquet`.
  O dbt lê utilizando globs: `mes_referencia=*/*.parquet`.
- **Seleção Explícita de Partição**:
  Como o DuckDB reconhece partições Hive automaticamente, evite ambiguidade entre a coluna da pasta (`mes_referencia`) e a coluna gravada nos dados (`_mes_referencia`). Nossas fontes utilizam globs específicos e filtram explicitamente o maior mês disponível.
- **Estatísticas de Rodapé (Min/Max)**:
  O formato Parquet embute metadados de valores mínimos e máximos por bloco de 100k linhas. Consultas filtradas por data (`dat_inicio_atividade >= '2020-01-01'`) realizam *row group skipping*, lendo apenas frações do arquivo físico.

---

### 2.4 Operação: O Mito da Primeira Execução Lenta (P9)

Ao clonar o repositório em uma máquina nova ou rodar o pipeline pela primeira vez em um ambiente de CI limpo, o comando inicial pode demorar alguns minutos. Nas execuções seguintes, o mesmo comando executa em **~20 segundos**.

#### Por que isso acontece?
1. **Resolução e download de dependências Python**: O `uv sync` precisa criar o ambiente virtual `.venv` e baixar dezenas de dependências compiladas.
2. **Download dinâmico da extensão `httpfs`**: Durante o teste de conexão S3 (`dbt debug --target s3`), o DuckDB baixa a extensão nativa pré-compilada `httpfs` do repositório oficial da DuckDB Labs para a pasta de extensões local do usuário (`~/.duckdb/extensions/`).
3. **Instalação de pacotes dbt**: O `dbt deps` baixa os pacotes `dbt_utils` e `dbt_expectations`.

#### Boas práticas operacionais:
- **Cache local**: Em esteiras de CI/CD (GitHub Actions, GitLab CI), configure cache para as pastas `.venv/`, `transform/dbt_packages/` e `~/.duckdb/extensions/`.
- **Prevenção de DarkWake e Sleep em Laptops (Mac)**: Quando rodando pipelines sobre o extrato real de 64M linhas em notebooks, o macOS pode entrar em modo *DarkWake* ou dormir quando ocioso. Utilize o utilitário **`caffeinate -i`** (ex.: `caffeinate -i make ci`) para impedir que a máquina durma por ociosidade durante a execução.

---

## 3. Usos Interessantes e Casos Avançados

### 3.1 dbt como Camada Semântica para BI

Em vez de construir modelos de dados proprietários e cálculos divergentes dentro de cada ferramenta de BI (Power BI, Tableau, Metabase), o dbt atua como o **repositório central da lógica de negócio**:
- As métricas de concorrência, idade média e elegibilidade de coortes são calculadas nos marts SQL do dbt.
- As ferramentas de BI apenas conectam nos arquivos Parquet gerados em `gold/` via DirectQuery ou modo Import periódico, garantindo que o número visto no relatório seja 100% idêntico ao auditado no CI.

---

### 3.2 Mapeamento de Linhagem Downstream com Exposures

O arquivo `transform/models/marts/core/_core__exposures.yml` formaliza que o dashboard executivo do Power BI depende diretamente das tabelas fato e dimensões do projeto:

```yaml
version: 2
exposures:
  - name: painel_power_bi_estabelecimentos
    label: Painel Power BI — estabelecimentos RFB
    type: dashboard
    maturity: low
    description: >
      Painel de BI sobre o modelo estrela (ADR-0013), conectado ao Parquet de gold/.
    depends_on:
      - ref('dim_data')
      - ref('dim_municipio')
      - ref('dim_cnae')
      - ref('fct_estabelecimentos')
      - ref('fct_resumo_mensal')
```
**Comando útil**: Se você for alterar a dimensão de municípios, execute:
```bash
uv run dbt ls --select "dim_municipio+"
```
O dbt listará todas as tabelas e o exposure do Power BI, alertando imediatamente sobre quem será impactado pela mudança.

---

### 3.3 Prototipação Rápida com `dbt show`

Em vez de abrir um client SQL externo ou compilar o modelo e inspecionar a saída manualmente, use `dbt show` para visualizar as primeiras 5 ou 10 linhas diretamente no terminal:

```bash
# Inspecionar a saída do modelo de fornecedores próximos
uv run dbt show --select mart_fornecedores_proximos --limit 5

# Testar uma query inline com macros Jinja sem criar arquivo (usando a flag --limit da CLI)
uv run dbt show --inline "select {{ texto_ou_nulo('nome') }} from {{ ref('bh_empresas') }}" --limit 3
```

---

### 3.4 Estudos de Caso Versionados no `analyses/`

O diretório `transform/analyses/` guarda scripts SQL que contêm Jinja e `{{ ref(...) }}`, mas que **não são materializados como tabelas ou views**.

Neste projeto, as 9 consultas analíticas que compõem o relatório final de negócios (estudo de viabilidade de varejo de tintas em Fundão/ES) estão versionadas em `transform/analyses/`:
- `transform/analyses/estudo_caso_q1_concorrentes.sql`
- `transform/analyses/estudo_caso_q2_q3_idade_porte.sql`
- `transform/analyses/estudo_caso_adicao_sobrevivencia.sql`
- `transform/analyses/estudo_caso_adicao_fornecedores_proximos.sql`

O comando `rfb relatorio` compila esses arquivos via dbt, executa as consultas diretamente no DuckDB e compila o relatório executivo em Markdown (`docs/RELATORIO_ESTUDO_CASO.md`).

---

### 3.5 Manutenção com `run-operation` e Macros de Hook

Macros Jinja podem ser executadas como comandos utilitários independentes via CLI:
```bash
# Executar manutenção hipotética de limpeza ou vacumming (exemplo conceitual)
uv run dbt run-operation macro_limpeza_artefatos --args '{"dias": 30}'
```
Além disso, macros acopladas aos eventos de ciclo de vida (`on-run-start` e `on-run-end` em `dbt_project.yml`) executam tarefas administrativas automaticamente antes e depois de cada execução.

---

### 3.6 Reprocessamento Histórico Parametrizado via `vars`

A flexibilidade de parâmetros permite reprocessar meses passados via variáveis de projeto:
```bash
# Reprocessar o extrato de janeiro de 2025 para um município específico
uv run dbt build --vars '{"mes_referencia": "2025-01", "caso_municipio": "COLATINA"}'
```
> **Atenção operacional crítica (P22)**:
> Os modelos das camadas de marts utilizam materialização `external`, gravando diretamente em `gold/<modelo>.parquet`. Ao executar um build de mês antigo com `--vars`, **o arquivo Parquet do mês corrente em `gold/` será sobrescrito** com os dados do mês antigo, e parâmetros como `caso_municipio` afetarão todo o dataset gerado! Para reprocessamentos históricos isolados, direcione a saída para um diretório ou target temporário (ex.: alterando `RAIZ_DADOS` para um scratchpad ou configurando `external_root` isolado), conforme detalhado no ADR-0004 e na revisão R3.

---

### 3.7 Telemetria Persistente de Testes via Hooks

A cada execução de testes, o hook `on-run-end` aciona a macro `registrar_resultados_testes` (`transform/macros/observability/registrar_resultados_testes.sql`). A macro itera sobre a variável global `results` do dbt e insere os resultados na tabela persistida `main.dq_historico_testes`:
- `invocation_id`: ID único da invocação dbt
- `executado_em`: Timestamp da execução
- `nome_teste`: Nome do teste ou unit test executado
- `tipo_teste`: Tipo do teste (`test` ou `unit_test`)
- `status`: Status do resultado (`pass`, `warn`, `fail` ou `error`)
- `falhas`: Quantidade de linhas com falha
- `severidade`: Severidade configurada (`error` ou `warn`)
- `escopo`: Classificação de governança (`original`, `adicao`, `adaptado`)

Isso permite criar dashboards de evolução histórica de Data Quality e monitorar o declínio ou melhora da qualidade das fontes públicas ao longo dos meses.

---

### 3.8 Geração Automatizada de Catálogo a partir do Manifest

O dbt gera o artefato `target/manifest.json`, que contém a árvore sintática completa do projeto.

Neste repositório, o script `scripts/gerar_qualidade_dados.py` lê o `manifest.json`, extrai todos os testes, descrições, severidades e escopos (`original` vs. `adicao`), e **regera a documentação técnica de qualidade** em `docs/QUALIDADE_DADOS.md`.

Uma guarda em teste de integração (`tests/integration/test_catalogo_dq.py`) regera o catálogo a partir do manifest atual e compara com o arquivo no disco via pytest, assegurando que qualquer alteração de testes ou modelos mantenha o catálogo de qualidade sincronizado!
