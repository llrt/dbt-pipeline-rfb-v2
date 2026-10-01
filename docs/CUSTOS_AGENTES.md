# Custo por agente — v1

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
- Reproduzir: `python3 custos.py custos.json` (script do líder no scratchpad da sessão; lógica descrita acima).
