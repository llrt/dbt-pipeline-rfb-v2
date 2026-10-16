# Custo por agente — v1 e pós-v1 (v1.1.0 a v1.5.1)

> Gerado pelo líder em 2026-10-01 a partir dos transcripts do Claude Code (`~/.claude/projects/*dbt-pipeline-rfb-v2*`, deduplicados por mensagem) e do banco do opencode (`~/.local/share/opencode/opencode.db`, sessões do OpenRouter). A tentativa anterior do projeto (24/09, outra sessão: `fase-0-design`, `guia-g1-guia-dbt`, `fase-1-b1a-fundacao`) está fora.

**Como ler**
- **Claude (assinatura):** os agentes Claude rodaram no login da assinatura do usuário; o custo mostrado é o **equivalente de API**, não cobrança. Preços públicos (US$/M tokens): Opus 5.5 entrada 4, saída 20, leitura de cache 0,20; Sonnet 5 entrada 2, saída 10, leitura 0,20; escrita de cache = 2× a entrada (TTL de 1 h do Claude Code). Sonnet 5.5 sem preço publicado: estimado como Sonnet 5.
- **OpenRouter (medido):** DeepSeek v4 Flash e Gemini 3.8 Flash, cobrança real por uso; o opencode não registrou o valor, então o custo foi calculado com os preços do OpenRouter em 2026-10-01 (Gemini: 0,75/3,75/0,075; DeepSeek: 0,0108/1,28/0,0108 US$/M).
- **R$:** câmbio US$ 1 = R$ 5,2353 (AwesomeAPI, 01/10/2026).
- **Horas ativas:** tempo entre a primeira e a última mensagem descontando pausas de mais de 30 min; lotes com execução em dado real ou com o Mac em sleep (B7, B7b) aparecem mais longos.

## Resumo

| | US$ | R$ | % |
|---|---:|---:|---:|
| Líder | 88,11 | 461,28 | 36 % |
| Implementação | 77,74 | 406,99 | 31 % |
| Revisão | 39,07 | 204,54 | 16 % |
| Correção | 42,46 | 222,29 | 17 % |
| **Total** | **247,38** | **1.295,11** | 100 % |

| Cobrança | US$ | R$ |
|---|---:|---:|
| Assinatura Claude (equivalente de API, sem desembolso adicional) | 236,83 | 1.239,88 |
| OpenRouter (medido, desembolso real) | 10,55 | 55,23 |

| Modelo | US$ | R$ |
|---|---:|---:|
| Claude Opus 5.5 | 169,76 | 888,74 |
| Claude Sonnet 5.5 | 44,38 | 232,34 |
| Claude Sonnet 5 | 22,69 | 118,79 |
| Gemini 3.8 Flash | 10,23 | 53,56 |
| DeepSeek v4 Flash | 0,32 | 1,68 |

## Por agente (ordem de início)

