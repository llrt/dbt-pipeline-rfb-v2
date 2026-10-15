# RD — Revisão independente da reorganização da documentação (v1.5.0)

Revisor: agente RD (Traycer, Claude Opus), 2026-10-15. Não sou autor de nenhum dos commits revisados.

- **Alvo:** branch `docs/reorganizacao`, `git diff a43f60f..d5bfa48`: os 6 commits do lote D1 (mecânico) e os 10
  do D2 (consolidação). Base de comparação: o `main` em `a43f60f` (v1.4.1).
- **O que não toquei:** não alterei código, YAML, docs nem testes. O único arquivo deste commit é esta revisão.
- **Mutações:** aplicadas à mão e revertidas com `git checkout -- <arquivo>`. `git status --short` ficou vazio no fim.
- **Dado real:** não usado. As perguntas livres rodaram nas fixtures (`.tmp/ci/dados`), em conexão somente leitura.
- **Gates:**
  - `caffeinate -i make ci`: verde em 5 min 23 s (553 testes unitários, 435 de integração; links e âncoras ok em
    85 `.md`).
  - `uvx pre-commit run --all-files`: verde.
  - `make dicionario`, `make golden`, `make conceitos` e `make semantica` (com `RAIZ_DADOS=$PWD/.tmp/ci/dados`):
    verdes, sem diff depois.

## Veredito

**APROVÁVEL COMO MINOR, MAS O OBJETIVO DO USUÁRIO SÓ FOI ATINGIDO PELA METADE.** A parte mecânica e de
rastreabilidade está boa:

- não achei perda real de conteúdo;
- os links e o histórico do git estão preservados;
- os 24 doc blocks são fiéis ao texto antigo e às fontes;
- o guia do agente continua autossuficiente com o catálogo;
- o CHANGELOG bate com as releases.

O ganho, porém, foi em **portas de entrada e separação**, não em **volume nem em clareza dentro do documento**.

- Quem quer entender o negócio abre `docs/conceitos.md`: são 1.012 linhas, e as primeiras 230 são definições
  geradas.
- Logo depois, a §2 repete as mesmas definições em prosa longa, e a §5 as repete uma terceira vez, em uma linha
  (**RD-01**).
- Uma mutação mostrou que essas cópias podem divergir sem nenhum teste reprovar (**RD-02**). É o mesmo tipo de
  divergência que a reorganização queria eliminar (a RIBG-06 é o exemplo).

Recomendo corrigir **RD-01 a RD-03 antes da release**. Elas não exigem reescrever conteúdo, só movê-lo: a proposta
de cortes abaixo leva o caminho de leitura de `conceitos.md` de ~1.010 para ~510 linhas, sem perder nada. RD-04 e
RD-05 podem entrar no FD ou ser registradas como adiadas. As demais são baixas.

O que está bem:

- **README:** 63 linhas, pitch por persona mantido, um índice de 6 entradas com o "para quê" de cada uma e o
  histórico numa linha à parte. A porta de entrada ficou muito mais clara do que a tabela de 15 documentos da v1.4.1.
- **Separação por público:** `uso/`, `referencia/`, `relatorios/` e `historico/`. O histórico tem um README que diz
  "registro, não referência". As triagens anexadas reduziram as revisões de 19 para 10 arquivos.
- **Cabeçalho "Para quem / Quando ler" em todo doc vivo, com teste.** É o que mais ajuda o leitor que cai num
  documento por link.
- **ARCHITECTURE §5.3** virou uma tabela por camada que de fato resume, e o ESCOPO entrou como §11 sem perda.
- **Engenharia:**
  - `caminhos.py` é a fonte única dos caminhos;
  - o verificador de links é sólido (acentos, âncoras repetidas, `<>` e `%xx` estão certos);
  - o `git log --follow` atravessa as mudanças de lugar. `conceitos.md` herda os 16 commits da antiga
    CAMADA_SEMANTICA.

## Os 4 percursos de leitor (antes × depois)

Para cada leitor, refiz o caminho a partir do README, no `main` (`a43f60f`) e no branch.

