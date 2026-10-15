# Reorganização da documentação (v1.5.0): seção antiga → lugar novo

Registro de 2026-10-15. Na v1.5.0 a documentação foi reorganizada por público, com uma fonte única por assunto
([CHANGELOG](../../CHANGELOG.md)). Esta tabela cobre toda seção `##`/`###` dos documentos fundidos ou enxugados e diz
para onde foi cada uma. As referências aos arquivos antigos estão em versões fixadas por tag (por exemplo
[`docs/CAMADA_SEMANTICA.md` na v1.4.1](https://github.com/llrt/dbt-pipeline-rfb-v2/blob/v1.4.1/docs/CAMADA_SEMANTICA.md)).

Legenda do destino:

- **mantida**: a seção continua no mesmo documento, com o mesmo conteúdo (pode ter ganhado link ou cabeçalho);
- **movida**: o texto foi para outro lugar sem mudar (salvo links e numeração);
- **duplicada → fonte**: o texto repetia o que já existia noutro lugar e foi trocado por um link para lá;
- **descartada**: saiu de verdade, com o motivo.

Mudanças de lugar sem reescrita (lote D1) não estão aqui: `git log --follow` mostra o histórico de cada arquivo.

## `docs/CAMADA_SEMANTICA.md` (v1.4.1: `docs/referencia/camada-semantica.md`, inteiro)

| Seção antiga | Destino | Lugar novo |
|---|---|---|
| Introdução: "Adição" (ADR-0018) e o que a camada descreve | mantida | [camada-semantica.md](../referencia/camada-semantica.md), topo |
| Introdução: "O documento tem duas partes" | movida (reescrita) | [camada-semantica.md](../referencia/camada-semantica.md), topo: a separação em dois documentos, com link para os conceitos |
| Introdução: fontes entre colchetes, A7, números das fixtures, catálogo RN-xx | movida | [conceitos.md](../conceitos.md), introdução |
| `## Parte A — Negócio` | movida | [conceitos.md](../conceitos.md) |
| `### A1. As bases` | movida | [conceitos.md, §1](../conceitos.md#1-as-bases) |
| `### A2. Conceitos` (e todas as subseções `####`: CNPJ, Empresa × estabelecimento, Matriz × filial, Razão social × nome fantasia, Natureza jurídica, Capital social, Porte, Simples Nacional e MEI, Situação cadastral, Situação especial, Data de início de atividade, CNAE principal e secundárias, Município, CEMPRE, REGIC, Renda per capita, Valor adicionado) | movida | [conceitos.md, §2](../conceitos.md#2-conceitos), as mesmas subseções como `###`, com as mesmas âncoras. A definição curta de cada conceito central passou a ser doc block do dbt e aparece em [Definições](../conceitos.md#definições) |
| `### A3. Ciclo de vida` | movida | [conceitos.md, §3](../conceitos.md#3-ciclo-de-vida) |
| `### A4. Ontologia` | movida | [conceitos.md, §4](../conceitos.md#4-ontologia) |
| `### A5. Glossário rápido` | movida | [conceitos.md, §5](../conceitos.md#5-glossário), a mesma tabela, com um parágrafo que liga ao glossário do guia (vocabulário → coluna) |
| `### A6. Perguntas frequentes` | movida | [conceitos.md, §6](../conceitos.md#6-perguntas-frequentes) |
| `### A7. Fontes` | movida | [conceitos.md, §7](../conceitos.md#7-fontes) |
| `## Parte B — Estrutura técnica` | mantida | [camada-semantica.md](../referencia/camada-semantica.md), agora o documento inteiro |
| `### B1. Onde está e em qual padrão` | mantida | [§1](../referencia/camada-semantica.md#1-onde-está-e-em-qual-padrão) |
| `### B2. Entidades e junções` | mantida | [§2](../referencia/camada-semantica.md#2-entidades-e-junções) |
| `### B3. Métricas` | mantida | [§3](../referencia/camada-semantica.md#3-métricas) (âncora antiga `#b3-métricas`) |
| `### B4. Consultas salvas` | mantida | [§4](../referencia/camada-semantica.md#4-consultas-salvas) |
| `### B5. Como usar` | mantida | [§5](../referencia/camada-semantica.md#5-como-usar) |
| `### B6. Garantias (testes)` | mantida | [§6](../referencia/camada-semantica.md#6-garantias-testes) |
| `### B7. Limites e cuidados` | mantida | [§7](../referencia/camada-semantica.md#7-limites-e-cuidados) |
| `### B8. Como estender` | mantida | [§8](../referencia/camada-semantica.md#8-como-estender) |

## `docs/GUIA_CONSULTA_LINGUAGEM_NATURAL.md` (v1.4.1: `docs/uso/consulta-agente.md`)

O guia continua autossuficiente para o agente, que recebe só o guia e o catálogo (ADR-0023). Nenhuma seção saiu.

| Seção antiga | Destino | Lugar novo |
|---|---|---|
| Introdução e convenções | mantida | [consulta-agente.md](../uso/consulta-agente.md), topo, com o cabeçalho "Para quem", o link para os conceitos e a convenção nova: as definições dos conceitos estão no catálogo (`conceitos[].definicoes`) |
| `## 1. O que há na base` | mantida | §1 |
| `## 2. Camadas e a regra de escolha` | mantida | §2 |
| `## 3. Esquema físico consultável` e `### DuckDB local`, `### MotherDuck`, `### Target ci × dado real` | mantida | §3 |
| `## 4. Grão das tabelas e caminhos de join` | mantida | §4 |
| `## 5. Glossário: do vocabulário do usuário às colunas` | mantida | §5, agora declarado fonte única do mapeamento vocabulário → coluna; a definição de cada termo fica no catálogo e em [conceitos.md](../conceitos.md) |
| `## 6. Armadilhas` | mantida | §6 |
| `## 7. Privacidade` e `### Checagem obrigatória pós-execução` | mantida | §7 |
| `## 8. Procedimento: da pergunta à resposta` | mantida | §8 (o passo 2 cita as definições do catálogo) |
| `## 9. Exemplos de ponta a ponta` e `### Exemplo 1` a `### Exemplo 6` | mantida | §9 |
| `## 10. Resultados do dado real` | mantida | §10 |
| `## 11. Índice do catálogo` (bloco gerado) | mantida | §11 |
| `## 12. Métricas, dimensões e relações` (bloco gerado) | mantida | §12 (as descrições das colunas ganharam o texto dos doc blocks) |

## `docs/POWER_BI.md` (v1.4.1: `docs/uso/power-bi.md`)

| Seção antiga | Destino | Lugar novo |
|---|---|---|
| Introdução, resumo e tamanho do resumo mensal | mantida | [power-bi.md](../uso/power-bi.md), topo, com o cabeçalho "Para quem" |
| `## Como o Power BI acessa os dados` e `### 1. Parquet`, `### 2. Arquivo DuckDB local`, `### 3. MotherDuck`, `### Qual escolher`, `### Fontes oficiais` | mantida | [Como o Power BI acessa os dados](../uso/power-bi.md#como-o-power-bi-acessa-os-dados) |
| `## 1. O modelo estrela`: diagrama `erDiagram` | duplicada → fonte | [dicionário, Modelo estrela](../referencia/dicionario-dados.md#modelo-estrela) (gerado das chaves) e a tabela de [Relacionamentos](../uso/power-bi.md#relacionamentos), que continua no guia |
| `## 1. O modelo estrela`: `dim_mes` e `dim_cnae_secundario` são cópias; natureza jurídica fora do resumo | mantida | [§1](../uso/power-bi.md#1-o-modelo-estrela), texto abaixo da tabela |
| `## 1. O modelo estrela`: convenções (`sk_*` inteiras, membro `-1`) | mantida (resumida) | §1, texto abaixo da tabela; detalhe no [dicionário](../referencia/dicionario-dados.md) |
| `## 1. O modelo estrela`: `dim_data` de 1900-01-01 até a data de referência, `sk_data = yyyymmdd`, `sk_mes_referencia = yyyymm01` | duplicada → fonte | `dim_data` e `fct_resumo_mensal` no [dicionário](../referencia/dicionario-dados.md); o `yyyymm01` ficou na tabela da §1 |
| `## 1. O modelo estrela`: membros `-1` (1899-12-31) e `-2` (1899-12-30, ex.: 1194-08-15), só a fato detalhada aponta para `-2` | mantida (movida dentro do guia) | bullet "Tabela de datas" de [Relacionamentos](../uso/power-bi.md#relacionamentos) e a linha de `dim_data` da tabela da §1; o exemplo 1194-08-15 está no dicionário |
| `## 1. O modelo estrela`: hierarquias em colunas | mantida (resumida) | §1, última frase; as colunas no [dicionário](../referencia/dicionario-dados.md) |
| `### Relacionamentos` | mantida | [Relacionamentos](../uso/power-bi.md#relacionamentos) (inclui a ressalva da linha toda NULL num Parquet vazio) |
| `## 2. Atualização incremental por mês` | mantida | §2 |
| `## 3. Medidas DAX sugeridas` | mantida | §3 (o link da camada semântica aponta para `#3-métricas`) |
| `## 4. Exposure no dbt` | mantida | §4 |

## `ARCHITECTURE.md`

| Seção antiga | Destino | Lugar novo |
|---|---|---|
| Cabeçalho (documento vivo, links para ADRs, ESCOPO e PRODUCT) | mantida | topo, com o cabeçalho "Para quem"; o escopo aponta para a §11, e há links para a operação e os conceitos |
| `## 1. Visão geral`, `## 2. Stack` | mantida | §1, §2 |
| `## 3. Estrutura do repositório` | mantida | §3 (a árvore troca `ESCOPO.md` por `conceitos.md` e mostra `CHANGELOG.md` e `models/docs/`) |
| `## 4. EL — Ingestão` e `### 4.1` a `### 4.5` | mantida | §4 |
| `### 5.1 Camadas, materializações e convenções` | mantida | §5.1 (o mapeamento de nomes aponta para a §11) |
| `### 5.2 Variáveis` | mantida | §5.2 |
| `### 5.3 Modelos`: bullets por modelo (staging, intermediate, original, core, análises, observabilidade, golden queries) e o `erDiagram` do core | duplicada → fonte | tabela-resumo por camada na [§5.3](../../ARCHITECTURE.md#53-modelos); a descrição de cada modelo e coluna está no [dicionário](../referencia/dicionario-dados.md), gerado dos YAMLs, e o diagrama em [Modelo estrela](../referencia/dicionario-dados.md#modelo-estrela). A frase de `mart_dinamica_mercado` ("encerramentos (situação 08 com `dat_situacao`)") estava desatualizada: a regra vigente (todo não ativo) está na descrição do modelo e no doc block `abertura_encerramento` |
| `### 5.4 Seeds` | mantida | §5.4 |
| `## 6. Qualidade de dados — estratégia` | mantida | §6 |
| `## 7. Execução`: tabela de comandos | duplicada → fonte | [operação, Comandos](../operacao.md#comandos) (tabela de `pipeline`/`atualizar`/`regras` e a nova "Outros alvos", com `setup`, `fixtures`, `ci`, `docs`, `lint`, `sincronizar`, `publicar`…) |
| `## 7. Execução`: perfis dbt (`ci`, `dev`, `s3`) | movida | [operação, Primeira execução](../operacao.md#primeira-execução) |
| `## 7. Execução`: fluxo S3 (ingerir local → sincronizar por tamanho e sha256 → `dbt build --target s3`; variáveis vazias = ausentes) | duplicada → fonte | [operação, Publicação e S3](../operacao.md#publicação-e-s3) (o detalhe do sha256 foi acrescentado lá) e Primeira execução (`.env.example`) |
| `## 7. Execução`: consumo por BI e publicação opcional (ADR-0016) | mantida | §7 |
| `## 8. Segurança e privacidade`, `## 9. Riscos e mitigação`, `## 10. Índice de decisões` | mantida | §8, §9, §10 |
| — | nova | [§11. Escopo: original × adaptado × adição](../../ARCHITECTURE.md#11-escopo-original--adaptado--adição) (o antigo `docs/ESCOPO.md`) |

## `docs/ESCOPO.md` (agora arquivo-ponte, sai na v1.6.0)

| Seção antiga | Destino | Lugar novo |
|---|---|---|
| Cabeçalho: marcação `meta.escopo` (ADR-0006), `dbt ls --select tag:escopo_*`, fonte do original | movida | [ARCHITECTURE, §11](../../ARCHITECTURE.md#11-escopo-original--adaptado--adição), introdução e bloco `bash` |
| Cabeçalho: "Esta tabela é mantida pelos lotes; a versão final é consolidada na tarefa T31." | descartada | nota de processo datada (a T31 foi concluída na v1); trocada por "Mantenha a tabela ao acrescentar ou mudar um artefato" |
| Incrementos BD e IBGE (`dbt ls --select tag:incremento_*`) | movida | §11, bloco `bash` |
| Legenda | movida | §11 |
| `## Artefatos` | movida | §11, `### Artefatos` (a mesma tabela; links ajustados para a raiz) |
| `## Mapeamento de nomes de colunas (original → port)` | movida | §11, `### Mapeamento de nomes de colunas (original → port)` |

## `docs/OPERACAO.md` (v1.4.1: `docs/operacao.md`)

| Seção antiga | Destino | Lugar novo |
|---|---|---|
| Introdução | mantida | [operacao.md](../operacao.md), com o cabeçalho "Para quem" |
| — | nova | [Primeira execução](../operacao.md#primeira-execução): o que saiu do README e do ARCHITECTURE §7 |
| `## Nota de upgrade (v1.5.0)` | mantida | idem |
| `## Comandos` | mantida | idem, com a tabela nova "Outros alvos" (antes no ARCHITECTURE §7 e no README) |
| `## Fontes do IBGE`, `## Estado e ordem dos meses`, `## Retenção` | mantida | idem |
| `## Publicação e S3` | mantida | idem (+ comparação por tamanho e sha256 do `sincronizar`) |
| `## Requisitos de máquina (P14)` | mantida (ampliada) | [Requisitos e tempos medidos (P14)](../operacao.md#requisitos-e-tempos-medidos-p14): ganhou a máquina de referência, os tempos por etapa e os volumes de [execucao-real-2026-10.md](execucao-real-2026-10.md), que continua aqui como registro datado |
| `## Execuções longas`, `## Agendamento` (`### cron`, `### launchd`, `### GitHub Actions`), `## Peculiaridades dos dados reais` | mantida | idem |

## `README.md`

| Seção antiga | Destino | Lugar novo |
|---|---|---|
| Título, badge, descrição e pergunta-guia | mantida | [README](../../README.md) |
| `## Por que isso é interessante para você` | mantida | idem; o link do escopo aponta para o ARCHITECTURE §11, e há uma persona nova (consulta por agente) com o que era "Consultar em linguagem natural" |
| `## Documentos`: tabela de 15 documentos e 3 diretórios | movida (reorganizada) | [Documentação](../../README.md#documentação): 6 entradas (Conceitos, Arquitetura, Operação, Uso, Referência, Decisões) e uma linha à parte (relatórios, histórico, guia de dbt, CHANGELOG, `.specs`). PRODUCT ficou na seção do pitch; plano e execução real, no [histórico](README.md); ESCOPO, no ARCHITECTURE |
| `## Uso rápido` | movida (enxugada) | [Início rápido](../../README.md#início-rápido) (`setup`, `ci`, `pipeline`, `atualizar` e a pergunta-guia com `mf query`); `publicar`, `semantica`, `golden`, `regras` e `docs` estão em [operação, Comandos](../operacao.md#comandos) |
| `### Consultar em linguagem natural` | duplicada → fonte | a persona do pitch e o [guia de consulta](../uso/consulta-agente.md) (o que entregar ao agente); `make golden` em [operação](../operacao.md#comandos) |
| `### Primeira execução` (incluindo Migração ADR-0014 e Threads) | movida | [operação, Primeira execução](../operacao.md#primeira-execução) |
| `## Licença` | mantida | idem |

## Revisões e triagens

| Antes | Depois |
|---|---|
| `docs/historico/revisoes/<revisão>-triagem.md` (R1, R2, R3, R4, RBP, RSEM, RDIC, RRN, RIBG, RGQ) | anexada, sem mudar o texto, ao fim de `<revisão>.md`, na seção `## Triagem do líder` (título da triagem em itálico; subtítulos um nível abaixo). Links atualizados no ARCHITECTURE, nos ADRs 0013 e 0023 e na RGQ |
| `docs/historico/revisoes/pendencias.md` | mantida |

## Conteúdo descartado

Só a nota de processo do cabeçalho do ESCOPO ("a versão final é consolidada na tarefa T31"), datada e já cumprida.
