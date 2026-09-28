# PRODUCT — Pipeline RFB/CNPJ em dbt + DuckDB

## A ideia

Uma base analítica de **inteligência de mercado** construída a partir dos dados abertos de CNPJ da Receita
Federal (RFB) e de tabelas de apoio da [Base dos Dados](https://basedosdados.org/), agora como um pipeline
**dbt** reprodutível que roda num notebook comum: **DuckDB** como motor de consulta sobre **arquivos
Parquet** locais (ou em um bucket S3/Tigris).

É o port do MVP de Engenharia de Dados da pós PUC-Rio
([repo original](https://github.com/llrt/pos_dados_puc_rio-mvp_sprint_eng_dados)), que rodava em notebooks
Databricks Community Edition. O port preserva as regras de negócio originais e adiciona testes, novas
análises e checks de qualidade de dados — sempre marcados como **adição** (ver [docs/ESCOPO.md](docs/ESCOPO.md)).

A pergunta-guia continua a mesma: *"É viável abrir uma loja de tintas em Fundão/ES? Há muitos
concorrentes? Há fornecedores por perto?"* — generalizada para qualquer CNAE e município.

## Personas

| Persona | Quem é | Dor atual |
|---|---|---|
| **Consultor(a) / empreendedor(a)** | Apoia a abertura de negócios com dados | Responder "quantos concorrentes, há quanto tempo sobrevivem, onde estão os fornecedores" exige garimpar 20+ GB de CSV mal formatado |
| **Analista de inteligência de mercado** | Faz estudos setoriais/regionais recorrentes | Precisa de tabelas confiáveis e atualizáveis mês a mês, com métricas comparáveis (densidade, sobrevivência) |
| **Engenheiro(a) de dados aprendendo dbt** | Estudante/profissional migrando de notebooks para engenharia analítica | Faltam exemplos reais, completos e em português de um projeto dbt com testes e DQ sérios |
| **Avaliador(a)/professor(a)** | Avalia o MVP acadêmico | Quer ver linhagem, qualidade e rastreabilidade das decisões — não só o resultado final |

## Pitch por persona

- **Consultor(a):** *"Troque dias de planilha por uma consulta: concorrentes, idade média, porte, taxa de
  sobrevivência em 3 anos e fornecedores num raio de X km, para qualquer atividade e município do Brasil."*
- **Analista:** *"Um pipeline mensal, idempotente e testado: agende `make atualizar` e, quando a RFB publicar um
  novo mês, receba o modelo estrela em Parquet pronto para o Power BI, com série histórica e relatório de qualidade."*
- **Engenheiro(a) aprendendo dbt:** *"Um projeto dbt real, em português, com fontes, staging, marts, testes
  genéricos, singulares e unitários, contratos, freshness e um guia que explica cada peça — sem nuvem, sem
  custo, no seu laptop."*
- **Avaliador(a):** *"Cada regra tem origem rastreável: o que veio do MVP original e o que é adição está
  marcado no código (`meta.escopo`) e documentado, com decisões registradas em ADRs."*

## Principais casos de uso

1. **Contagem de concorrentes** por CNAE × município/UF, com situação (ativa/inativa) — *original*.
2. **Idade média e distribuição por porte** das empresas ativas de um setor/local — *original*.
3. **Busca de fornecedores** por CNAE (principal e secundário) no município, microrregião, mesorregião e UF — *original*.
4. **Densidade de concorrência** normalizada por população (empresas / 10 mil hab.) e ranking na UF — *adição*.
5. **Sobrevivência por coorte** (taxa de empresas ainda ativas após 1, 3 e 5 anos) por CNAE/porte/região — *adição* (responde de verdade a pergunta 3 do original).
6. **Dinâmica de mercado**: aberturas × encerramentos por ano — *adição*.
7. **Fornecedores próximos por distância** (km entre centroides de municípios) — *adição*.
8. **Relatório de qualidade de dados** por execução — *adição*.
9. **Atualização mensal automática** com série histórica (`rfb atualizar`) — *adição, pedido do usuário*.
10. **Modelo estrela para Power BI** (chaves inteiras, calendário, hierarquias, fato agregada mensal) — *adição, pedido do usuário*.

## Valores centrais

- **Reprodutibilidade:** um comando reconstrói tudo; resultados determinísticos (datas de referência fixas, não `now()`).
- **Qualidade verificável:** checks antes e depois de cada etapa; falhas bloqueiam ou alertam conforme severidade.
- **Rastreabilidade:** original × adição explícitos; decisões registradas.
- **Custo zero / local-first:** roda num laptop; nuvem (S3/Tigris) é opcional.
- **Didático:** código e documentação servem de material de estudo de dbt.

## O que está fora (outside)

- **Dados de sócios (QSA/Sócios)** — contêm dados de pessoas físicas; fora por minimização (LGPD) e por não responderem às perguntas.
- **Orquestrador** (Airflow/Dagster) — `rfb atualizar` é idempotente e há receitas de agendamento (cron/launchd/GitHub Actions); um orquestrador fica como trabalho futuro.
- **Relatório Power BI pronto (.pbix)** — entregamos o modelo estrela e o guia de conexão/medidas; o painel é montado pelo usuário.
- **SCD2 por estabelecimento** — o histórico é mantido de forma agregada (`fct_resumo_mensal`); snapshots por CNPJ ficam explicados no guia.
- **Geocodificação por endereço** — distância usa centroide do município, não o endereço do estabelecimento.
