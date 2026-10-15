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

## `docs/CAMADA_SEMANTICA.md` (caminho na v1.5.0: `docs/referencia/camada-semantica.md`, inteiro)

| Seção antiga | Destino | Lugar novo |
|---|---|---|
| Introdução: "Adição" (ADR-0018) e o que a camada descreve | mantida | [camada-semantica.md](../referencia/camada-semantica.md), topo |
| Introdução: "O documento tem duas partes" | movida (reescrita) | [camada-semantica.md](../referencia/camada-semantica.md), topo: a separação em dois documentos, com link para os conceitos |
| Introdução: fontes entre colchetes, A7, números das fixtures, catálogo RN-xx | movida | [conceitos.md](../conceitos.md), introdução |
| `## Parte A — Negócio` | movida | [conceitos.md](../conceitos.md) |
| `### A1. As bases` | movida | [conceitos.md, §1](../conceitos.md#1-as-bases) |
| `### A2. Conceitos` (e todas as subseções `####`: CNPJ, Empresa × estabelecimento, Matriz × filial, Razão social × nome fantasia, Natureza jurídica, Capital social, Porte, Simples Nacional e MEI, Situação cadastral, Situação especial, Data de início de atividade, CNAE principal e secundárias, Município, CEMPRE, REGIC, Renda per capita, Valor adicionado) | movida | [conceitos.md, §2](../conceitos.md#2-conceitos), as mesmas subseções como `###`, com as mesmas âncoras. A definição curta de cada conceito central passou a ser doc block do dbt e abre a subseção do conceito; o texto que só a repetia saiu (ver [Ajustes da revisão RD](#ajustes-da-revisão-rd-lote-fd)) |
| `### A3. Ciclo de vida` | movida | [conceitos.md, §3](../conceitos.md#3-ciclo-de-vida) |
| `### A4. Ontologia` | movida | [referência da ontologia](../referencia/ontologia/README.md) (diagrama, afinidade e a tabela "Onde cada conceito está no projeto"); em [conceitos.md, §4](../conceitos.md#4-ontologia), um parágrafo com o link |
| `### A5. Glossário rápido` | duplicada → fonte | [conceitos.md, §5](../conceitos.md#5-glossário): índice gerado, termo → definição; os termos sem doc block (CNPJ básico e completo, ME/EPP, unidade local, sigilo, membro `-1`, município RFB) ligam à subseção que os explica, e o parágrafo que liga ao glossário do guia ficou |
| `### A6. Perguntas frequentes` | movida | [camada-semantica.md, §5, Perguntas frequentes](../referencia/camada-semantica.md#perguntas-frequentes) (são comandos `mf query`; links ajustados) |
| `### A7. Fontes` | movida | [conceitos.md, §6](../conceitos.md#6-fontes) |
| `## Parte B — Estrutura técnica` | mantida | [camada-semantica.md](../referencia/camada-semantica.md), agora o documento inteiro |
| `### B1. Onde está e em qual padrão` | mantida | [§1](../referencia/camada-semantica.md#1-onde-está-e-em-qual-padrão) |
| `### B2. Entidades e junções` | mantida | [§2](../referencia/camada-semantica.md#2-entidades-e-junções) |
| `### B3. Métricas` | mantida | [§3](../referencia/camada-semantica.md#3-métricas) (âncora antiga `#b3-métricas`) |
| `### B4. Consultas salvas` | mantida | [§4](../referencia/camada-semantica.md#4-consultas-salvas) |
| `### B5. Como usar` | mantida | [§5](../referencia/camada-semantica.md#5-como-usar) |
| `### B6. Garantias (testes)` | mantida | [§6](../referencia/camada-semantica.md#6-garantias-testes) |
| `### B7. Limites e cuidados` | mantida | [§7](../referencia/camada-semantica.md#7-limites-e-cuidados) |
| `### B8. Como estender` | mantida | [§8](../referencia/camada-semantica.md#8-como-estender) |

## `docs/GUIA_CONSULTA_LINGUAGEM_NATURAL.md` (caminho na v1.5.0: `docs/uso/consulta-agente.md`)

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

## `docs/POWER_BI.md` (caminho na v1.5.0: `docs/uso/power-bi.md`)

| Seção antiga | Destino | Lugar novo |
|---|---|---|
| Introdução, resumo e tamanho do resumo mensal | mantida | [power-bi.md](../uso/power-bi.md), topo, com o cabeçalho "Para quem" |
| `## Como o Power BI acessa os dados` e `### 1. Parquet`, `### 2. Arquivo DuckDB local`, `### 3. MotherDuck`, `### Qual escolher`, `### Fontes oficiais` | mantida | [Como o Power BI acessa os dados](../uso/power-bi.md#como-o-power-bi-acessa-os-dados) |
| `## 1. O modelo estrela`: diagrama `erDiagram` | duplicada → fonte | [dicionário, Modelo estrela](../referencia/dicionario-dados.md#modelo-estrela) (gerado das chaves) e a tabela de [Relacionamentos](../uso/power-bi.md#relacionamentos), que continua no guia |
| `## 1. O modelo estrela`: `dim_mes` e `dim_cnae_secundario` são cópias; natureza jurídica fora do resumo | mantida | [§1](../uso/power-bi.md#1-o-modelo-estrela), texto abaixo da tabela |
| `## 1. O modelo estrela`: convenções (`sk_*` inteiras, membro `-1`: "a fato nunca tem chave nula nem perde linhas") | mantida (resumida) | §1, texto abaixo da tabela; detalhe no [dicionário](../referencia/dicionario-dados.md). O "nem perde linhas" tinha saído no D2 e voltou no FD (RD-09) |
| `## 1. O modelo estrela`: `dim_data` de 1900-01-01 até a data de referência, `sk_data = yyyymmdd`, `sk_mes_referencia = yyyymm01` | duplicada → fonte | `dim_data` e `fct_resumo_mensal` no [dicionário](../referencia/dicionario-dados.md); o `yyyymm01` ficou na tabela da §1 |
| `## 1. O modelo estrela`: membros `-1` (1899-12-31) e `-2` (1899-12-30, ex.: 1194-08-15), só a fato detalhada aponta para `-2` | mantida (movida dentro do guia) | bullet "Tabela de datas" de [Relacionamentos](../uso/power-bi.md#relacionamentos) e a linha de `dim_data` da tabela da §1; o exemplo 1194-08-15 está no dicionário |
| `## 1. O modelo estrela`: hierarquias em colunas | mantida (resumida) | §1, última frase, com as duas hierarquias de `dim_municipio` (região → … → município e intermediária → imediata; a segunda tinha saído no D2 e voltou no FD, RD-09); as colunas no [dicionário](../referencia/dicionario-dados.md) |
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
| `### 5.3 Modelos`: bullets por modelo (staging, intermediate, original, core, análises, observabilidade, golden queries) e o `erDiagram` do core | duplicada → fonte | tabela-resumo por camada na [§5.3](../../ARCHITECTURE.md#53-modelos), que no FD recuperou duas microperdas do D2 (RD-09): as hierarquias de `dim_municipio` no Core e o "incremental" de `dq_historico_testes`; a descrição de cada modelo e coluna está no [dicionário](../referencia/dicionario-dados.md), gerado dos YAMLs, e o diagrama em [Modelo estrela](../referencia/dicionario-dados.md#modelo-estrela). A frase de `mart_dinamica_mercado` ("encerramentos (situação 08 com `dat_situacao`)") estava desatualizada: a regra vigente (todo não ativo) está na descrição do modelo e no doc block `abertura_encerramento` |
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

## `docs/OPERACAO.md` (caminho na v1.5.0: `docs/operacao.md`)

| Seção antiga | Destino | Lugar novo |
|---|---|---|
| Introdução | mantida | [operacao.md](../operacao.md), com o cabeçalho "Para quem" |
| — | nova | [Primeira execução](../operacao.md#primeira-execução): o que saiu do README e do ARCHITECTURE §7 |
| — | nova (D1) | `## Nota de upgrade (v1.5.0)`, criada no D1; no FD foi para [Notas de upgrade](../operacao.md#notas-de-upgrade), no fim (RD-03) |
| `## Comandos` | mantida | idem, com a tabela nova "Outros alvos" (antes no ARCHITECTURE §7 e no README) |
| `### Primeira execução` do README: "Migração (ADR-0014)" | movida | no D2, para Primeira execução; no FD, para [Notas de upgrade](../operacao.md#notas-de-upgrade), com a v1.5.0 e um resumo da v1.4.0 (RD-03) |
| `## Fontes do IBGE`, `## Estado e ordem dos meses`, `## Retenção` | mantida | idem; no FD, Fontes do IBGE passou para depois de Agendamento (RD-03) |
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

## Ajustes da revisão RD (lote FD)

A [revisão RD](revisoes/RD.md) achou que `conceitos.md` dizia cada conceito três vezes: no bloco "Definições" do
topo, na prosa da §2 e na tabela da §5 (RD-01). No lote FD, a definição de cada conceito passou a existir **uma
vez**, no lugar onde se lê: o `make conceitos` a insere no começo da subseção, e o texto escrito à mão em volta é só
o complemento, que um teste impede de repetir os valores da definição (RD-02).

| Antes (D2) | Agora | O que mudou |
|---|---|---|
| `## Definições`: bloco gerado com os 24 doc blocks, antes da §1 | a definição de cada um abre a subseção do conceito, na §2 ou na §3 | o mesmo texto; a âncora `#def-<nome>` continua. Conceitos sem subseção ganharam uma: "Concorrência e área de mercado" (§2) e, na §3, "O que o extrato mensal mostra" (data de referência e fotografia), "Aberturas, encerramentos e sobrevivência" e "Lotes de inaptidão e período parcial" |
| §2: a prosa de cada conceito | §2: só o complemento | saiu a frase que repetia a definição; ficou o que ela não tem (base legal detalhada, exemplos e números do dado, colunas). Lista abaixo |
| §3: tabela "Ligação com as métricas" (pergunta, métrica, regra) | uma frase com as métricas | as regras de cada métrica são as definições de abertura, encerramento e sobrevivência, logo acima |
| §3: nota "Empresa × estabelecimento no ciclo de vida" | "filtre `eh_matriz`" em [Situação cadastral](../conceitos.md#situação-cadastral) | o resto ("situação da empresa = a da matriz", "empresa ATIVA com filiais baixadas") está na definição de situação cadastral |
| §4 Ontologia (107 linhas) | [referencia/ontologia/README.md](../referencia/ontologia/README.md) | movida inteira; em `conceitos.md` ficou um parágrafo com o link |
| §5 Glossário (tabela de 23 termos) | índice gerado, termo → definição | ver a linha A5 acima |
| §6 Perguntas frequentes (129 linhas) | [camada-semantica.md, §5](../referencia/camada-semantica.md#perguntas-frequentes) | movida inteira |
| §7 Fontes | §6 Fontes | só a numeração |
| §2, Simples Nacional e MEI: "Mudança já publicada: Resolução CGSN nº 190/2026" (com a CGSN 194) e "Mudança em discussão: PLP nº 186/2026" (com a contradição do MEMP) | [referencia/regras-negocio.md, Mudanças na lei do Simples e do MEI](../referencia/regras-negocio.md#mudanças-na-lei-do-simples-e-do-mei) | movidas depois do reteste, por decisão do líder; em `conceitos.md` ficou uma frase com o link para cada uma, e a vigência do regime (art. 88 e LC 128) ficou. Lá o texto diz de novo "R$ 81 mil" e "R$ 81.000,00", que em `conceitos.md` tinham virado "o limite atual" |

Fora de `conceitos.md`, o FD também mudou:

| Documento | O que mudou |
|---|---|
| [operacao.md](../operacao.md) | a primeira tela traz a tabela dos 4 comandos do dia a dia e um sumário; a nota de upgrade da v1.5.0 e a migração do ADR-0014 foram para "Notas de upgrade", no fim; Fontes do IBGE passou para depois de Agendamento (RD-03) |
| [ARCHITECTURE.md](../../ARCHITECTURE.md#12-como-estender) | §12 nova, "Como estender", com o checklist de fonte, modelo, conceito e documento novos (RD-04) |
| [uso/cenarios.md](../uso/cenarios.md#estudo-de-caso-de-fundão) | seção nova "Estudo de caso de Fundão", que aponta para o [relatório do caso](../relatorios/estudo-caso.md) sem copiá-lo; o README liga o relatório no pitch do consultor (RD-05) |
| [referencia/camada-semantica.md](../referencia/camada-semantica.md#perguntas-frequentes) | recebeu as perguntas frequentes de `conceitos.md` (§5) |
| [referencia/ontologia/README.md](../referencia/ontologia/README.md) | nova, com a antiga §4 de `conceitos.md` |
| [docs/CAMADA_SEMANTICA.md](../CAMADA_SEMANTICA.md) (ponte) | aponta para os dois lugares: conceitos (Parte A) e referência técnica (Parte B) (RD-06) |

**Não feito de propósito** (RD-05). A proposta de reorganização aprovada pelo usuário previa três coisas que a
v1.5.0 não entrega:

- **Os cenários com as perguntas do estudo de caso.** Os cenários continuam com as cinco perguntas do IBGE e agora
  apontam para o relatório do caso; as respostas de "abrir uma loja" (concorrentes, idade, porte, fornecedores,
  sobrevivência) ficam no relatório, que é gerado do dado real a cada mês. Absorvê-las nos cenários fica para a v1.6, se
  o usuário quiser.
- **O guia do agente enxuto.** Ele foi de 816 para 828 linhas: o agente recebe só o guia e o catálogo
  ([ADR-0023](../adr/0023-golden-queries-e-guia-para-agente.md)), e o guia precisa continuar autossuficiente (a RD
  confirmou com 3 perguntas livres). O ganho foi tirar dele as definições, que agora vêm do catálogo.
- **O efeito "~6.000 → ~2.500 linhas lidas".** Medido de novo no FD, só o caminho de leitura de quem é de negócio
  (conceitos + cenários + guia do agente + Power BI): 2.354 linhas na v1.4.1 (CAMADA_SEMANTICA + cenários + guia +
  POWER_BI), 2.350 no D2 e **2.037** no FD (`conceitos.md`: 1.019 → 1.012 → 687, das quais 50 são marcadores
  invisíveis do bloco gerado). O "~2.500" da proposta contava também o REGRAS_NEGOCIO (629 linhas), que virou
  referência e saiu desse caminho.

**O que saiu de cada complemento por repetir a definição** (e onde o fato está agora: sempre na definição do
mesmo conceito, salvo indicação):

- **Empresa × estabelecimento:** as definições de empresa e de estabelecimento em lista, a frase "uma empresa tem
  um ou mais estabelecimentos" e a divisão dos atributos. Ficou a definição legal completa (citação da IN), o art. 4º,
  a fato e as métricas, e os números das fixtures.
- **Matriz × filial:** "vale 1 (matriz) ou 2 (filial)", "a baixa da matriz implica a baixa de todas as filiais
  [art. 24, § 2º]" e "todo básico tem matriz". Ficaram as colunas, a leitura dos arts. 4º e 9º, o art. 21 e os números
  de 2026-09.
- **Natureza jurídica:** "é a forma jurídica… cinco grupos", "o código 2135" e "para achar MEI, use `opcao_mei`".
  Ficaram a tabela de exemplos, o ente federativo, o MEI na lei (art. 966 do CC, art. 18-A, § 1º) e os números do
  dado real.
- **Capital social:** "é o capital da empresa, repetido em cada estabelecimento; some só nas matrizes". Ficaram a
  coluna e as métricas.
- **Porte:** a coluna "limite de receita" da tabela (R$ 360 mil e R$ 4,8 milhões, art. 3º), "o porte é declarado",
  "os dados abertos não trazem a receita", "MEI não é porte" e "não informado de dois jeitos". Ficaram os códigos, os
  incisos I e II do art. 3º, a Lei 8.934, a redação da LC 155 e o rótulo do seed; entrou "MICRO, PEQUENA e DEMAIS
  estão em `rotulo_porte`" (RD-10).
- **Simples Nacional e MEI:** "a opção é anual", "a flag é a situação no extrato", "sem registro vira `false`", o
  art. 12, o art. 18-A sem parágrafo, "receita até R$ 81.000,00", "um único estabelecimento", "no máximo um empregado
  [art. 18-C]", "todo MEI é optante pelo Simples; o contrário não vale" e o "filiais fazem a contagem passar do
  número de empresas". Ficaram o nome legal do regime, os arts. 16, 88 e 18-E, a CGSN 140/190/194, o ano anterior, o
  ano de abertura (R$ 6.750,00), o transportador (R$ 251.600,00), as 3.749 filiais, o PLP 186/2026 e as colunas. A
  citação do "um empregado" passou ao art. 18-C na definição (RD-10).
- **Situação cadastral:** "está numa de cinco situações [art. 9º]", a fonte "art. 9º" da linha ATIVA, o bullet
  "ativa não quer dizer em operação" (é a definição `ativa_em_operacao`) e "a inaptidão chega em lotes" (definição
  `baixa_inaptidao`). Ficaram a tabela das situações, o "pode" dos arts. 31 e 38, o ADE (art. 39), o motivo, a data
  da situação e a ressalva R3-19.
- **CNAE principal e secundárias:** "mantida pela CONCLA, versão 2.3, cinco níveis", "um principal e zero ou mais
  secundários", "como `4741500`" e "secundária não entra em `cnae__codigo_subclasse = '4741500'`". Ficaram a tabela
  do exemplo, as colunas, `dim_cnae` e a ponte.
- **Município:** "código da tabela da RFB, 4 dígitos, não é o IBGE" e "sem par, membro `-1`". Ficaram o nome do campo
  no leiaute, a conversão `codigo_rfb` → `id_municipio_ibge`, a RN-19 e o seed de exceções.
- **CEMPRE:** "reúne empresas e organizações formais ativas", "os MEI ficam de fora", "o projeto não imputa, o valor
  fica NULL e somar subestima" e "31/12, hoje 2024". Ficaram os critérios de entrada desde 2022, os 71,6 %, a
  comparação em colunas, os números de 2026-09, o `X` e `tem_sigilo`.
- **REGIC:** os cinco níveis por extenso, "os 67 municípios não têm polo" e "45 % em Serra quer dizer 45 % de quem
  compra fora". Ficaram os subníveis, o método do questionário, a Q2, "Outros" e o empate, "não diz quanto fica no
  município", a ponte e a malha.
- **Renda per capita:** a definição inteira (SIDRA 10295, nominal, média × mediana). Ficaram o exemplo de Vitória, os
  5.570 municípios e o tratamento do `...`.
- **Valor adicionado:** a definição inteira ("somam 100", PIB até 2023, VA até 2021). Ficaram as colunas e o exemplo
  de VA negativo.
- **§3:** "comparando dois extratos se vê a variação líquida", "um inativo reativado deixa de contar como
  encerramento", a regra de cada métrica e a definição de sobrevivência na tabela. Ficaram as transições
  intermediárias, as métricas da variação, o CNPJ que some do extrato, o notebook 2.2 e os lotes de inaptidão.

Nada subiu da prosa para os doc blocks além da citação do art. 18-C no MEI: os fatos centrais de cada complemento
já estavam na definição.

## Conteúdo descartado

Só a nota de processo do cabeçalho do ESCOPO ("a versão final é consolidada na tarefa T31"), datada e já cumprida.