| Leitor | v1.4.1 (`a43f60f`) | v1.5.0 (`d5bfa48`) | Onde se confunde ou o que sobra/falta |
|---|---|---|---|
| **(a) Consultor:** entender empresa × estabelecimento e abrir uma loja | Precisa adivinhar que os conceitos estão em "CAMADA_SEMANTICA (dbt/MetricFlow)": 1.019 linhas, com a parte técnica no fim. Os cenários (183 linhas) só tratam do IBGE. O relatório do caso nem está no índice. | Entrada "Conceitos" com o "para quê" certo, mas o documento tem 1.012 linhas e abre com 230 linhas de definições geradas, com ids internos à mostra (`ativa_em_operacao`). Empresa × estabelecimento aparece 3 vezes no mesmo arquivo (Definições, §2, §5). O pitch leva a `cenarios.md` (186 linhas, só IBGE, abrindo com "Como rodar" e comandos `dbt show`). As respostas de "abrir uma loja de tintas" (concorrentes, idade, porte, fornecedores, sobrevivência) estão em `relatorios/estudo-caso.md`. Esse relatório só aparece na linha "Também:" do README; nem os cenários nem os conceitos linkam para ele. | **Melhor na porta, igual em volume.** Sobra: a duplicação dentro de `conceitos.md`, a ontologia OWL e o FAQ de `mf query` no caminho de quem é de negócio. Falta: o link para o relatório do caso (RD-01, RD-05). |
| **(b) Analista de BI:** montar o Power BI | README → POWER_BI (336 linhas), autocontido, com o `erDiagram`. | README → Uso → Power BI (324 linhas). A §1 virou uma tabela tabela/papel/grão. Os relacionamentos, as cópias `dim_mes`/`dim_cnae_secundario`, a atualização incremental, o DAX e a ressalva da linha NULL ficaram. O diagrama e o detalhe de `dim_data` foram para o dicionário (2.852 linhas, gerado), com link para a âncora certa. | **Equivalente, um pouco melhor.** O guia ficou mais focado, mas o diagrama (o que o BI mais usa) agora está a um clique, dentro de um documento enorme. O pitch "Analista de BI" do README não linka o guia (baixa, sem achado próprio). |
| **(c) Operador:** agendar a atualização mensal | Comandos e primeira execução no README, mais OPERACAO (287 linhas). Requisitos espalhados entre OPERACAO e EXECUCAO_REAL. | README "Início rápido" → operação (354 linhas, um lugar só, com requisitos e tempos medidos: ótimo). A primeira tela, porém, mostra a **nota de upgrade da v1.5.0** e a **migração do ADR-0014** (variáveis renomeadas na v1.0), que não interessam a quem instala agora. Não há sumário, e o Agendamento começa na linha 273, depois de 70 linhas sobre as fontes do IBGE. | **Melhor em fonte única, pior na primeira tela** (RD-03). |
| **(d) Dev:** acrescentar uma fonte nova | ARCHITECTURE (394 linhas) + ESCOPO + ADRs + CAMADA B8 ("Como estender"). Nenhum roteiro de "fonte nova". | ARCHITECTURE (387 linhas, com o ESCOPO como §11) + a referência da camada semântica §8. Ainda não há roteiro. A reorganização **aumentou** os lugares a manter em sincronia: doc block, `make conceitos`, `make golden` e `make dicionario`, o cabeçalho, a tabela da §11, as fontes de `conceitos.md` §7, a matriz das golden queries e a ontologia. Só se descobre isso pelo CI quebrando. | **Igual, com mais peças escondidas** (RD-04). |

**As linhas de leitura** (conceitos/camada + cenários + guia + Power BI) foram de 2.354 para 2.350. A proposta
estimava ~6.000 → ~2.500 contando também REGRAS_NEGOCIO (629 linhas, que agora é referência), então o "~2.500" foi
atingido só porque o catálogo de regras saiu do caminho. Para o leitor de negócio, `conceitos.md` tem 7 linhas a
menos que a antiga CAMADA_SEMANTICA inteira.

### Proposta de cortes sem perder conteúdo (para RD-01)

