# RETRO — port do MVP RFB/CNPJ para dbt + DuckDB (v1 e pós-v1 até a v1.4.0)

> Retrospectiva do líder (agente Traycer "Migração dbt DuckDB MVP v2", Claude Opus 5.5).
> - Seções 1–7: v1, de 28/09 a 01/10/2026.
> - Seção 8: pós-v1, de 01/10 a 13/10/2026 (v1.0.0 a v1.3.0).
> - Seção 9: pós-v1.3, de 13/10 a 14/10/2026 (avaliações e v1.4.0).
>
> Custos por agente: [docs/CUSTOS_AGENTES.md](docs/CUSTOS_AGENTES.md). Decisões: `.specs/STATE.md` (AD-001..AD-043)
> e `docs/adr/` (0001–0022). Revisões: `docs/revisoes/`.

## 1. O que foi entregue

| Área | Resultado |
|---|---|
| Port do original | Notebooks 1–4 do MVP Databricks reproduzidos em dbt-core + dbt-duckdb sobre Parquet local/S3: `bh_empresas`, `agg_empresas`, estudo de caso (q1–q4) |
| Fidelidade | Paridade linha a linha com a **tradução literal do SQL original**: 0 diferenças em 71,4 M linhas (2026-09) e 62,6 M (fev/2025); números do notebook 4 reproduzidos em fev/2025 (1 ativa + 4 inativas, MICRO; idade 3,8 × 3,9 explicada pela data de referência) |
| Adições | Modelo estrela para Power BI (chaves inteiras, membros −1/−2, `dim_data`, série mensal particionada), análises novas (concorrência, sobrevivência por coorte, dinâmica, fornecedores por distância), DQ (DV de CNPJ, taxa de conversão tipada, reconciliações, histórico de testes, catálogo gerado), relatório gerado |
| Melhorias pedidas no caminho | Atualização mensal (`rfb atualizar`), modelo estrela/guia Power BI, enriquecimento com a Base dos Dados (incremento `enriquecimento_bd`: Censo 2022, regiões metropolitanas, vizinhança, área de mercado com vazios), publicação opcional no MotherDuck, guia dbt ampliado, revisão de boas práticas, máscara de CPF |
| Operação real | `rfb pipeline` em 2026-09: 73,4 M estabelecimentos, PASS=339 WARN=14 ERROR=0, 339 s com o raw presente (download de 7 GB ~21 min); `rfb atualizar` no-op em 0,56 s |
| Qualidade do código | `make ci` ~130 s (unit + lint + freshness + 2 meses + backfill + ~124 testes de integração); 107 ACs da spec com evidência (Verifier da R4); 32 merges em `main`, 256 commits |

## 2. Processo: o que funcionou

- **Lotes pequenos, agente novo por lote, worktree por lote e verificação pelo líder antes de cada merge.**
  Em todo lote o líder reexecutou `make ci`, consultou o gold e rodou ao menos uma **mutação própria**.
  Isso pegou problemas que o relatório do worker não mostrava: referências inventadas no guia (B9b),
  vazios de mercado para CNAE desconhecido (B12), lentidão que era sleep do Mac (B7).
- **Revisões independentes com dados reais.** A R2 reprovou a paridade só por rodar sobre o extrato real
  (espaço nas bordas); a R3 achou o capital social inflado 15,6×, a tabela "leve" de 22 M linhas e o
  calendário desde 1194; a R4 achou CPF completo em 12,5 M nomes. Nenhum desses aparecia nas fixtures.
- **Testes de mutação como métrica de revisão.** Cada revisão rodou de 20 a 28 mutações; as sobreviventes viraram
  testes nos lotes de correção. Ao fim, as mutações sobreviventes das revisões anteriores morrem no próprio dbt/CI.
- **Paridade com tradução literal do SQL original** (EXCEPT ALL → hash por linha) como rede de segurança:
  toda adaptação precisou ser **declarada** (trim, `upper` da q4, dedup de raiz, máscara de CPF) e alinhada.