| Agente | Papel | Modelo | Cobrança | Saída (tokens) | Leitura de cache | Entrada + escrita de cache | Horas ativas | US$ | R$ |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| B1 Fundação | implementação | DeepSeek v4 Flash | medida | 24.036 | 4.974.080 | 82.685 | 0,13 | 0,09 | 0,47 |
| B9a Guia dbt (fundamentos) | implementação | DeepSeek v4 Flash | medida | 53.963 | 9.864.704 | 407.730 | 0,58 | 0,18 | 0,94 |
| B2 Fixtures (1ª tentativa, falhou) | implementação | DeepSeek v4 Flash | medida | 33.848 | 816.896 | 76.847 | 0,16 | 0,05 | 0,26 |
| Líder (planejamento, verificação, integração) | líder | Claude Opus 5.5 | assinatura | 596.642 | 234.778.079 | 3.653.363 | 14,76 | 88,11 | 461,28 |
| B2 Fixtures e clientes | implementação | Claude Sonnet 5 | assinatura | 89.627 | 16.340.484 | 238.993 | 0,54 | 5,12 | 26,80 |
| B3 Conversão Parquet | implementação | Claude Opus 5.5 | assinatura | 39.613 | 3.320.638 | 95.854 | 0,33 | 2,22 | 11,62 |
| B4 Ingestão e fontes dbt | implementação | Claude Sonnet 5 | assinatura | 176.712 | 71.627.216 | 368.939 | 1,3 | 17,57 | 91,98 |
| B4 Ingestão e fontes dbt | implementação | Claude Sonnet 5.5 | assinatura | 169 | 0 | 453.255 | 1,3 | 1,81 | 9,48 |
| R1 Revisão fases 1–4 | revisão | Claude Opus 5.5 | assinatura | 61.167 | 8.453.605 | 456.539 | 0,52 | 6,57 | 34,40 |
| F1a Correções R1 | correção | Claude Sonnet 5.5 | assinatura | 73.187 | 8.449.575 | 424.083 | 0,5 | 4,12 | 21,57 |
| F1b Correções R1 (conversão) | correção | Claude Opus 5.5 | assinatura | 20.566 | 2.795.783 | 114.737 | 0,1 | 1,89 | 9,89 |
| B5 Staging + bh_empresas | implementação | Claude Opus 5.5 | assinatura | 50.615 | 6.649.338 | 184.239 | 0,92 | 3,82 | 20,00 |
| RN Padronização de nomes | implementação | Claude Sonnet 5.5 | assinatura | 43.968 | 7.094.913 | 111.174 | 0,55 | 2,30 | 12,04 |
| R2 Revisão B5 + RN | revisão | Claude Opus 5.5 | assinatura | 72.385 | 12.537.928 | 152.601 | 0,5 | 5,18 | 27,12 |
| F2a Correções R2 (dbt) | correção | Claude Opus 5.5 | assinatura | 51.912 | 11.831.754 | 349.379 | 0,85 | 6,20 | 32,46 |
| F2b Correções R2 (nomes) | correção | Claude Sonnet 5.5 | assinatura | 16.815 | 2.722.142 | 105.936 | 0,07 | 1,14 | 5,97 |
| B6 agg + modelo estrela | implementação | Claude Sonnet 5.5 | assinatura | 75.517 | 11.908.565 | 171.526 | 0,35 | 3,82 | 20,00 |
| B7 Análises, DQ, estudo de caso | implementação | Claude Sonnet 5.5 | assinatura | 101.540 | 21.638.442 | 510.012 | 3,18 | 7,38 | 38,64 |
| B7b Série mensal + Power BI | implementação | Claude Sonnet 5.5 | assinatura | 32.938 | 6.149.158 | 142.972 | 2,99 | 2,13 | 11,15 |
| B9b Guia dbt robusto | implementação | Gemini 3.8 Flash | medida | 125.266 | 32.469.114 | 4.402.019 | 0,78 | 6,21 | 32,51 |
| FBPg Correções RBP (guia) | correção | Gemini 3.8 Flash | medida | 151.566 | 29.918.404 | 1.607.228 | 0,82 | 4,02 | 21,05 |
| R3 Revisão B6/B7/B7b | revisão | Claude Opus 5.5 | assinatura | 86.970 | 19.219.002 | 337.739 | 0,43 | 8,28 | 43,35 |
| F3a Correções R3 (estrela/BI) | correção | Claude Sonnet 5.5 | assinatura | 65.285 | 14.612.561 | 175.517 | 0,33 | 4,28 | 22,41 |
| F3b Correções R3 (DQ/relatório) | correção | Claude Sonnet 5.5 | assinatura | 59.728 | 13.772.875 | 178.861 | 0,3 | 4,07 | 21,31 |
| RBP Boas práticas + guia | revisão | Claude Opus 5.5 | assinatura | 100.700 | 24.545.127 | 370.105 | 0,42 | 9,88 | 51,72 |
| B10 Enriquecimento Base dos Dados | implementação | Claude Sonnet 5.5 | assinatura | 93.748 | 17.126.865 | 225.694 | 0,53 | 5,27 | 27,59 |
| FBPa Correções RBP (projeto) | correção | Claude Sonnet 5.5 | assinatura | 69.481 | 15.268.976 | 197.993 | 0,71 | 4,54 | 23,77 |
| B11 MotherDuck + acesso Power BI | implementação | Claude Sonnet 5.5 | assinatura | 30.138 | 4.452.101 | 97.460 | 0,14 | 1,58 | 8,27 |
| B8 Pipeline real + rfb atualizar | implementação | Claude Opus 5.5 | assinatura | 164.584 | 49.293.778 | 387.020 | 1,52 | 16,25 | 85,07 |
| R4 Final + segurança + Verifier | revisão | Claude Opus 5.5 | assinatura | 98.914 | 23.011.795 | 322.643 | 0,36 | 9,16 | 47,96 |
| F4 Correções R4 | correção | Claude Opus 5.5 | assinatura | 117.971 | 36.964.371 | 306.565 | 0,96 | 12,20 | 63,87 |
| B12 Vazios de mercado (P23) | implementação | Claude Sonnet 5.5 | assinatura | 31.447 | 5.218.145 | 145.636 | 0,32 | 1,94 | 10,16 |

