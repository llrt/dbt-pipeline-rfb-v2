# ADR-0014 — Convenção de idioma dos nomes

**Contexto.** O projeto misturava inglês e português sem regra explícita: pastas `transform/models`
(`staging`, `core` × `analises`, `observabilidade`), módulos Python (`convert.py`, `manifest.py` ×
`basedosdados.py`), subcomandos da CLI (`ingest`, `sync` × `atualizar`), variáveis de ambiente
(`DATA_ROOT` × `RFB_MAX_TAXA_REJEITO`) e identificadores (`lock_execucao`). O usuário pediu uma convenção
única e coerente (2026-09-29) e escolheu a opção abaixo.

**Decisão.** **Inglês apenas no vocabulário padronizado do dbt e das ferramentas; português em todo o resto.**

Lista fechada do que fica em inglês (exceções permitidas):

| Categoria | Termos |
|---|---|
| Pastas/arquivos exigidos pelas ferramentas | `models/`, `seeds/`, `macros/`, `tests/`, `analyses/`, `snapshots/`, `src/`, `dbt_project.yml`, `profiles.yml`, `packages.yml`, `pyproject.toml`, `Makefile`, `README.md` e demais arquivos-padrão |
| Camadas e subpastas do dbt (vocabulário da documentação oficial/ecossistema) | `staging`, `intermediate`, `marts`, `core`, `analytics`, `observability`, `audit` (modelos auxiliares de reconciliação/paridade — termo do `dbt-audit-helper`) |
| Prefixos de modelos dbt | `stg_`, `int_`, `dim_`, `fct_`, `bridge_`, `mart_`, `dq_`, `audit__` |
| Camadas de dados (arquitetura medalhão) e vocabulário de warehouse | `raw`, `gold`, `warehouse` (arquivo `warehouse.duckdb`) |
| Vocabulário de processo/ferramenta | `ci`, `lint`, `docs`, `setup`, `clean`, `fixtures`, `pipeline`, `cli`, `tmp`, `lock` (extensão de arquivo), `main`; nomes de targets dbt `dev`, `ci`, `s3` |
| Nomes de APIs/bibliotecas e variáveis de ambiente de terceiros | `AWS_*`, `DUCKDB_*`, `S3_URL_STYLE`, `DBT_*`, parâmetros de `httpx`/`duckdb`/`boto3`/`pytest` (`tmp_path`, `monkeypatch`…) |

Tudo o mais em **português** (sem acentos em identificadores): módulos e funções Python, variáveis, classes,
colunas, modelos (após o prefixo), macros, testes singulares, seeds, subcomandos da CLI, alvos do Make próprios
do projeto, variáveis de ambiente do projeto, diretórios de dados próprios, mensagens e documentação.

**Renomeações decorrentes (lote RN):**

| Antes | Depois |
|---|---|
| `transform/models/marts/analises/` | `transform/models/marts/analytics/` |
| `transform/models/observabilidade/` | `transform/models/observability/` |
| `config.py`, `schemas.py`, `errors.py`, `rfb_client.py`, `convert.py`, `manifest.py`, `storage.py` | `configuracao.py`, `esquemas.py`, `erros.py`, `cliente_rfb.py`, `conversao.py`, `manifesto.py`, `armazenamento.py` (testes idem) |
| CLI `rfb ingest` / `sync` / `report` | `rfb ingerir` / `sincronizar` / `relatorio` (`pipeline` e `atualizar` mantidos) |
| Make `ingest` / `sync` / `report` | `ingerir` / `sincronizar` / `relatorio` |
| `DATA_ROOT`, `DATA_ROOT_LOCAL` | `RAIZ_DADOS`, `RAIZ_DADOS_LOCAL` |
| `DATA_ROOT/_manifests`, `_downloads` | `_manifestos`, `_baixados` |
| `data/` (diretório padrão de `RAIZ_DADOS`), `part-<zip>.parquet`, `extract-<entidade>-*`, `_rfb_rejeitos_scan`, `_no_implementado` | `dados/`, `parte-<zip>.parquet`, `extracao-<entidade>-*`, `_rfb_rejeitos_varredura`, `_nao_implementado` (R2-09) |
| `DBT_DUCKDB_PATH` (variável do projeto com prefixo de terceiros) | `CAMINHO_DUCKDB` (R2-09) |
| identificadores Python com palavras em inglês (ex.: `lock_execucao`, `sha`) | equivalentes em português (`trava_execucao`, `sha256_arquivo`…) |

**Consequências.** Um teste automatizado (`tests/unit/test_convencao_nomes.py`) protege a regra nas partes
verificáveis (subpastas de `models/`, prefixos dos modelos, módulos Python, subcomandos da CLI, alvos do Make).
O guia de dbt continua usando os nomes de camada da comunidade (staging/intermediate/marts), o que facilita o
aprendizado. Documentos anteriores são atualizados para os novos nomes.

**Correção (2026-09-29, apontada pelo usuário).** O lote RN manteve `transform/models/paridade/` e o prefixo
`paridade__` por orientação equivocada do líder, que os tratou como termo de domínio. São estrutura do dbt: a pasta
passa a `transform/models/audit/` e o modelo a `audit__bh_empresas_sql_original`. Nomes de **testes** singulares
continuam em português (ex.: `paridade_bh_empresas`), como os demais testes do projeto. Regra prática para casos
novos: **pasta ou prefixo = estrutura (inglês, lista acima); nome após o prefixo, colunas, testes e macros = português.**