- **Spec viva com emendas rastreáveis** (EARS + `tasks.md` validado por script + `STATE.md` com decisões).
- **Escada de escalonamento de modelos**: DeepSeek (P/NC) → Sonnet (M/NC) → Opus (crítico/E2E/revisões).

## 3. Achados de produto (dados reais)

1. **O "nada nas imediações" do notebook 4 era um bug**: comparava município em MAIÚSCULAS com a grafia mista
   da Base dos Dados e sempre achava 0. Com a comparação corrigida (adaptação declarada), fev/2025 mostra
   1 fabricante na microrregião de Fundão, 12 atacadistas e 155 estabelecimentos com CNAE de fornecedor.
2. **Fundão perdeu sua única loja de tintas ativa** entre fev/2025 e 2026-09 (0 ativas, 5 inativas), mas a área
   de mercado tem 57 ativas nos vizinhos e 182 na RM Grande Vitória.
3. **Dados pessoais escondidos em dado "de empresa"**: 12,5 M razões sociais de EI/MEI terminam em CPF completo
   (e 908 o trazem no meio). Mascarado no gold por decisão do usuário (ADR-0008).
4. **A RFB mudou sob nossos pés**: primeiro CNPJ alfanumérico real (Banco do Brasil), raiz de CNPJ duplicada,
   bytes C1 no latin-1, datas de 1194; Base dos Dados com caminho de download congelado em 2023 (população e PIB
   em 2021 — corrigido para 2025/2023 pela API atual) e um município criado em 2025 sem código RFB.

## 4. O que não funcionou ou custou caro

| Problema | Efeito | Lição |
|---|---|---|
| DeepSeek no B2 (`finish=length`) | lote perdido, refeito em Sonnet | modelo pequeno + arquivo grande numa resposta = falha; pedir escrita incremental sempre |
| Gemini 3.8 Flash no guia (B9b) | caminhos, checks e SQL "compilado" inventados; 43 erros técnicos na RBP | modelo rápido para texto longo exige verificação por script (caminhos/nomes contra o manifesto) e revisão técnica independente; com protocolo explícito ele corrigiu bem |
| Brief do líder com nome errado (`paridade` como domínio) | retrabalho (P13/R2-08) | a convenção de idioma (ADR-0014) vale também para os briefs; o líder errou e o usuário apontou |
| Mac em sleep com DarkWake a cada 15 min | `make ci` de 20 s levando 16 min; diagnósticos falsos de lentidão | `caffeinate -i` em todo comando longo; olhar `pmset -g log` antes de culpar o código |
| Testes que afirmavam fixtures, não regras | mutações sobrevivendo em R3/RBP/R4 | unit tests de regra + invariantes no dbt, não só pytest sobre fixtures |
| Gold "corrente" × backfill (P22) | três rodadas (B7b, B8, F4) até ficar seguro | caminho alternativo que grava no destino final precisa dos mesmos gates e de área temporária + promoção atômica (lição L-003) |
| `temp_directory` (RBP-01 → B8) | a correção da RBP quebrou com spill no DuckDB 1.5; virou `config_options` | conferir o efeito real (`current_setting`) e rodar em dado real antes de fechar |
| Meta de CI < 120 s | ultrapassada ao incluir unit + lint + freshness + integração | metas de tempo mudam com o escopo do CI; revisar a meta junto (AD-026) |

## 5. Lições para os próximos projetos

1. **Verificação por evidência do líder em todo merge** (gates + consulta ao dado + mutação própria) é barata e
   pegou erro em ~1/3 dos lotes.
2. **Rodar em dado real cedo** (já na R2): fixtures sintéticas não mostram espaços, CPFs, códigos novos, datas absurdas.
3. **Declarar adaptações** em vez de "corrigir" o original em silêncio; a paridade literal obriga isso.
4. **Para documentação gerada por modelo, script de verificação contra o repositório** (caminhos, nomes no manifesto,
   linhas citadas) antes de qualquer revisão humana.