## Observações

- A **leitura de cache** domina o volume (contexto relido a cada chamada), mas custa 5–10 % da entrada; a **saída** domina o custo dos workers.
- O **líder** é a maior fatia porque reexecuta gates, consulta o gold e roda mutações em todo merge, além de planejar, triar e documentar.
- **Revisões** (Opus alto) custaram em média ~US$ 8 cada e foram as que mais acharam problemas reais (paridade em dado real, capital inflado, CPF).
- **Gemini 3.8 Flash** (guia) foi ~2× mais barato que um lote Sonnet equivalente, mas exigiu uma rodada de correção de referências e outra de 43 erros técnicos (FBPg).
- **DeepSeek v4 Flash** custou centavos; falhou no B2 (estouro de saída) e foi substituído por Sonnet.
- Reproduzir: o script da v1 ficou só no scratchpad da sessão e se perdeu. A lógica está descrita acima e foi reimplementada em `scripts/custos_agentes_pos_v1.py`.

## Pós-v1 (v1.1.0 a v1.3.0)

> Gerado pelo líder em 2026-10-13 com `scripts/custos_agentes_pos_v1.py`, versionado desta vez. A metodologia e os preços são os da v1. Cobre o período depois do commit da RETRO v1 (`eef3b22`, 01/10/2026 15:16): a publicação no GitHub, o CI, as releases v1.0.0 a v1.3.0, a avaliação do dbt Fusion e os 12 agentes dos PRs #1, #3 e #4. Todos os agentes rodaram no Claude (assinatura). Não houve uso do OpenRouter. Câmbio US$ 1 = R$ 5,021 (AwesomeAPI, 13/10/2026). O transcript do líder é o desta sessão, ainda em uso; os números do líder vão até a geração.

| | US$ | R$ | % |
|---|---:|---:|---:|
| Líder | 77,22 | 387,72 | 49 % |
| Implementação | 25,02 | 125,63 | 16 % |
| Revisão | 18,29 | 91,83 | 12 % |
| Correção | 36,24 | 181,96 | 23 % |
| **Total pós-v1** | **156,77** | **787,14** | 100 % |

| Modelo | US$ | R$ |
|---|---:|---:|
| Claude Opus 5.5 | 146,79 | 737,03 |
| Claude Sonnet 5.5 | 9,98 | 50,11 |

**Líder por fase**

| Fase | Horas ativas | US$ | R$ |
|---|---:|---:|---:|
| Publicação no GitHub, CI e v1.0.0 | 0,83 | 10,96 | 55,02 |
| Avaliação do Fusion, lote AF inline e v1.0.1 | 0,57 | 10,93 | 54,86 |
| Camada semântica inicial inline | 0,28 | 8,86 | 44,49 |
| Orquestração delegada v1.1.0 a v1.3.0 | 4,77 | 46,47 | 233,33 |
| **Total do líder** | **6,45** | **77,22** | **387,72** |

**Agentes por versão** (sem o líder)

