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
| Camadas e subpastas do dbt (vocabulário da documentação oficial) | `staging`, `intermediate`, `marts`, `core`, `analytics`, `observability` |
| Prefixos de modelos dbt | `stg_`, `int_`, `dim_`, `fct_`, `bridge_`, `mart_`, `dq_` |
| Camadas de dados (arquitetura medalhão) | `raw`, `gold` |
| Vocabulário de processo/ferramenta | `ci`, `lint`, `docs`, `setup`, `clean`, `fixtures`, `pipeline`, `cli`, `tmp`, `lock` (extensão de arquivo), `main` |
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
| identificadores Python com palavras em inglês (ex.: `lock_execucao`, `sha`) | equivalentes em português (`trava_execucao`, `sha256_arquivo`…) |

**Consequências.** Um teste automatizado (`tests/unit/test_convencao_nomes.py`) protege a regra nas partes
verificáveis (subpastas de `models/`, prefixos dos modelos, módulos Python, subcomandos da CLI, alvos do Make).
O guia de dbt continua usando os nomes de camada da comunidade (staging/intermediate/marts), o que facilita o
aprendizado. Documentos anteriores são atualizados para os novos nomes.