5. **Uma pendência por linha com dono e lote** (`pendencias.md`) evita que achados se percam entre revisões.
6. **Lições do Verifier** (`.specs/LESSONS.md`): provar regravação apagando antes (L-001); emenda de fixture
   atualiza todos os ACs que citam o valor (L-002); caminho alternativo de build com os mesmos gates (L-003).

## 6. Custo (resumo)

Detalhe por agente em [docs/CUSTOS_AGENTES.md](docs/CUSTOS_AGENTES.md). Total **US$ 247,38 ≈ R$ 1.295**
(câmbio R$ 5,2353), dos quais **US$ 236,83 são equivalente de API da assinatura Claude** (sem desembolso adicional)
e **US$ 10,55 foram cobrança real do OpenRouter** (Gemini 3.8 Flash US$ 10,23; DeepSeek v4 Flash US$ 0,32).

| Papel | US$ | % |
|---|---:|---:|
| Líder (planejamento, verificação de cada merge, triagens, docs) | 88,11 | 36 % |
| Implementação (17 lotes) | 77,74 | 31 % |
| Correções pós-revisão (9 lotes) | 42,46 | 17 % |
| Revisões independentes (5) | 39,07 | 16 % |

Leituras: revisão + correção ≈ um terço do custo e foram responsáveis pelos achados mais valiosos; o lote mais caro
foi o B8 (US$ 16,25, E2E real); Opus 5.5 respondeu por 69 % do custo (líder, críticos e revisões).

## 7. Pós-entrega (fora da v1)

- **Fase 2 da Base dos Dados** (BigQuery: pirâmide etária, RAIS, exportadoras) — AD-029; estimativa construir
  ≈ US$ 28–36 equivalente (R$ 150–190), operar ≈ R$ 0/mês.