| Seção de `conceitos.md` | Linhas | Para onde | Por quê |
|---|---:|---|---|
| Definições (bloco gerado) | 230 | **fim do documento, como apêndice**, absorvendo a §5 | É a terceira forma da mesma definição. Continua sendo a fonte do dicionário e do catálogo, e o leitor que quer a versão curta a acha pelo sumário. |
| §5 Glossário | 33 | fundido no apêndice | Só ficam os termos sem doc block: CNPJ básico/completo, unidade local, sigilo `X`, membro `-1`, ME/EPP, município RFB. |
| §6 Perguntas frequentes (`mf query`) | 129 | [camada-semantica.md §5 "Como usar"](../../referencia/camada-semantica.md#5-como-usar) | São comandos para quem escreve consultas, não explicação do negócio. `test_camada_semantica`/`verificar_doc_semantica` já tratam o par `(CONCEITOS, CAMADA_SEMANTICA)` como um só, então mover é barato. |
| §4 Ontologia (OWL, `classDiagram`, tabela conceito → modelo) | 107 | referência (camada semântica ou `referencia/ontologia/README.md`), deixando 1 parágrafo e o link | É referência técnica: anota modelos, colunas e métricas. |
| Introdução, §1 Bases, §2 Conceitos, §3 Ciclo de vida, §7 Fontes | ~510 | ficam | São o caminho do leitor de negócio. |

O resultado é um caminho de leitura de ~510 linhas, metade do atual, e cada conceito explicado uma vez no corpo,
com a definição curta no apêndice.

## Achados

### RD-01 — `conceitos.md` continua longo e diz cada conceito três vezes (alta, objetivo do usuário)

- **Evidência:**
  - `docs/conceitos.md:27-256` é o bloco gerado "Definições" (24 conceitos, 230 linhas), antes da §1;
  - a §2 (`:311-648`) explica os mesmos conceitos em prosa longa;
  - a §5 (`:826-858`) os resume de novo, em uma linha cada.
  - O texto do MEI abre igual em `:144` e `:466` ("é o optante pelo Simples Nacional que recolhe em valores fixos
    mensais"), e "81 mil/81.000" aparece 8 vezes no arquivo.
  - Para o leitor, "fonte única" virou "um arquivo só, com três versões dentro".
  - O pedido era "muito cheio e confuso", mas as linhas de leitura não caíram (2.354 → 2.350, relatado pelo D2 e
    conferido aqui).
- **Por que importa:** é exatamente a queixa do usuário, agora concentrada no documento mais lido.
- **Correção sugerida:** a tabela de cortes acima. Ela é só mudança de lugar e cabe no FD. Ajustar o sumário, o
  teste de cabeçalho e o `verificar_doc_semantica` (que já lê o par).

### RD-02 — nada impede a prosa da §2 de divergir do doc block (média, testes)

- **Evidência:** a mutação M4 trocou o limite do MEI na §2 (`docs/conceitos.md:470`) de R$ 81.000,00 para
  R$ 91.000,00.
  - `gerar_conceitos.py --verificar` disse "em dia".
  - Os 773 testes unitários e de integração relevantes passaram, entre eles `test_doc_semantica`,
    `test_camada_semantica` (números citados), `test_golden_queries` e `test_dicionario_dados`.
  - O documento passou a dizer 81 mil nas Definições e 91 mil na §2.
- **Por que importa:** a reorganização foi motivada por divergências desse tipo (RIBG-06). O doc block protege as
  cópias geradas (dicionário, catálogo, Definições), mas não a narrativa escrita à mão ao lado.
- **Correção sugerida:** resolver junto com o RD-01. Com uma só explicação no corpo e a definição curta num
  apêndice, o risco cai, e é a solução preferida. Se as duas formas ficarem lado a lado, um teste barato serve: os
  valores monetários e os artigos de lei citados em cada doc block têm de aparecer também na subseção da §2 com o
  mesmo título.

### RD-03 — a primeira tela de `operacao.md` é nota de upgrade e migração antiga (média, percurso do operador)

- **Evidência:**
  - `docs/operacao.md:10-14` traz a "Nota de upgrade (v1.5.0)", que repete o CHANGELOG.
  - `:31-32` traz a "Migração (ADR-0014)", com as variáveis renomeadas na v1.0, dentro de "Primeira execução".
  - Não há sumário: o Agendamento começa em `:273` de 354, depois de "Fontes do IBGE" (`:75-144`), "Estado",
    "Retenção" e "Publicação".
- **Por que importa:** o operador que chega pelo README ("antes da primeira execução real, leia a operação") lê
  primeiro o que não se aplica a ele. É a "confusão" do pedido, num documento que melhorou por ter virado fonte
  única.
- **Correção sugerida:**
  - deixar as duas notas só no CHANGELOG, com no máximo uma linha de link no fim de "Primeira execução";
  - pôr um sumário de uma linha no topo (como o de `conceitos.md`);
  - considerar levar "Fontes do IBGE" para depois de "Agendamento", porque é detalhe de comportamento, não passo
    de operação.

### RD-04 — falta o roteiro "como acrescentar uma fonte ou um modelo" (média, percurso do dev)

- **Evidência:** `git grep -niE 'nova fonte|fonte nova|como estender'` nos docs vivos só acha
  `referencia/camada-semantica.md#8-como-estender` (métricas) e a frase do ARCHITECTURE §11 ("mantenha a tabela ao
  acrescentar…"). A v1.5.0 acrescentou peças que o dev precisa conhecer:
  - doc block, quando o conceito é novo;
  - `make conceitos`, `make golden` e `make dicionario`;
  - o cabeçalho obrigatório;
  - o verificador de links.

  Elas se somam às que já existiam: `meta.escopo`/§11, `conceitos.md` §7 Fontes, a matriz das golden queries, a
  ontologia e as descrições a 100 %.
- **Por que importa:** o dev descobre cada obrigação quando o CI quebra. Mais fontes de verdade sincronizadas sem
  roteiro é exatamente o tipo de complexidade que o usuário sente como "cheio".
- **Correção sugerida:** uma seção curta "Como estender" no ARCHITECTURE (ou um `CONTRIBUTING.md`), em checklist:
  - fonte nova;
  - modelo novo;
  - conceito novo;
  - documento novo.

  Cada item com o comando ou o arquivo. Linkar do README na linha "Arquitetura".

### RD-05 — itens da proposta que não foram entregues nem registrados como adiados (média, alinhamento)

- **Evidência:** a proposta aprovada (`proposta-reorganizacao-docs`, "Estrutura proposta" e "Efeito") prevê três
  coisas que não aparecem no branch nem no CHANGELOG como adiadas:
  - **`uso/cenarios.md` com as perguntas do estudo de caso** (q1–q4, adição e IBGE): os cenários continuam só IBGE
    (186 linhas, eram 183), e as respostas de "abrir uma loja" ficam em `relatorios/estudo-caso.md`, que nenhum doc
    de uso linka;
  - **o guia do agente "enxuto"**: ele cresceu de 816 para 828 linhas. A manutenção se justifica pela
    autossuficiência do ADR-0023, decisão do líder no brief do D2, mas o desvio não está registrado;
  - **o efeito "~6.000 → ~2.500 linhas lidas"**: só foi atingido porque REGRAS_NEGOCIO virou referência (ver os
    percursos).
- Os relatórios "com o mês no nome" foram trocados por `estudo-caso.md`/`regras-negocio.md` no mapa do D1: é decisão
  do líder, e está ok.
- **Por que importa:** o usuário aprovou a proposta com esse efeito. A diferença precisa estar à vista dele, não só
  num "ponto de atenção" do andamento.
- **Correção sugerida:**
  - linkar `relatorios/estudo-caso.md` no topo de `uso/cenarios.md` e no pitch do consultor no README. É o mínimo
    para o leitor (a);
  - registrar na proposta ou no CHANGELOG o que ficou fora: a absorção das perguntas do caso e o guia enxuto
    mantido por causa do ADR-0023;
  - deixar ao usuário a decisão de fazer a absorção agora ou na v1.6.

### RD-06 — a ponte `docs/CAMADA_SEMANTICA.md` aponta só para a metade técnica (baixa, compatibilidade)

- **Evidência:** a ponte (`docs/CAMADA_SEMANTICA.md:3`) só diz "Movido para referencia/camada-semantica.md". Mas
  ~75 % do arquivo antigo (Parte A, que o README da v1.4.1 descrevia como "conceitos de negócio do CNPJ…") foi para
  `docs/conceitos.md`.
- **Por que importa:** quem chega por um link antigo para os conceitos cai na referência do MetricFlow.
- **Correção sugerida:** "A parte de negócio (antiga Parte A) foi para `conceitos.md`; a parte técnica
  (Parte B), para `referencia/camada-semantica.md`."

### RD-07 — a guarda contra caminho de `docs/` montado à mão deixa passar f-string e `os.path.join` (baixa, testes)

- **Evidência:** o regex de `tests/unit/test_caminhos.py:53`
  (`["']docs["']\s*/|/\s*["']docs["']|["']docs/`) exige aspas imediatamente antes de `docs`.
  - Mutações M2 (`f"{RAIZ}/docs/QUALIDADE_DADOS.md"`) e M3 (`os.path.join(str(RAIZ), "docs", "QUALIDADE_DADOS.md")`)
    num script: os 17 testes passaram.
  - O controle `RAIZ / "docs/QUALIDADE_DADOS.md"` foi reprovado.
- **Correção sugerida:** acrescentar `/docs/` dentro de literal (`/docs/[\w-]+`) e `"docs"` como argumento
  (`["']docs["']\s*[,)]`), ou checar por AST as constantes de string que são `docs`, começam com `docs/` ou contêm
  `/docs/`.

### RD-08 — no macOS, o verificador aceita link com caixa errada (baixa, verificador)

- **Evidência:** a mutação M1 trocou `(docs/operacao.md)` por `(docs/OPERACAO.md)` no README, e o verificador
  respondeu "links e âncoras ok". O motivo é que `Path.exists()` não distingue caixa num disco sem diferença de caixa,
  e `core.ignorecase=true` no repositório. É justamente o tipo de renomeação desta versão (`OPERACAO.md` →
  `operacao.md`). O CI no Ubuntu pega, mas o `make ci`/`make lint` local, onde o usuário trabalha, não.
- **Correção sugerida:** conferir o alvo contra o conjunto de `git ls-files` (que preserva a caixa), ou comparar
  `alvo.name` com `os.listdir(alvo.parent)`.

### RD-09 — imprecisões na tabela "seção antiga → lugar novo" e duas microperdas não registradas (baixa, rastreabilidade)

- **Evidência:**
  - Os cabeçalhos de `docs/historico/reorganizacao-v1.5.0.md:17, 42, 62, 110` dizem
    "(v1.4.1: `docs/referencia/camada-semantica.md`…)". Na v1.4.1, o arquivo era `docs/CAMADA_SEMANTICA.md`; o
    caminho citado é o do D1.
  - A linha `:116` lista "`## Nota de upgrade (v1.5.0)` | mantida" para o OPERACAO antigo, mas essa seção não
    existia em `a43f60f`: foi criada pelo D1.
  - Duas frases saíram sem registro:
    - "a fato nunca tem chave nula **nem perde linhas**" (POWER_BI antigo, convenções);
    - a segunda hierarquia de `dim_municipio` ("intermediária → imediata", POWER_BI §1 e ARCHITECTURE §5.3). As
      colunas continuam no dicionário; só a frase de hierarquia sumiu dos guias.
  - `dq_historico_testes` perdeu o "(incremental)" no ARCHITECTURE §5.3.
- **Correção sugerida:**
  - trocar "v1.4.1:" por "caminho na v1.5.0:";
  - marcar a nota de upgrade como "nova";
  - devolver as duas frases à tabela da §1 do Power BI e ao resumo do Core, ou registrá-las como resumidas.

### RD-10 — o glossário do guia não diz em que coluna está "MICRO" (baixa, guia do agente, anterior à v1.5.0)

- **Evidência:**
  - Na pergunta livre Q3 (abaixo), segui `consulta-agente.md:198` ("porte (`MICRO`, `PEQUENA`)") e filtrei
    `dim_porte.descricao_porte = 'MICRO'`. O resultado veio vazio, sem erro.
  - O valor está em `rotulo_porte`, o que só se descobre pela §12 ou consultando a dimensão.
- **Correção sugerida:** "porte (`dim_porte.rotulo_porte`: MICRO, PEQUENA, DEMAIS; `descricao_porte` é o texto
  longo)".

Notas sem achado:

- `uso/cenarios.md:9-10` diz "está na [conceitos]": sobrou de "na camada semântica".
- O doc block `mei` cita só o art. 18-A, mas "no máximo um empregado" é do art. 18-C. O texto antigo e as Fontes
  citam o 18-C; vale uma correção de uma palavra.
- O README linka o `catalogo.json` (490 KB) como entrada de referência para pessoas. Melhor apontar para a §11 do
  guia, que é o índice legível.
- Esta revisão não entrou na tabela de `docs/historico/README.md`, porque o brief pede o commit só do RD.md. O FD deve
  acrescentá-la.

## Conferência "nada se perdeu"

**Método:**

1. Comparei toda seção `##`/`###` dos 7 documentos com a tabela `reorganizacao-v1.5.0.md`.
2. Rodei um script que quebra cada documento antigo (`git show a43f60f:<arquivo>`) em frases e procura cada uma, já
   normalizada (sem alvo de link, crase ou espaços), em todos os `.md` e `.yml` versionados do branch.
3. Conferi à mão cada frase sem correspondência.

| Documento antigo | Seções conferidas | Frases sem correspondência literal | Perda real |
|---|---|---|---|
| CAMADA_SEMANTICA (1.019 linhas) | todas as A1–A7 e B1–B8, mais as subseções `####` | 9: o roteiro "duas partes", os caminhos antigos, a frase "a tabela da B3" | nenhuma; tudo foi reescrito ou religado em `conceitos.md`/`camada-semantica.md` |
| GUIA_CONSULTA (816) | §1–§12 e Exemplos 1–6 | 4: caminhos antigos e o passo 2 ampliado | nenhuma |
| POWER_BI (336) | todas | 16: a §1 antiga | a frase "nem perde linhas" e a hierarquia intermediária → imediata (RD-09); o resto está na tabela da §1, nos Relacionamentos ou no dicionário (`dim_data`: 1900-01-01, "ou a maior data observada", `yyyymmdd`, `-1`/`-2`, 1194-08-15 conferidos) |
| ARCHITECTURE (394) | §1–§10 e 4.1–5.4 | 47: os bullets da §5.3 e a tabela da §7 | nenhuma relevante: conferi no dicionário a montagem de `cnpj_completo`, as sentinelas `0`/`00000000`, a vírgula do capital, `tem_cnae_bd`, os pares simétricos sem autopares, `ano_cempre` × mês RFB, haversine entre centroides, `NÃO PERTENCE` e 1 casa decimal na idade. A "diferença zero" e o `now()` ficaram na tabela da §5.3, e o sha256 em `operacao.md`. A regra de encerramento ("situação 08") e a de sobrevivência ("início ≤ data_referencia − N") da §5.3 antiga estavam desatualizadas; as vigentes estão nos doc blocks. Só o "(incremental)" de `dq_historico_testes` sumiu (RD-09) |
| ESCOPO (77) | cabeçalho, Artefatos, Mapeamento | 2: um caminho antigo e o `dbt ls` reformatado | nenhuma; a nota "T31" foi descartada com motivo |
| OPERACAO (287) | todas | 2: um caminho antigo e uma frase quebrada pelo script | nenhuma |
| README (84) | todas | 20: a tabela de 15 documentos e "Consultar em linguagem natural" | nenhuma; a tabela foi reorganizada e o "o que entregar ao agente" está no guia e no pitch |

**Fatos específicos por amostragem**, todos presentes e iguais ao texto antigo:

- R$ 81.000,00 e R$ 6.750,00 por mês de atividade (LC 123, art. 18-A, §1º);
- PLP 186/2026;
- os artigos da IN 2.119: 5º, 9º, 24 §2º e §4º, 38 e os 90 dias;
- os 67 municípios sem questionário da REGIC;
- SIDRA 10295 e 9528;
- CEMPRE 2024 sem MEI, com 0,83 unidade local por ativo;
- o PIB até 2023 e o VA até 2021;
- 12/09/2026 como data do extrato;
- os 3.749 MEI filiais.

As 19 fontes de `conceitos.md` §7 mantêm link e data de acesso.

### Doc blocks contra o texto antigo e as fontes

Conferi 18 dos 24 doc blocks com o texto antigo (Parte A) e com as fontes citadas nele:

- empresa, estabelecimento, matriz_filial;
- situacao_cadastral, ativa_em_operacao, baixa_inaptidao;
- porte, natureza_juridica, cnae_principal;
- simples_nacional, mei;
- data_referencia, fotografia_mensal, sobrevivencia;
- cempre, renda_censo, regic_polo_compras, valor_adicionado.

Todos são fiéis. Valores, artigos e ressalvas batem:

- ME até R$ 360 mil e EPP até R$ 4,8 milhões (LC 123, art. 3º);
- os códigos de situação 1/2/3/4/8 (IN 2.119, art. 9º);
- "não se confundem com a condição de atividade" (art. 9º, parágrafo único);
- os cinco grupos CONCLA e a natureza 2135;
- CNAE 2.3 com subclasse de 7 dígitos;
- o percentual da REGIC entre os destinos de fora;
- o sigilo do CEMPRE como piso.

Única ressalva: a citação do art. 18-C no MEI (nota acima).

**Fonte única:**

- empresa × estabelecimento, situação, fotografia mensal e fontes do IBGE agora têm **um** documento para pessoas
  (`conceitos.md`) e **uma** fonte da definição curta (doc block). A repetição que sobra é a de dentro de
  `conceitos.md` (RD-01) e a do glossário do guia, que é intencional (vocabulário → coluna);
- "como rodar" está no README (4 comandos) e em `operacao.md` (tabela completa), sem conflito;
- os cenários ainda têm um "Como rodar" próprio, com `dbt show`, que é específico deles.

## Guia do agente: 3 perguntas livres só com o guia e o catálogo

Regra do teste: sem abrir `conceitos.md`. Usei a regra de camada (§2), o esquema (§3/§4), o glossário (§5), as
armadilhas e o SQL das golden queries do catálogo, e executei com `duckdb.connect(..., read_only=True)` nas fixtures.

| Pergunta | Caminho pelo guia e pelo catálogo | Resultado |
|---|---|---|
| Q1. Quantas **empresas** MEI ativas há em cada UF? | O glossário diz "empresa = matriz"; a armadilha de `gq_core__simples_mei__01` diz "para empresas MEI filtre `eh_matriz`". Adaptei o SQL com `eh_ativa and opcao_mei and eh_matriz`. | ES: 1. Certo. A definição do MEI veio do catálogo (`conceitos[].definicoes` e a descrição de `opcao_mei`). |
| Q2. Quantos estabelecimentos fecharam **de vez** por ano, e quantos só ficaram inativos? | O glossário dá "fechou → `encerramentos` × `baixas`". Usei o SQL de `gq_core__dinamica_mercado__01` e a armadilha "fechou de vez = só baixa (código 8)". | 2019–2026 com baixas ≤ encerramentos (2023: 0 baixa, 1 encerramento). Certo. |
| Q3. Qual o capital social médio das empresas MICRO ativas, por UF? | Armadilha 4 e `gq_core__capital_social__01` (só matrizes); glossário "porte (`MICRO`, `PEQUENA`)". | A primeira tentativa, com `descricao_porte = 'MICRO'`, veio **vazia, sem erro**. Com `rotulo_porte` (achado na §12): ES, AL e NI com 1 empresa cada, média de 1.000,00. Certo depois de RD-10. |

**Conclusão:** o guia continua autossuficiente com o catálogo. As definições dos conceitos chegaram pelo catálogo,
e não precisei de `conceitos.md`. 20 dos 23 conceitos do catálogo têm `definicoes`; os três sem definição
(`fornecedores_proximos`, `regras_qualidade` e `modelos_originais`) são explicados no próprio guia. O tropeço da Q3
é anterior à v1.5.0 (RD-10).

## Mecânica

| Item | Resultado |
|---|---|
| Links e âncoras | 85 `.md` sem problema. Sondas no verificador: acentos via `%C3%A7` ok; âncora repetida (`-1` existe, `-2` não) ok; `<arquivo com espaço.md>` inexistente pego; `C++ & Python` → `c--python` ok. Falsos positivos, no sentido seguro: link absoluto `/README.md` (o GitHub o resolve pela raiz), cabeçalho setext (`===`) e parênteses no nome do arquivo. Nenhum ocorre hoje. Falso negativo: caixa no macOS (RD-08). |
| Arquivos-ponte | 6 (CAMADA_SEMANTICA, DICIONARIO_DADOS, GUIA_CONSULTA, REGRAS_NEGOCIO, ESCOPO, RETRO), cada um com 3 linhas e a data de saída. Nenhum teste garante que existam até a v1.6.0 (M5); o conteúdo da ponte da camada é parcial (RD-06). Os ADRs 0015 e 0022 citam `docs/ESCOPO.md` no texto da decisão; isso está certo hoje, mas fica obsoleto quando a ponte sair. |
| `caminhos.py` | Fonte única de fato: CLI, `regras.py`, `relatorio.py`, `ibge.py`, `orquestracao.py` e os 5 scripts usam as constantes; os testes também. A guarda tem os furos do RD-07. Os links do relatório de regras são calculados a partir de `RELATORIO_REGRAS_NEGOCIO`, não do `--saida` real. Com `--saida` em outra pasta, eles ficam relativos ao lugar padrão; o comportamento é o mesmo da v1.4.1, então não é regressão. |
| Caminhos padrão de `rfb relatorio`/`rfb regras` e nota de upgrade | Os padrões mudaram para `docs/relatorios/estudo-caso.md` e `docs/relatorios/regras-negocio.md`. `--saida` e `--saida-relatorio` mantidos; os textos de ajuda vêm das constantes; a nota está no CHANGELOG e em `operacao.md`. **Minor é razoável:** nenhum comando, opção ou formato de saída muda, só o lugar padrão de um arquivo versionado que o `git mv` já levou junto, e a nota diz o que muda. Os caminhos antigos dos relatórios não têm ponte, de propósito (a proposta pedia ponte só para os mais citados). |
| `git log --follow` | Preserva a história: `referencia/dicionario-dados.md` (13 commits, desde `81baa74`), `historico/retro.md` (10), `uso/consulta-agente.md` (17), `conceitos.md` e `referencia/camada-semantica.md` (16 cada, desde `1374daa`) e `historico/revisoes/R1.md` (4). |

## CHANGELOG

As 7 entradas (v1.0.0 a v1.4.1) batem com `gh release view`:

- **v1.4.1:** 93 golden queries, 23 conceitos × 7 camadas, 21 armadilhas;
- **v1.4.0:** `--renovar-ibge`/`--sem-ibge`, RN-30, falha do IBGE como aviso, upgrade sem quebra;
- **v1.3.0:** RN-01 a RN-29, sai com 0;
- **v1.2.0:** 57 tabelas e 559 colunas;
- **v1.1.0:** 8 modelos semânticos, 26 métricas, 4 saved queries, *time spine*;
- **v1.0.1:** Fusion adiado, testes herméticos, Node 24;
- **v1.0.0:** 0 diferenças em 71,4 M linhas, CPF mascarado, ADRs 0001–0016.

As datas são as da publicação em UTC (a v1.4.0 saiu às 02:19 UTC de 15/10, ainda 14/10 no horário de Brasília),
e o critério é coerente entre as entradas. A nota de upgrade da v1.5.0 está correta e lista as 6 pontes.

## Mutações

| # | Mutação | Resultado |
|---|---|---|
| M1 | link com caixa errada no README: `(docs/operacao.md)` → `(docs/OPERACAO.md)` | **sobrevive** no macOS: "links e âncoras ok em 85 arquivos" (RD-08); o CI no Ubuntu pegaria |
| M2 | `ANTIGO = f"{RAIZ}/docs/QUALIDADE_DADOS.md"` em `scripts/gerar_qualidade_dados.py` | **sobrevive**: `test_caminhos.py` com 17 aprovados (RD-07) |
| M3 | `ANTIGO = os.path.join(str(RAIZ), "docs", "QUALIDADE_DADOS.md")` no mesmo script | **sobrevive**: 17 aprovados (RD-07) |
| M3c | controle: `ANTIGO = RAIZ / "docs/QUALIDADE_DADOS.md"` | morta: `test_nenhum_python_monta_caminho_de_docs_fora_de_caminhos` |
| M4 | limite do MEI na §2 de `conceitos.md`: R$ 81.000,00 → R$ 91.000,00, com o doc block intacto | **sobrevive**: `gerar_conceitos.py --verificar` "em dia" e 773 testes aprovados (unit, `test_doc_semantica`, `test_camada_semantica`, `test_ontologia`, `test_golden_queries`, `test_dicionario_dados`) (RD-02) |
| M5 | `git rm docs/CAMADA_SEMANTICA.md` (ponte) | **sobrevive**: verificador ok em 84 arquivos e 553 testes unitários aprovados. Nada garante as pontes até a v1.6.0 (baixa, sem achado próprio) |
| M6 | apagar a seção `## Triagem do líder` de `historico/revisoes/R1.md` (23 linhas) | **sobrevive**: verificador ok e 553 aprovados. Perda de histórico sem guarda (baixa: o histórico é registro, e o git preserva) |

As mutações do D1 e do D2 (link quebrado, âncora inexistente, caminho antigo num script, doc block sem regenerar,
doc sem cabeçalho, `doc('inexistente')` e link para `-triagem.md`) foram relatadas como mortas pelos lotes, e não as
repeti.

## Triagem do líder (2026-10-15)

Veredito da RD: **aprovável como minor, com o objetivo do usuário atingido pela metade.** As portas de entrada e a
separação por público melhoraram. O volume e a clareza dentro de `conceitos.md` não mudaram.
- São 1 achado alto, 4 médios e 5 baixos.
- Das 7 mutações da RD, 6 sobreviveram.
- Nada se perdeu, e o guia do agente segue autossuficiente (3/3).

Como o pedido do usuário era "menos cheio e confuso", **todos os achados entram antes da release**, inclusive o RD-01,
que é o centro do pedido. As correções ficam com o lote **FD**, um agente novo (Opus, esforço médio, o mesmo nível do
D2), que também faz o commit da versão 1.5.0.

| Achado | Decisão | Lote | Resolvido em |
|---|---|---|---|
| **RD-01** `conceitos.md` com 1.012 linhas diz cada conceito três vezes | **Definição uma vez, no lugar onde se lê.** Cada conceito da §2 abre com a definição do doc block, **inserida pelo gerador** no próprio lugar (bloco gerado por conceito), seguida só do complemento escrito à mão ("na prática", exemplos, armadilhas), **sem repetir** a definição. Some o bloco "Definições" do topo. A §5 (glossário) vira um índice curto, gerado: termo → link para a âncora da §2. O FAQ de `mf query` e a ontologia saem para a referência (`docs/referencia/camada-semantica.md` e `docs/referencia/ontologia/README.md`, novo). Meta: o caminho de leitura de `conceitos.md` fica abaixo de ~550 linhas, sem perder conteúdo | FD | |
| **RD-02** a prosa da §2 pode divergir do doc block (M4) | Com o RD-01, a definição só existe no doc block. Teste: o complemento escrito à mão de um conceito **não pode repetir** valores do doc block (números com 3 ou mais dígitos, valores em R$, artigos de lei). M4 tem de morrer | FD | |
| **RD-03** `operacao.md` abre com nota de upgrade e migração da v1.0 | A primeira tela traz o que é, os comandos do dia a dia e um sumário. As notas de upgrade (v1.5.0, ADR-0014) vão para uma seção final "Notas de upgrade", com link para o CHANGELOG | FD | |
| **RD-04** falta um roteiro "fonte, modelo ou conceito novo" | Seção nova no `ARCHITECTURE.md`: "Como estender", em forma de checklist (doc block, `make conceitos`/`golden`/`dicionario`, cabeçalho "Para quem", escopo/§11, fontes, matriz, ontologia, testes), sem arquivo novo | FD | |
| **RD-05** itens da proposta não entregues nem registrados | Os cenários linkam o estudo de caso: uma seção curta "Estudo de caso de Fundão" em `uso/cenarios.md`, apontando para `relatorios/estudo-caso.md`, sem copiar o relatório gerado. O enxugamento do guia do agente fica **registrado como não feito de propósito** (autossuficiência, ADR-0023) em `historico/reorganizacao-v1.5.0.md`, junto com a medida de linhas corrigida | FD | |
| **RD-06** a ponte `docs/CAMADA_SEMANTICA.md` aponta só para a parte técnica | A ponte aponta para os dois lugares: conceitos e referência técnica | FD | |
| **RD-07** a guarda de caminho deixa passar f-string e `os.path.join` | Guarda por AST: qualquer literal `"docs"` usado para montar caminho fora de `caminhos.py`. M2 e M3 têm de morrer | FD | |
| **RD-08** o verificador aceita caixa errada no macOS | O verificador compara o nome exato pelo `os.listdir`, sem depender do sistema de arquivos. M1 tem de morrer | FD | |
| **RD-09** a tabela da reorganização tem rótulo errado e duas microperdas não registradas | Corrigir o rótulo e registrar ou recuperar as duas microperdas ("nem perde linhas"; hierarquia intermediária → imediata) | FD | |
| **RD-10** o glossário não diz que "MICRO" está em `rotulo_porte` | Corrigir o glossário do guia. Também o doc block do MEI: "um empregado" é do art. 18-C, não do 18-A | FD | |
| Mutações M5 e M6 | Teste: as 6 pontes existem até a v1.6.0; toda revisão que tinha triagem tem a seção "Triagem do líder" | FD | |
