# Changelog

> **Para quem:** quem atualiza de uma versão para outra ou quer saber o que mudou · **Quando ler:** antes de
> atualizar, e para achar a release com o detalhe de cada versão.

Formato do [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/); versões no
[Versionamento Semântico](https://semver.org/lang/pt-BR/). O detalhe completo está na release de cada versão; o
histórico de como o projeto foi feito, em [docs/historico/](docs/historico/README.md).

## [Não lançada] — v1.5.1

### Adicionado
- [Construção do agente de consulta](docs/uso/construcao-agente.md): guia para quem programa o agente (o que
  indexar, prompt de sistema, ferramentas, versão do catálogo × banco, avaliação, modelo e segurança). Teste confere
  que os campos do catálogo citados existem.
- `versao_projeto` no `catalogo.json` (a versão do pacote que o gerou), para casar o catálogo com a tag que
  construiu o banco. Só aditivo: nenhum campo existente mudou.
- Funções de referência no guia de construção, extraídas e executadas pelo CI: `conectar_somente_leitura` e
  `exigir_leitura` (conexão endurecida: só arquivos sob a raiz dos dados, sem rede, sem extensão, configuração
  travada, uma consulta de leitura por vez), `comparar_resposta` (acerto exato com a normalização do catálogo, que
  aprova as 93 golden queries) e `conferir_esquema` (falha fechada catálogo × banco, com as golden queries
  bloqueadas).
- `tabelas` também nas golden queries semânticas (as relações que o `sql` lê). Só aditivo.
- Tamanhos do catálogo e do guia gerados pelo `make golden` no guia de construção e conferidos no CI.

### Corrigido
- Guia de construção: `read_only=True` mais um filtro de `SELECT` ainda deixavam o agente ler qualquer arquivo da
  máquina e acessar a rede; a conexão endurecida passa a ser obrigatória (revisão RGA). A camada vira desempate na
  recuperação, o manifesto da ingestão é descrito como tem `versao_pipeline` e o teste confere todo campo citado.
- `checar_saida` (guia de consulta §7) deixava passar CNPJ como `DECIMAL`, `DOUBLE`, lista ou struct: agora
  percorre valores aninhados, inclusive as chaves de `map`, e trata número inteiro em qualquer tipo numérico. O
  guia §3 descreve a conexão endurecida que o agente recebe.
- `comparar_resposta` (guia de construção §7) convertia texto com cara de número em número em todas as camadas e
  aprovava o código `'5'` contra `'05'`: agora só a semântica passa pelo texto do CSV do `mf`, como no gerador.

## [1.5.0] — 2026-10-15

### Adicionado
- `make conceitos`: insere a definição de cada doc block no lugar do conceito em
  [docs/conceitos.md](docs/conceitos.md) e monta o índice de termos; o `make ci` confere que está em dia e que o
  texto escrito à mão não repete a definição.
- Roteiro "Como estender" no [ARCHITECTURE (§12)](ARCHITECTURE.md#12-como-estender): o que fazer para uma fonte, um
  modelo, um conceito ou um documento novo.
- [Referência da ontologia](docs/referencia/ontologia/README.md), com o diagrama e a tabela conceito → modelo.

### Alterado
- Documentação reorganizada por público: `docs/uso/`, `docs/referencia/`, `docs/relatorios/` e `docs/historico/`;
  o README vira porta de entrada com 6 entradas. Correspondência das seções antigas em
  [reorganizacao-v1.5.0.md](docs/historico/reorganizacao-v1.5.0.md).
- Conceitos de negócio com fonte única: definições curtas em doc blocks do dbt, usadas pelos YAMLs, pelo
  dicionário, pelo catálogo do agente e por [docs/conceitos.md](docs/conceitos.md), que recebe a antiga Parte A da
  camada semântica. O ESCOPO entra no ARCHITECTURE (§11) e cada triagem vai para o fim da sua revisão.
- Em [docs/conceitos.md](docs/conceitos.md), cada conceito é dito uma vez: abre com a sua definição e segue só com o
  que ela não diz (base legal, exemplos, cuidados). As perguntas frequentes com `mf query` vão para a
  [referência da camada semântica](docs/referencia/camada-semantica.md#perguntas-frequentes); 1.012 → 643 linhas.
- [docs/operacao.md](docs/operacao.md) abre com os comandos do dia a dia e um sumário; as notas de upgrade ficam no
  fim. Os cenários apontam para o relatório do estudo de caso.
- Verificador de links e âncoras dos `.md` no `make ci`, que confere também a caixa do nome do arquivo; caminhos de
  `docs/` centralizados no código, com uma guarda por AST.

**Nota de upgrade:** `rfb relatorio` e `rfb regras` passam a gravar em `docs/relatorios/estudo-caso.md` e
`docs/relatorios/regras-negocio.md`. `--saida` e `--saida-relatorio` continuam valendo. Os arquivos-ponte nos
caminhos antigos (`docs/CAMADA_SEMANTICA.md`, `docs/DICIONARIO_DADOS.md`, `docs/GUIA_CONSULTA_LINGUAGEM_NATURAL.md`,
`docs/REGRAS_NEGOCIO.md`, `docs/ESCOPO.md`, `RETRO.md`) saem na v1.6.0. Depois de editar um doc block
(`transform/models/docs/conceitos.md`), rode `make conceitos`, `make golden` e `make dicionario`.

Release: [v1.5.0](https://github.com/llrt/dbt-pipeline-rfb-v2/releases/tag/v1.5.0)

## [1.4.1] — 2026-10-15

### Adicionado
- 93 golden queries em 23 conceitos × 7 camadas, testadas no CI com a resposta exata nas fixtures, e a matriz
  de cobertura conceito × camada.
- Catálogo legível por máquina (`make golden`) e o guia de consulta em linguagem natural para um agente, com
  glossário, 21 armadilhas, privacidade e exemplos testados (ADR-0023). Modelos e métricas não mudam.

Release: [v1.4.1](https://github.com/llrt/dbt-pipeline-rfb-v2/releases/tag/v1.4.1)

## [1.4.0] — 2026-10-15

### Adicionado
- Fontes gratuitas do IBGE baixadas da origem: CEMPRE, renda do Censo 2022 e REGIC 2018, mais o valor
  adicionado por atividade (ADR-0022).
- `bridge_municipio_destino_compras`, `mart_emprego_setor_municipio`, o polo de compras em `dim_municipio` e em
  `mart_concorrencia_area_mercado`, a RN-30 e os cenários de uso.
- `--renovar-ibge` e `--sem-ibge`; uma falha do IBGE vira aviso. Upgrade da v1.3 sem quebra.

Release: [v1.4.0](https://github.com/llrt/dbt-pipeline-rfb-v2/releases/tag/v1.4.0)

## [1.3.0] — 2026-10-13

### Adicionado
- Catálogo das regras e invariantes de negócio (RN-01 a RN-29), cada uma com a fonte primária (ADR-0020).
- Checks fora do `dbt build` e `rfb regras` / `make regras`, que geram o relatório de inconsistências do dado
  real só com contagens e saem com 0 mesmo havendo violações.

Release: [v1.3.0](https://github.com/llrt/dbt-pipeline-rfb-v2/releases/tag/v1.3.0)

## [1.2.0] — 2026-10-13

### Adicionado
- Dicionário de dados gerado do manifesto e do catálogo do dbt (`make dicionario`, ADR-0019): 57 tabelas e 559
  colunas, com grão, chaves, domínio, origem e linhagem, conferido no CI.
- `meta.campo_leiaute`, `meta.grao` e `meta.linhagem` nos YAMLs; descrições a 100 % nas fontes e no gold.

Release: [v1.2.0](https://github.com/llrt/dbt-pipeline-rfb-v2/releases/tag/v1.2.0)

## [1.1.0] — 2026-10-10

### Adicionado
- Camada semântica dbt/MetricFlow (ADR-0018): 8 modelos semânticos, 26 métricas com fotografia mensal, *time
  spine* e 4 *saved queries*; `make semantica`.
- Contexto de negócio das bases da RFB com fontes primárias e a ontologia OWL ligada ao modelo, ambos testados.

Release: [v1.1.0](https://github.com/llrt/dbt-pipeline-rfb-v2/releases/tag/v1.1.0)

## [1.0.1] — 2026-10-06

### Alterado
- YAMLs no formato `config:`, compatível com o dbt v2 (Fusion); a migração ao Fusion foi avaliada e adiada
  (ADR-0017).
- Testes herméticos (ignoram o `.env` do desenvolvedor) e CI com actions em Node 24. Sem mudança de modelo ou
  resultado.

Release: [v1.0.1](https://github.com/llrt/dbt-pipeline-rfb-v2/releases/tag/v1.0.1)

## [1.0.0] — 2026-10-02

### Adicionado
- Port do MVP de notebooks Spark para dbt + DuckDB sobre Parquet: `bh_empresas`, `agg_empresas` e o estudo de
  caso Fundão/ES, com paridade de 0 diferenças em 71,4 M linhas contra o SQL original.
- Pipeline mensal idempotente (`rfb pipeline`, `rfb atualizar`), modelo estrela para Power BI, marts de
  concorrência, sobrevivência, dinâmica e fornecedores, enriquecimento Base dos Dados e publicação opcional no
  MotherDuck.
- Qualidade de dados em todas as etapas, CPF mascarado nos nomes, guia de dbt e ADRs 0001–0016.

Release: [v1.0.0](https://github.com/llrt/dbt-pipeline-rfb-v2/releases/tag/v1.0.0)
