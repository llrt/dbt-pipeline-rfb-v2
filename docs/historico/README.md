# Histórico do projeto

Registros datados de **como** o projeto foi feito: planos, revisões, execuções, custos e a referência do MVP
original. Eles são **registro, não referência**: cada um descreve o projeto como estava na data em que foi escrito,
e não é atualizado depois. Caminhos, números e nomes citados neles podem ter mudado; para o estado atual, use o
[README](../../README.md), o [ARCHITECTURE](../../ARCHITECTURE.md), os [conceitos](../conceitos.md), a
[operação](../operacao.md) e a [referência](../referencia/dicionario-dados.md). O que mudou de versão em versão está no
[CHANGELOG](../../CHANGELOG.md); as decisões que continuam valendo, nos [ADRs](../adr/README.md).

Só os links quebrados por mudanças de lugar foram corrigidos; a prosa fica como foi escrita.

| Item | O que é | Data |
|---|---|---|
| [plano-v1.md](plano-v1.md) | plano da v1: analogia com um time, equipe de agentes, roteamento de modelos e o andamento dos lotes e revisões | 2026-09-28 a 2026-10-01 |
| [retro.md](retro.md) | retrospectiva do líder: v1 e pós-v1 até a v1.4.0 | até 2026-10-14 |
| [custos-agentes.md](custos-agentes.md) | custo por agente (equivalente de API e OpenRouter), gerado dos transcripts | 2026-10-01, atualizado até a v1.4.0 |
| [execucao-real-2026-10.md](execucao-real-2026-10.md) | execução real de 2026-09: tempos por etapa, volumes, avisos do build, memória, correções exigidas pelos dados reais e paridade com o notebook 4. O resumo vivo está em [operação](../operacao.md#requisitos-e-tempos-medidos-p14) | 2026-10-01 |
| [reorganizacao-v1.5.0.md](reorganizacao-v1.5.0.md) | onde foi parar cada seção dos documentos fundidos ou enxugados na v1.5.0 | 2026-10-15 |
| [revisoes/](revisoes/) | uma revisão independente por arquivo, com a **triagem do líder** anexada ao fim (`## Triagem do líder`): o que foi aceito, adiado ou recusado, e em qual commit | ver abaixo |
| [revisoes/pendencias.md](revisoes/pendencias.md) | achados do líder durante a verificação dos lotes, para o revisor da fase | 2026-09-28 em diante |
| [referencia-original/](referencia-original/README.md) | extração em texto dos notebooks do MVP original (Databricks/Spark): a fonte de verdade do escopo `original` | commit `2ea8bd2` do original |

## Revisões

| Revisão | Escopo | Versão |
|---|---|---|
| [R1](revisoes/R1.md) | fases 1–4 (T1–T13) | v1.0.0 |
| [R2](revisoes/R2.md) | lotes B5 (T14/T15) e RN (T37) | v1.0.0 |
| [R3](revisoes/R3.md) | lotes B6, B7 e B7b | v1.0.0 |
| [RBP](revisoes/RBP.md) | boas práticas (guia dbt × projeto) | v1.0.0 |
| [R4](revisoes/R4.md) | revisão final, segurança e Verifier da spec | v1.0.0 |
| [RSEM](revisoes/RSEM.md) | camada semântica, contexto de negócio e ontologia | v1.1.0 |
| [RDIC](revisoes/RDIC.md) | dicionário de dados | v1.2.0 |
| [RRN](revisoes/RRN.md) | regras e invariantes de negócio | v1.3.0 |
| [RIBG](revisoes/RIBG.md) | enriquecimento IBGE | v1.4.0 |
| [RGQ](revisoes/RGQ.md) | golden queries e guia para agente | v1.4.1 |

Até a v1.4 cada triagem era um arquivo à parte (`<revisão>-triagem.md`); na v1.5.0 foi anexada ao fim da revisão,
sem mudar o texto.
