# Inteligência de mercado com dados de CNPJ — dbt + DuckDB + Parquet

> **Para quem:** todo mundo; é a porta de entrada · **Quando ler:** primeiro, para achar o documento certo.

[![ci](https://github.com/llrt/dbt-pipeline-rfb-v2/actions/workflows/ci.yml/badge.svg)](https://github.com/llrt/dbt-pipeline-rfb-v2/actions/workflows/ci.yml)

Port do [MVP de Engenharia de Dados (PUC-Rio)](https://github.com/llrt/pos_dados_puc_rio-mvp_sprint_eng_dados)
— originalmente notebooks Spark no Databricks Community Edition — para um pipeline **dbt** com **DuckDB**
sobre arquivos **Parquet** locais (ou em S3/Tigris). Base: dados abertos de CNPJ da Receita Federal,
tabelas da [Base dos Dados](https://basedosdados.org/) e fontes gratuitas baixadas direto do IBGE (CEMPRE, renda do
Censo 2022 e REGIC 2018).

> Pergunta-guia (do original): *"É viável abrir uma loja de tintas em Fundão/ES? Há muitos concorrentes? Há
> fornecedores por perto?"* — agora generalizável para qualquer atividade (CNAE) e município.

## Por que isso é interessante para você

- **Consultor(a) / empreendedor(a):** concorrentes, idade média, porte, **taxa de sobrevivência em 3 anos** e
  **fornecedores num raio de X km** para qualquer CNAE e município do Brasil — numa consulta. E, com as fontes
  do IBGE, a renda da população, **para onde os moradores vão comprar** e **quantas pessoas trabalham no setor**
  ([cenários de uso](docs/uso/cenarios.md); a resposta da pergunta-guia no dado real está no
  [relatório do estudo de caso](docs/relatorios/estudo-caso.md)).
- **Analista de mercado / BI:** pipeline mensal, idempotente e testado; agende `make atualizar` e, a cada mês novo
  da RFB, receba um **modelo estrela pronto para o Power BI** (Parquet) com série histórica e relatório de qualidade
  ([guia Power BI](docs/uso/power-bi.md)).
- **Quem quer perguntar em linguagem natural:** entregue a um agente (LLM) o [guia de consulta](docs/uso/consulta-agente.md) (quem **constrói** o agente lê [construcao-agente.md](docs/uso/construcao-agente.md)),
  o catálogo de golden queries e acesso somente leitura à base, e pergunte *"quantas lojas de tinta tem em Fundão?"*.
- **Quem está aprendendo dbt:** um projeto real, em português, com fontes, staging, marts, testes genéricos,
  singulares e unitários, contratos, freshness e um [guia de dbt](docs/guia-dbt/README.md) — tudo no laptop, custo zero.
- **Avaliador(a):** cada regra é rastreável — o que veio do MVP e o que é adição está marcado no código e no
  [ARCHITECTURE](ARCHITECTURE.md#11-escopo-original--adaptado--adição); decisões em [ADRs](docs/adr/README.md).

Produto, personas e casos de uso: [PRODUCT.md](PRODUCT.md).

## Início rápido

```bash
make setup                 # uv sync + dbt deps
make ci                    # fluxo completo sobre fixtures sintéticas (sem rede, ~2 min com cache)
make pipeline MES=2026-09  # dados reais: ingestão → freshness → dbt build → relatório (→ publicar)
make atualizar             # processa o mês mais recente publicado pela RFB, se houver novidade
cd transform && uv run mf query --saved-query estudo_caso_fundao_tintas   # a pergunta-guia, pela camada semântica
```

Antes da primeira execução real (máquina, disco, tempo, agendamento, S3, MotherDuck), leia a
[operação](docs/operacao.md).

## Documentação

| Entrada | Para quê |
|---|---|
| [Conceitos](docs/conceitos.md) | o que os dados significam: empresa × estabelecimento, situação cadastral, porte, MEI, CNAE, ciclo de vida, fontes IBGE, glossário |
| [Arquitetura](ARCHITECTURE.md) | camadas, contratos, qualidade de dados, riscos, o escopo original × adaptado × adição e [como estender](ARCHITECTURE.md#12-como-estender) (fonte, modelo, conceito ou documento novo) |
| [Operação](docs/operacao.md) | rodar com dados reais, atualização mensal, requisitos e tempos medidos, agendamento, publicação |
| Uso | [cenários](docs/uso/cenarios.md) · [Power BI](docs/uso/power-bi.md) · [consulta por agente](docs/uso/consulta-agente.md) · [construir o agente](docs/uso/construcao-agente.md) |
| Referência | [dicionário de dados](docs/referencia/dicionario-dados.md) · [camada semântica](docs/referencia/camada-semantica.md) · [regras de negócio](docs/referencia/regras-negocio.md) · [qualidade](docs/referencia/qualidade-dados.md) · [golden queries](docs/referencia/golden_queries/catalogo.json) |
| [Decisões](docs/adr/README.md) | os ADRs, com contexto, alternativas e consequências |

Também: [relatórios do dado real](docs/relatorios/estudo-caso.md) ([regras](docs/relatorios/regras-negocio.md)) ·
[histórico](docs/historico/README.md) · [guia de dbt](docs/guia-dbt/README.md) · [CHANGELOG](CHANGELOG.md) ·
[`.specs`](.specs/features/rfb-dbt-port/spec.md).

## Licença

MIT (como o projeto original).