- **1ª publicação real no MotherDuck** (P25) e confirmação da transação no `md:`.
- **Power BI de fato carregado** (único Success Criterion sem evidência na R4) e medidas DAX testadas.
- Mês real seguinte (2026-10) via `rfb atualizar`.
- *(Resolvido após a entrega)* **GitHub Actions**: o 1º run no repositório publicado falhou porque o Makefile usava `set -o pipefail` e o `/bin/sh` do Ubuntu é `dash` (no macOS é bash); corrigido com `SHELL := /bin/bash`, run verde em ~6,5 min. Lição: o CI local roda no mesmo SO do desenvolvedor — fixe o shell do make.
- *(Resolvido após a entrega)* **Avisos do CI**: as actions rodavam em Node 20 (descontinuado nos runners) e o `ubuntu-latest` migra para o Ubuntu 26 em 2026-10-19. Atualizadas para Node 24 (checkout v7.0.1, setup-uv v10.2.0, cache v6.1.0, ainda por SHA), runner fixado em `ubuntu-24.04` e `workflow_dispatch` para disparo manual; 3 runs verdes (AD-034). Lição: run verde com anotações amarelas é dívida com data marcada — fixar o runner e revisar as actions junto com o pin por SHA.
- **Release [v1.0.0](https://github.com/llrt/dbt-pipeline-rfb-v2/releases/tag/v1.0.0)** publicada no GitHub (tag anotada em `8294e6e`, CI verde), com a lista de features; versão do pacote 1.0.0.
- **dbt Fusion (dbt v2)**: avaliado em 2026-10-02 e **adiado** ([ADR-0017](docs/adr/0017-avaliacao-dbt-fusion.md)); reavaliar quando os critérios do ADR forem atendidos. O `dbt-autofix` dos YAMLs já foi aplicado (lote AF, AD-036), e no v2 resta só o bloqueio do `options`.
- **Incidente (2026-10-02): teste não hermético publicou no MotherDuck real.** Com o token real no `.env`, o
  `test_cli_sem_variaveis_sai_com_zero` apagava as variáveis do ambiente, mas a CLI as relia do `.env` e publicava 3 tabelas
  sintéticas (`dim_x`, `dim_y`, `fct_serie`) no banco `dbt_rfb`. Correção: `tests/conftest.py` desliga o `load_dotenv`
  em todos os testes (AD-036). As 3 tabelas foram removidas pelo usuário em 2026-10-06; incidente encerrado. Lição: teste que remove variáveis de ambiente precisa também isolar as fontes que as
  recarregam (`.env`); revisar isso quando um segredo real passa a existir na máquina.
- Sugestões R4-11 pendentes: warn de controles C1 nos nomes, raiz alfanumérica em teste de unidade,
  gitleaks/detect-secrets, teto de descompressão contra zip bomb.
- *(Resolvido após a entrega)* **Limpeza**: 32 worktrees integrados/órfãos e ~49 GB de cópias de dados reais removidos com aprovação do usuário (AD-031).

## 8. Pós-v1: v1.1.0 a v1.3.0 (01/10 a 13/10/2026)

### 8.1 O que foi entregue

| Versão | PR | Entrega |
|---|---|---|
| v1.0.0 / v1.0.1 | — (direto em `main`, antes da regra de PR) | Repositório público, CI no GitHub (shell, Node 24, runner fixado), avaliação do dbt Fusion (ADR-0017, adiado), YAML no formato `config:` (lote AF), testes herméticos sem `.env` |
| [v1.1.0](https://github.com/llrt/dbt-pipeline-rfb-v2/releases/tag/v1.1.0) | [#1](https://github.com/llrt/dbt-pipeline-rfb-v2/pull/1) | Camada semântica dbt/MetricFlow (26 métricas, fotografia mensal, saved queries); Parte A de negócio com fontes primárias; ontologia OWL com testes (ADR-0018) |
| [v1.2.0](https://github.com/llrt/dbt-pipeline-rfb-v2/releases/tag/v1.2.0) | [#3](https://github.com/llrt/dbt-pipeline-rfb-v2/pull/3) | Dicionário de dados gerado (57 tabelas, 559 colunas, campo do leiaute oficial, linhagem, nulidade com aviso) (ADR-0019) |
| [v1.3.0](https://github.com/llrt/dbt-pipeline-rfb-v2/releases/tag/v1.3.0) | [#4](https://github.com/llrt/dbt-pipeline-rfb-v2/pull/4) | 29 regras de negócio com fonte, checks em `analyses/`, `rfb regras` sem falhar o build, relatório do dado real de 2026-09 (16 regras com inconsistência, nenhuma acima de 0,5 %) (ADR-0020) |

### 8.2 Processo: o que mudou
- **Tudo por PR** desde 09/10, a pedido do usuário. O merge fica com o usuário, salvo quando o pedido já inclui a
  release ("nova versão minor se buildar no CI").
- **Erro do líder corrigido pelo usuário.** O lote AF e a camada semântica inicial foram feitos **no contexto do
  líder**, sem implementador nem revisor de contexto limpo. O usuário cobrou: "isso é muito importante para a
  qualidade do projeto". A partir daí, toda mudança seguiu a dinâmica original:
  - implementador novo;
  - verificação do líder por evidência;
  - revisor independente (Opus alto);
  - correções por outro agente novo;
  - PR com CI e Greptile.
- **Três camadas de revisão, e cada uma achou o que as outras não acharam:**
  - **Verificação do líder.** A mutação própria pegou lacunas que os autores não viam: datas inválidas sem teste (FSEM), FK declarada sem teste (FDIC), fronteira do mesmo dia na RN-27 (FRN). Também conferiu fatos na fonte: limite do MEI e PLP 186/2026 (FNEG), os 54 campos do leiaute no PDF (DIC).
  - **Revisores independentes** (RSEM 12 achados, RDIC 11, RRN 10). Os achados mais valiosos vieram do **dado real**: a fotografia mensal que devolve mês antigo sob filtro, 44 % dos encerramentos de 2026 como inaptidões em lote, a RN-13 marcando como "futuro" o dia seguinte ao extrato, a RN-05 contando 3.247 empresas MEI quando só 33 violam.
  - **Greptile:** 3 + 2 + 2 comentários P2, todos procedentes. Pegou divergências de regra com o mart, versão mínima, limiares `warn_if`/`error_if`, situação desconhecida e mês do relatório. Revisou de novo depois de cada correção e fechou as threads.

### 8.3 Achados de produto
1. **"Ativa" no cadastro não quer dizer "em operação"**, e "encerramento" no projeto inclui inaptidões declaradas em lote
   pela RFB. Daí a métrica `baixas` (só BAIXADA).
2. **O extrato tem corte D+1:** 1.038 datas caem exatamente no dia seguinte ao token do arquivo. **A opção pelo Simples
   para 2027** aparece com data futura legítima (CGSN 190/194/2026).
3. **Inconsistências reais do cadastro (2026-09), todas abaixo de 0,5 %:**
   - 2.427 filiais que começaram depois do fim da matriz;
   - 1.236 empresas MEI com natureza de sociedade;
   - 3.488 estabelecimentos com CNAE secundário repetido;
   - 33 empresas MEI com mais de um estabelecimento não baixado.
4. **Dois bugs do dbt-core 1.12.5**, contornados e documentados:
   - o *partial parse* duplica métricas;
   - o `fill_nulls_with` é descartado nas métricas do YAML novo.
5. **O dbt v2 (Fusion)** ainda não suporta `options` na materialização `external` (dbt#16526). A migração foi adiada
   com critérios.

### 8.4 O que custou caro

| Problema | Efeito | Lição |
|---|---|---|
| Lote AF e camada semântica inicial feitos inline pelo líder | sem revisor de contexto limpo; no PR #1, o Greptile e a RSEM acharam depois 3 + 12 problemas; ~US$ 20 do líder nas fases com trabalho inline | **o líder não implementa**, nem lote "pequeno" ou "mecânico" (memória `delegar-implementacao-revisao`) |
| Teste não hermético com token real no `.env` | 3 tabelas sintéticas publicadas no MotherDuck real | teste que remove variáveis precisa isolar também a fonte que as recarrega |
| Testes que provam sincronia ou totais, não conteúdo | 7/8 (RSEM), 8/8 (RDIC) e 10/10 (RRN) mutações sobreviventes na 1ª entrega | o brief já pede mutações do autor, mas o revisor e o líder precisam fazer as **suas**; fixar o universo por regra e injetar violação por regra |
| Regras de negócio traduzidas sem olhar o dado real | falsos positivos em massa (RN-05, RN-13, RN-14) | rodar cada regra no dado real **antes** de escrever a interpretação; ler a distribuição do que viola |
| Script de custos da v1 só no scratchpad | perdido; reimplementado | ferramenta de relatório recorrente vai para `scripts/` |
| Script do líder com separador `||` na triagem (2 vezes) | tabela quebrada, commit extra | conferir a contagem de colunas depois de edição programática de tabela |

### 8.5 Lições
1. **A delegação é a garantia de qualidade, não um custo a otimizar.** O autor não acha o próprio ponto cego. Em todo
   PR, a revisão independente ou o líder acharam algo que o autor tinha dado como pronto.
2. **Verificação do líder = gates + dado + mutação própria + fonte.** Pelo menos uma mutação diferente das do autor;
   pelo menos um fato conferido na fonte primária.
3. **Greptile complementa, não substitui:** pega divergências de regra e de configuração no diff. A revisão
   independente pega semântica e dado real.
4. **Documento gerado + teste de atualização + teste de conteúdo.** Só o de atualização prova sincronia, não verdade
   (RDIC-08).
5. **Fatos que mudam com o tempo** (limites do MEI, prazos do Simples) levam data de acesso e a ressalva do que está em
   tramitação (PLP 186/2026). Blogs não são fonte.

### 8.6 Custo (resumo)
Pós-v1: **US$ 156,77 ≈ R$ 787**, todo no Claude (equivalente de API da assinatura), sem OpenRouter. Acumulado do
projeto: **US$ 404,15 ≈ R$ 2.082**, dos quais US$ 10,55 foram desembolso real.

| Papel | US$ | % |
|---|---:|---:|
| Líder (6,45 h ativas; ~US$ 20 nas fases com trabalho inline) | 77,22 | 49 % |
| Correções (FSEM, FRSEM, FDIC, FDIC2, FRN, FRN2) | 36,24 | 23 % |
| Implementação (FNEG, DIC, RN) | 25,02 | 16 % |
| Revisões independentes (RSEM, RDIC, RRN) | 18,29 | 12 % |

Por versão, sem o líder: v1.1.0 US$ 35,39; v1.2.0 US$ 15,38; v1.3.0 US$ 28,78. Detalhe em
[docs/CUSTOS_AGENTES.md](docs/CUSTOS_AGENTES.md#pós-v1-v110-a-v130).

## 9. Pós-v1.3: avaliações e v1.4.0 (13/10 a 14/10/2026)

### 9.1 O que foi entregue

| Item | PR | Entrega |
|---|---|---|
| Avaliação do nível de bairro | [#6](https://github.com/llrt/dbt-pipeline-rfb-v2/pull/6) | ADR-0021 **adiada**. O `bairro` da RFB é texto livre: 14 % dos ativos em "CENTRO" e 88 % dos pares município × bairro com menos de 5 ativos. A chave oficial exigiria o CNEFE (pesado, decenal) e uma emenda ao ADR-0008, a um custo estimado de US$ 150 a 250. O ADR traz os gatilhos para reabrir |
| Avaliação de fontes gratuitas | — | Princípio do usuário: **nenhuma base paga**, para não transferir o custo a quem usa nem contornar a cobrança da fonte. As tabelas da antiga Fase 2 não eram pagas na origem; só o caminho pelo BigQuery era. O pacote 1 saiu dessa avaliação |
| v1.4.0 (minor) | [#7](https://github.com/llrt/dbt-pipeline-rfb-v2/pull/7) | Enriquecimento com fontes gratuitas, direto da origem (ADR-0022, que encerra a Fase 2 do ADR-0015). CEMPRE (SIDRA 9528), renda do Censo 2022 (SIDRA 10295), REGIC 2018 (geoftp) e VA por atividade entram em `dim_municipio`, na ponte de destinos de compra, no mart CEMPRE × RFB e no polo de compras da área de mercado. Também: a RN-30, 5 analyses de cenário com `docs/CENARIOS_DE_USO.md` e as opções `--renovar-ibge` e `--sem-ibge` |

### 9.2 Processo
- **A dinâmica delegada ficou completa desde o início:** IBG1 e IBG2 (implementação), RIBG (revisão, Opus alto),
  FIBG e FIBG2 (correções), todos agentes novos. O líder confirmou as fontes na API antes do brief e verificou cada
  lote com `make ci`, uma mutação própria e a conferência de que o dado real não foi tocado.
- **A verificação do líder pegou o que o autor não via.** O IBG1 relatou o CI verde, mas as fixtures não eram
  determinísticas: o openpyxl grava a hora no `core.xml`, e o teste só passa quando as duas gerações caem no mesmo
  segundo.
- **Minor ou major virou critério explícito.** O usuário perguntou, e o líder definiu a "interface pública": gold,
  CLI, variáveis de ambiente, formato do `--origem-local`, camada semântica e requisitos. O brief do IBG2 ganhou a
  condição de compatibilidade do modo offline.
- **A compatibilidade quebrou duas vezes mesmo assim, por caminhos que ninguém listou:**
  - a RIBG achou o RIBG-01 (bloqueante): um `RAIZ_DADOS` da v1.3, como o do usuário, sem `raw/ibge`, quebrava
    `pipeline --sem-ingestao`, `atualizar` sem mês novo e `regras`;
  - o Greptile achou o `rfb relatorio` num warehouse da v1.3 ainda não reconstruído.

  A condição do brief cobria só o `--origem-local`.
- **O usuário mudou o escopo no meio do lote** (analyses de demonstração e cenários de uso). O adendo foi para o
  agente em curso, com o mesmo padrão de testes e mutações, sem abrir lote novo.

### 9.3 Achados de produto
1. **Fundão não tem loja de tintas porque compra fora.** A REGIC mostra os moradores comprando bens duráveis em Serra
   (45 %) e Vitória (38 %). Serra tem 45 ativos no CNAE 4741500, e o CEMPRE confirma 33 unidades locais e 196 pessoas.
2. **O CEMPRE exclui MEI** (metodologia do IBGE). A RN-30 compara só com os ativos sem MEI: são 2.101 divergências em
   1.073.268 pares município × classe (0,20 %), concentradas em educação e administração pública.
3. **O VA por atividade só vai até 2021,** enquanto o PIB total vai até 2023. O IBGE ainda não publicou as aberturas.
4. **A REGIC não mede evasão total:** o % é a divisão entre destinos de fora do município. Em 314 de 5.503 municípios,
   o polo de compras fica em outra UF.
5. **O sigilo do CEMPRE é grande:** 1.099 municípios só na classe 47.41-5. O pessoal ocupado nunca é imputado.

### 9.4 O que custou caro

| Problema | Efeito | Lição |
|---|---|---|
| Compatibilidade de upgrade testada só pelo caminho citado no brief | 1 bloqueante na revisão e 1 P1 no Greptile, dois lotes de correção | Para minor, o brief lista **todo comando** com o estado da v(n−1) (dados, warehouse, raw) e pede um teste de integração por comando |
| Fixtures não determinísticas (hora no `core.xml`) | uma volta extra ao IBG1 | Teste de determinismo com relógio forçado, não "duas gerações seguidas" |
| CEMPRE nacional: 337 consultas, 45 min, 2,1 GB de JSON | primeiro `atualizar` de 1 a 2 h e dependência do IBGE no mensal | Fonte lenta tem opção de desligar (`--sem-ibge`), falha tolerada e sonda espaçada desde o primeiro desenho |
| Adendo de escopo durante o lote | o IBG2 ficou com o maior custo do período | Aceitável: mais barato que um lote novo, mas a estimativa precisa prever esse tipo de pedido |

### 9.5 Lições
1. **Avaliar antes de construir rende.** Um ADR de avaliação de cerca de US$ 9 evitou um incremento de US$ 150 a 250
   que agregava pouco. O usuário pediu a avaliação crítica, e ela mudou a decisão.
2. **O princípio de custo zero para quem usa** vira critério de arquitetura: fonte primária gratuita, sem conta em
   nuvem nem chave.
3. **O critério de versão é um contrato verificável:** listar a interface pública e testar o upgrade por comando.
4. **Confirmar a fonte antes do brief** (tabelas da SIDRA, símbolos, limites, oráculos) deu ao implementador valores
   de referência para conferir. Todos bateram no dado real.

### 9.6 Custo (resumo)
Período: **US$ 97,27 ≈ R$ 488**, todo no Claude Opus 5.5 (equivalente de API da assinatura). Acumulado do projeto:
**US$ 501,42 ≈ R$ 2.571**, dos quais US$ 10,55 foram desembolso real.

| Papel | US$ | % |
|---|---:|---:|
| Implementação (IBG1, IBG2) | 43,20 | 44 % |
| Líder (3,0 h ativas: avaliações US$ 9,26; orquestração da v1.4.0 US$ 17,98) | 27,24 | 28 % |
| Correções (FIBG, FIBG2) | 18,01 | 19 % |
| Revisão independente (RIBG) | 8,82 | 9 % |

Detalhe em [docs/CUSTOS_AGENTES.md](docs/CUSTOS_AGENTES.md#pós-v13-avaliações-e-v140).
