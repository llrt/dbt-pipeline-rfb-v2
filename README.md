# Inteligência de mercado com dados de CNPJ — dbt + DuckDB + Parquet

Port do [MVP de Engenharia de Dados (PUC-Rio)](https://github.com/llrt/pos_dados_puc_rio-mvp_sprint_eng_dados)
— originalmente notebooks Spark no Databricks Community Edition — para um pipeline **dbt** com **DuckDB**
sobre arquivos **Parquet** locais (ou em S3/Tigris). Base: dados abertos de CNPJ da Receita Federal e
tabelas da [Base dos Dados](https://basedosdados.org/).

> Pergunta-guia (do original): *"É viável abrir uma loja de tintas em Fundão/ES? Há muitos concorrentes? Há
> fornecedores por perto?"* — agora generalizável para qualquer atividade (CNAE) e município.

## Por que isso é interessante para você

- **Consultor(a) / empreendedor(a):** concorrentes, idade média, porte, **taxa de sobrevivência em 3 anos** e
  **fornecedores num raio de X km** para qualquer CNAE e município do Brasil — numa consulta.
- **Analista de mercado / BI:** pipeline mensal, idempotente e testado; agende `make atualizar` e, a cada mês novo
  da RFB, receba um **modelo estrela pronto para o Power BI** (Parquet) com série histórica e relatório de qualidade.
- **Quem está aprendendo dbt:** um projeto real, em português, com fontes, staging, marts, testes genéricos,
  singulares e unitários, contratos, freshness e um [guia de dbt](docs/guia-dbt/README.md) — tudo no laptop, custo zero.
- **Avaliador(a):** cada regra é rastreável — o que veio do MVP e o que é adição está marcado no código e em
  [docs/ESCOPO.md](docs/ESCOPO.md); decisões em [ADRs](docs/adr/README.md).

## Documentos

| Documento | Conteúdo |
|---|---|
| [PRODUCT.md](PRODUCT.md) | ideia, personas, casos de uso, valores, fora de escopo |
| [ARCHITECTURE.md](ARCHITECTURE.md) | arquitetura geral e detalhada, contratos de dados, DQ, riscos |
| [docs/adr/](docs/adr/README.md) | decisões e justificativas |
| [docs/ESCOPO.md](docs/ESCOPO.md) | original × adaptado × adição |
| [docs/PLANO.md](docs/PLANO.md) | plano, equipe de agentes e modelos |
| [docs/OPERACAO.md](docs/OPERACAO.md) | pipeline real, atualização mensal, retenção, agendamento, requisitos de máquina |
| [docs/EXECUCAO_REAL.md](docs/EXECUCAO_REAL.md) | execução real (2026-09), tempos, volumes, avisos e paridade com o notebook 4 |
| [docs/POWER_BI.md](docs/POWER_BI.md) | modelo estrela e acesso pelo Power BI |
| [docs/guia-dbt/](docs/guia-dbt/README.md) | guia de uso do dbt |
| [.specs/features/rfb-dbt-port/](.specs/features/rfb-dbt-port/spec.md) | spec (EARS) e tarefas |

## Uso rápido

```bash
make setup                 # uv sync + dbt deps
make ci                    # fluxo completo sobre fixtures sintéticas (sem rede)
make pipeline MES=2026-09  # dados reais: ingestão → freshness → dbt build → relatório (→ publicar)
make atualizar             # processa o mês mais recente publicado pela RFB, se houver novidade
make publicar              # opcional: publica o gold no MotherDuck (requer MOTHERDUCK_TOKEN e MOTHERDUCK_BANCO)
make docs                  # dbt docs
```

### Primeira execução

Ao clonar o repositório em um ambiente limpo, a primeira execução pode levar alguns minutos:
- O `make setup` executa `uv sync --all-extras` (criação do `.venv` e resolução de pacotes Python) e `dbt deps` (download dos pacotes dbt).
- Durante o teste de conexão S3 (`dbt debug --target s3`), o DuckDB baixa a extensão nativa pré-compilada `httpfs` para `~/.duckdb/extensions/`.

Nas execuções seguintes, os caches locais (`.venv`, `transform/dbt_packages`, `~/.duckdb/extensions`) já estão populados e o `make ci` (unit + pipeline sobre fixtures de dois meses + integração + lint) completa em ~2 minutos.

**Migração (ADR-0014):** `DATA_ROOT`→`RAIZ_DADOS`, `DATA_ROOT_LOCAL`→`RAIZ_DADOS_LOCAL`, `DBT_DUCKDB_PATH`→`CAMINHO_DUCKDB`; o diretório padrão `data/` agora é `dados/`. As variáveis antigas causam erro.

**Threads:** `DBT_THREADS` (nós do dbt em paralelo) e `DUCKDB_THREADS` (threads do motor DuckDB) são variáveis distintas; ambas opcionais (padrões por alvo em `transform/profiles.yml`).

## Licença

MIT (como o projeto original).