| Versão | Entrega | US$ | R$ |
|---|---|---:|---:|
| v1.1.0 | camada semântica: correções, contexto de negócio, ontologia | 35,39 | 177,69 |
| v1.2.0 | dicionário de dados | 15,38 | 77,22 |
| v1.3.0 | regras de negócio, checks e relatório | 28,78 | 144,50 |

**Por agente (ordem de início)**

| Agente | Papel | Versão | Modelo | Saída (tokens) | Leitura de cache | Entrada + escrita de cache | Horas ativas | US$ | R$ |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| FSEM, correções do Greptile (PR #1) | correção | v1.1.0 | Claude Opus 5.5 | 67.335 | 17.148.322 | 196.686 | 0,46 | 6,35 | 31,88 |
| FNEG, contexto de negócio e ontologia | implementação | v1.1.0 | Claude Opus 5.5 | 122.413 | 28.738.046 | 315.822 | 0,51 | 10,72 | 53,83 |
| RSEM, revisão independente | revisão | v1.1.0 | Claude Opus 5.5 | 70.686 | 19.562.634 | 271.401 | 0,36 | 7,50 | 37,64 |
| FRSEM, correções da RSEM | correção | v1.1.0 | Claude Opus 5.5 | 120.778 | 28.895.433 | 328.353 | 0,73 | 10,82 | 54,33 |
| DIC, dicionário de dados | implementação | v1.2.0 | Claude Sonnet 5.5 | 80.738 | 12.887.102 | 262.815 | 0,39 | 4,44 | 22,27 |
| RDIC, revisão independente | revisão | v1.2.0 | Claude Opus 5.5 | 58.062 | 12.205.388 | 225.351 | 0,23 | 5,40 | 27,14 |
| FDIC, correções da RDIC | correção | v1.2.0 | Claude Sonnet 5.5 | 85.463 | 15.841.930 | 226.882 | 0,38 | 4,93 | 24,75 |
| FDIC2, comentários do Greptile (PR #3) | correção | v1.2.0 | Claude Sonnet 5.5 | 9.744 | 1.697.767 | 44.445 | 0,14 | 0,61 | 3,09 |
| RN, regras de negócio | implementação | v1.3.0 | Claude Opus 5.5 | 130.669 | 23.156.356 | 326.930 | 0,60 | 9,86 | 49,50 |
| RRN, revisão independente | revisão | v1.3.0 | Claude Opus 5.5 | 71.086 | 11.184.979 | 216.617 | 0,31 | 5,39 | 27,07 |
| FRN, correções da RRN | correção | v1.3.0 | Claude Opus 5.5 | 119.930 | 27.951.907 | 305.413 | 0,70 | 10,43 | 52,38 |
| FRN2, comentários do Greptile (PR #4) | correção | v1.3.0 | Claude Opus 5.5 | 31.317 | 7.600.615 | 119.588 | 0,33 | 3,10 | 15,58 |

## Pós-v1.3: avaliações e v1.4.0

> Gerado pelo líder em 2026-10-14 com o mesmo `scripts/custos_agentes_pos_v1.py`, agora estendido. A metodologia, os preços e o câmbio (US$ 1 = R$ 5,021) são os da seção anterior. O período começa no fim da geração anterior (13/10/2026, 16:24) e vai até esta geração. Ele cobre:
> - o fechamento do PR #5 e a limpeza dos worktrees;
> - as avaliações do nível de bairro (ADR-0021, adiada) e das fontes gratuitas;
> - os 5 agentes do PR #7 (enriquecimento IBGE, v1.4.0).
>
> Todos rodaram no Claude (assinatura), em Opus 5.5. O líder passou a ser lido em duas sessões (`96cb3a2c` e `07fdca18`, a continuação); a deduplicação por mensagem evita contar o histórico repetido.

| | US$ | R$ | % |
|---|---:|---:|---:|
| Líder | 27,24 | 136,77 | 28 % |
| Implementação (IBG1, IBG2) | 43,20 | 216,91 | 44 % |
| Revisão (RIBG) | 8,82 | 44,29 | 9 % |
| Correção (FIBG, FIBG2) | 18,01 | 90,43 | 19 % |
| **Total do período** | **97,27** | **488,39** | 100 % |

**Líder por fase**

| Fase | Horas ativas | US$ | R$ |
|---|---:|---:|---:|
| PR #5 depois da geração anterior, housekeeping e avaliações (bairro, fontes gratuitas) | 1,39 | 9,26 | 46,49 |
| Orquestração delegada da v1.4.0 (fontes, briefs, verificação, triagem, PR, Greptile, este relatório) | 1,61 | 17,98 | 90,28 |
| **Total do líder** | **3,00** | **27,24** | **136,77** |

**Por agente (v1.4.0, ordem de início)**

| Agente | Papel | Modelo | Saída (tokens) | Leitura de cache | Entrada + escrita de cache | Horas ativas | US$ | R$ |
|---|---|---|---:|---:|---:|---:|---:|---:|
| IBG1, ingestão e staging do IBGE | implementação | Claude Opus 5.5 | 175.859 | 51.688.494 | 432.112 | 1,30 | 17,31 | 86,92 |
| IBG2, gold, RN-30, semântica, cenários e docs | implementação | Claude Opus 5.5 | 220.112 | 84.909.377 | 563.756 | 0,90 | 25,89 | 130,01 |
| RIBG, revisão independente | revisão | Claude Opus 5.5 | 97.113 | 23.029.193 | 283.779 | 0,42 | 8,82 | 44,27 |
| FIBG, correções da RIBG e versão 1.4.0 | correção | Claude Opus 5.5 | 120.099 | 38.912.899 | 326.028 | 0,76 | 12,79 | 64,23 |
| FIBG2, comentários do Greptile (PR #7) | correção | Claude Opus 5.5 | 56.081 | 13.146.566 | 183.090 | 0,34 | 5,22 | 26,18 |
| **Agentes da v1.4.0** | | | | | | **3,72** | **70,03** | **351,61** |

**Observações**
- **Implementação foi o maior custo desta vez** (44 %), ao contrário do pós-v1 anterior.
  - O IBG2 (US$ 25,89) concentrou gold, regra, semântica, ontologia, ADR e o adendo do usuário (5 analyses de cenário e `CENARIOS_DE_USO.md`).
  - As 1,3 h do IBG1 incluem o download real do CEMPRE (45 min, 337 consultas à SIDRA).
- **A fatia do líder caiu de 49 % para 28 %:** sem trabalho inline, ficaram só fontes, briefs, verificação, triagem e PR.
- **A avaliação do bairro custou parte dos US$ 9,26 da primeira fase** e evitou um incremento estimado em US$ 150 a 250 (ADR-0021).
- A estimativa da avaliação de fontes era de US$ 40 a 70 para o pacote 1. O custo real dos agentes foi de US$ 70,03, no teto. A estimativa não previa o adendo dos cenários nem as duas rodadas de correção de compatibilidade.
- **Reproduzir:** `uv run python scripts/custos_agentes_pos_v1.py`. Rodar de novo dá US$ 47,26 para a fase "orquestração delegada v1.1.0 a v1.3.0", e não os 46,47 da tabela anterior: a fase agora vai até o fim da geração anterior. Os US$ 0,79 de diferença estão somados aqui na primeira fase do líder.

## v1.4.1 e v1.5.0 (golden queries e reorganização das docs)

> Gerado pelo líder em 2026-10-15 com `scripts/custos_agentes_pos_v1.py`, estendido com os 9 agentes dos PRs #8 e #9 e com as fases novas do líder. A metodologia, os preços e o câmbio (US$ 1 = R$ 5,021) são os das seções anteriores. O período começa no fim da geração anterior (15/10/2026, 02:17 UTC) e vai até esta geração. A última fase do líder, este relatório, ainda está em curso.

| | US$ | R$ | % |
|---|---:|---:|---:|
| Líder | 23,40 | 117,49 | 24 % |
| Implementação (GQ, D1, D2) | 32,84 | 164,89 | 33 % |
| Revisão (RGQ, RD) | 11,08 | 55,63 | 11 % |
| Correção (FGQ, FGQ2, FD, FD2) | 32,24 | 161,88 | 32 % |
| **Total do período** | **99,56** | **499,89** | 100 % |

Por modelo: Claude Opus 5.5, US$ 94,93; Claude Sonnet 5.5 (D1, FD2), US$ 4,63.

**Por versão, com o líder**

| Versão | Entrega | Agentes US$ | Líder US$ | Total US$ |
|---|---|---:|---:|---:|
| v1.4.1 | golden queries, guia e catálogo para o agente de consulta | 38,76 | 5,46 | 44,22 |
| v1.5.0 | reorganização da documentação por público | 37,40 | 8,43 | 45,83 |
| — | fechamento da v1.4.0, avaliação das docs e este relatório | — | 9,51 | 9,51 |

**Líder por fase**

| Fase | Horas ativas | US$ | R$ |
|---|---:|---:|---:|
| Fechamento da v1.4.0: resto da fase anterior depois da geração, PR #7 sem o último commit, PR #8 de reenvio, release | 0,04 | 2,32 | 11,65 |
| Orquestração da v1.4.1, parte 1: golden queries (brief, verificação, RGQ despachada) | 0,43 | 1,85 | 9,26 |
| Avaliação crítica das docs (proposta) | 0,05 | 1,40 | 7,03 |
| Orquestração da v1.4.1, parte 2: triagem da RGQ, FGQ, FGQ2, Greptile, release | 0,75 | 3,61 | 18,11 |
| Orquestração da v1.5.0: D1, D2, RD, FD, FD2, Greptile, release | 2,33 | 8,43 | 42,32 |
| RETRO e custos da v1.4.1 e v1.5.0 (em curso) | 0,01 | 5,79 | 29,07 |
| **Total do líder** | **3,61** | **23,40** | **117,49** |

**Por agente (ordem de início)**

| Agente | Papel | Versão | Modelo | Saída (tokens) | Leitura de cache | Entrada + escrita de cache | Horas ativas | US$ | R$ |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| GQ, golden queries e guia do agente | implementação | v1.4.1 | Claude Opus 5.5 | 182.465 | 38.712.909 | 470.942 | 0,86 | 15,16 | 76,11 |
| RGQ, revisão independente | revisão | v1.4.1 | Claude Opus 5.5 | 62.218 | 12.199.873 | 229.848 | 0,23 | 5,52 | 27,73 |
| FGQ, correções da RGQ | correção | v1.4.1 | Claude Opus 5.5 | 157.659 | 38.313.021 | 359.288 | 1,15 | 13,69 | 68,73 |
| FGQ2, comentários do Greptile (PR #8) | correção | v1.4.1 | Claude Opus 5.5 | 48.585 | 10.963.699 | 153.465 | 0,38 | 4,39 | 22,05 |
| D1, links, caminhos e mudança de lugar | implementação | v1.5.0 | Claude Sonnet 5.5 | 56.972 | 11.646.803 | 203.917 | 0,45 | 3,71 | 18,65 |
| D2, consolidação e doc blocks | implementação | v1.5.0 | Claude Opus 5.5 | 121.024 | 42.455.462 | 382.849 | 0,76 | 13,97 | 70,16 |
| RD, revisão independente | revisão | v1.5.0 | Claude Opus 5.5 | 62.191 | 13.061.560 | 213.547 | 0,27 | 5,56 | 27,94 |
| FD, correções da RD e versão 1.5.0 | correção | v1.5.0 | Claude Opus 5.5 | 148.264 | 37.519.282 | 346.514 | 0,98 | 13,24 | 66,48 |
| FD2, CI no Ubuntu e Greptile (PR #9) | correção | v1.5.0 | Claude Sonnet 5.5 | 13.690 | 1.964.944 | 97.889 | 0,54 | 0,92 | 4,63 |
| **Agentes da v1.4.1 e v1.5.0** | | | | | | | **5,62** | **76,16** | **382,48** |

**Observações**
- **A correção custou quase o mesmo que a implementação** (US$ 32,24 × 32,84). Nas duas versões, a revisão independente achou um problema central que o autor tinha dado como pronto:
  - na v1.4.1, a semântica não rodava no ambiente do agente;
  - na v1.5.0, o texto continuava dizendo cada conceito três vezes.

  Também houve o Greptile depois do CI verde: média de médias numa golden query e um teste que só passava no macOS.
- **A fatia do líder caiu para 24 %** (49 % no pós-v1 e 28 % na v1.4.0). As fases de orquestração ficaram baratas:
  - o contexto do líder tinha sido resumido pouco antes, no início da sessão `07fdca18`;
  - briefs e triagens foram escritos em arquivo.
- **Sonnet no lote mecânico (D1) deu certo:** US$ 3,71 para 50 renomeações, verificador e caminhos. O D2, de julgamento de conteúdo, ficou com Opus.
- **Reproduzir:** `uv run python scripts/custos_agentes_pos_v1.py`. Rodar de novo dá US$ 19,06 para a fase "orquestração delegada v1.4.0", e não os 17,98 da seção anterior: a fase agora vai até o fim da geração anterior. Os US$ 1,08 de diferença estão somados aqui, na primeira fase do líder.

## v1.5.1 (guia de construção do agente de consulta)

> Gerado pelo líder em 2026-10-16 com `scripts/custos_agentes_pos_v1.py`, estendido com os 4 agentes do PR #11 e com as fases novas do líder. A metodologia, os preços e o câmbio (US$ 1 = R$ 5,021) são os das seções anteriores. O período começa no fim da geração anterior (15/10/2026, 11:44 UTC) e vai até esta geração. A última fase do líder, este relatório, ainda está em curso.

| | US$ | R$ | % |
|---|---:|---:|---:|
| Líder | 37,18 | 186,68 | 72 % |
| Implementação (GA) | 2,45 | 12,29 | 5 % |
| Revisão (RGA) | 4,03 | 20,24 | 8 % |
| Correção (FGA, FGA2) | 8,03 | 40,34 | 15 % |
| **Total do período** | **51,69** | **259,55** | 100 % |

Por modelo: Claude Opus 5.5, US$ 49,24; Claude Sonnet 5.5 (GA), US$ 2,45.

**Por versão, com o líder**

| Versão | Entrega | Agentes US$ | Líder US$ | Total US$ |
|---|---|---:|---:|---:|
| v1.5.1 | guia de construção do agente, conexão endurecida e funções de referência testadas no CI | 14,51 | 33,43 | 47,94 |
| — | resto do relatório anterior, a pergunta sobre o agente e o dbt, a limpeza dos worktrees e este relatório | — | 3,75 | 3,75 |

**Líder por fase**

| Fase | Horas ativas | US$ | R$ |
|---|---:|---:|---:|
| RETRO e custos da v1.4.1 e v1.5.0: resto da fase depois da geração | 0,03 | 1,07 | 5,37 |
| Pergunta sobre o agente e o dbt (resposta) | 0,01 | 0,51 | 2,56 |
| Orquestração da v1.5.1: GA, RGA, FGA, FGA2, Greptile, release | 3,62 | 33,43 | 167,85 |
| Limpeza dos worktrees (v2 e consulta sobre os da v1) | 0,04 | 1,74 | 8,74 |
| RETRO e custos da v1.5.1 (em curso) | 0,01 | 0,43 | 2,16 |
| **Total do líder** | **3,71** | **37,18** | **186,68** |

**Por agente (ordem de início)**

| Agente | Papel | Versão | Modelo | Saída (tokens) | Leitura de cache | Entrada + escrita de cache | Horas ativas | US$ | R$ |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| GA, guia de construção do agente | implementação | v1.5.1 | Claude Sonnet 5.5 | 23.938 | 4.749.030 | 356.768 | 1,67 | 2,45 | 12,29 |
| RGA, revisão independente | revisão | v1.5.1 | Claude Opus 5.5 | 51.003 | 8.462.800 | 164.942 | 0,72 | 4,03 | 20,24 |
| FGA, correções da RGA | correção | v1.5.1 | Claude Opus 5.5 | 71.447 | 13.590.635 | 158.399 | 2,43 | 5,41 | 27,18 |
| FGA2, comentários do Greptile (PR #11) | correção | v1.5.1 | Claude Opus 5.5 | 28.807 | 6.919.445 | 82.790 | 2,06 | 2,62 | 13,16 |
| **Agentes da v1.5.1** | | | | | | | **6,88** | **14,51** | **72,87** |

**Observações**
- **O líder ficou com 72 % do período**, a maior fatia desde a v1. Os agentes custaram US$ 14,51, os mais baratos por versão do pós-v1. A causa foi o contexto do líder, não o trabalho:
  - ao longo da orquestração a sessão chegou a ~700 mil tokens de contexto (mediana por chamada; máximo de 779 mil);
  - quatro vezes, depois de uma pausa de 40 minutos a 2 horas, o contexto inteiro foi reescrito no cache, a US$ 5,41 a 6,13 cada. Foram duas retomadas depois de erro de servidor da API, o relatório da FGA e o aviso de que a FGA2 tinha encerrado o turno sem relatório;
  - essas 4 chamadas somam US$ 23,18, ou 69 % da fase. A escrita de cache foi US$ 24,24 dos 33,43; a saída do líder, US$ 0,99.
  - Depois do `/compact` (15/10, 22:15 UTC), cada chamada caiu para ~90 mil tokens de contexto.
- **Horas ativas dos agentes estão infladas** pela espera do `make ci` (mais de 10 minutos) e pelas quedas por erro de servidor. Os agentes não fizeram mais trabalho do que nos lotes anteriores.
- **Sonnet no lote de redação (GA) custou US$ 2,45.** A revisão RGA (Opus) achou nele um problema alto de segurança (`read_only` lia qualquer arquivo e a rede). O roteamento "redação → Sonnet, revisão → Opus alto" se sustentou de novo.
- **Reproduzir:** `uv run python scripts/custos_agentes_pos_v1.py`. Rodar de novo dá US$ 6,86 para a fase "RETRO e custos da v1.4.1 e v1.5.0", e não os 5,79 da seção anterior: a fase agora vai até o fim da geração anterior. Os US$ 1,07 de diferença estão somados aqui, na primeira fase do líder.

## Total acumulado

| Período | US$ | R$ |
|---|---:|---:|
| v1 (até 01/10/2026; câmbio 5,2353) | 247,38 | 1.295,11 |
| Pós-v1 (v1.1.0 a v1.3.0; câmbio 5,021) | 156,77 | 787,14 |
| Pós-v1.3 (avaliações e v1.4.0; câmbio 5,021) | 97,27 | 488,39 |
| v1.4.1 e v1.5.0 (câmbio 5,021) | 99,56 | 499,89 |
| v1.5.1 (câmbio 5,021) | 51,69 | 259,55 |
| **Total** | **652,67** | **3.330,08** |

Do total, **US$ 10,55 foram desembolso real** (OpenRouter, todo na v1). O resto é equivalente de API da assinatura Claude.

### Observações do pós-v1

- **Correção custou mais que implementação** (US$ 36,24 × 25,02). Cada PR teve uma revisão independente e os comentários do Greptile, e cada rodada voltou com achados reais: falsos positivos nas regras, guarda de privacidade furada, mutações sobreviventes. Revisão + correção = 35 % do pós-v1, contra 33 % na v1.
- **O líder ficou em 49 % do pós-v1.** 8,86 desses dólares foram a camada semântica feita inline, em 17 minutos de relógio, antes da cobrança do usuário; e 10,93 incluem o lote AF, também inline. Na orquestração delegada, o custo do líder se dividiu entre briefs, verificação por evidência (`make ci`, mutação própria, dado real), triagens, PRs e releases.
- **Sonnet 5.5 no dicionário** (DIC, FDIC, FDIC2) custou cerca de metade de um lote Opus equivalente. A revisão RDIC (Opus) ainda achou 11 pontos, o que sustenta o roteamento "não crítico → Sonnet, revisão → Opus alto".
- Reproduzir: `uv run python scripts/custos_agentes_pos_v1.py` (lê os transcripts locais do Claude Code; os IDs das sessões estão no script).
