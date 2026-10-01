# Triagem da R4 (líder, 2026-10-01)

Veredito da R4 ([R4.md](R4.md), [validation.md](../../.specs/features/rfb-dbt-port/validation.md)): **pronto
para entrega, com ressalvas** — 0 bloqueantes, 4 importantes, 6 menores, 5 sugestões; 107 ACs com evidência
citável (100 %), 100 exatos (93 %); 28 mutações, 2 sobreviventes (D04, D08). O líder reproduziu o R4-01 no gold
real (12.498.398 nomes de `bh_empresas` terminando em 11 dígitos; `mart_fornecedores_proximos` sem casos).

| Achado | Decisão | Lote | Resolvido em |
|---|---|---|---|
| **R4-01** CPF completo no fim do nome (LGPD) | **Usuário decidiu mascarar** (ADR-0008 emendado): sufixo de 11 dígitos → `***.***.***-**` em todo nome do gold, adaptação declarada; paridade alinha o mascaramento; teste error barra CPF válido em colunas de nome | F4 | `a9e6a7b` (F4) |
| **R4-02** backfill grava partição sem gate | build do backfill com os testes de `+fct_resumo_mensal`; partição gravada na raiz temporária e movida ao gold só após sucesso (Fix 2) | F4 | `a0239f2` (F4) |
| **R4-03** gold misto após falha do build corrente | marcador `_estado/em_andamento.json` (relatório e publicação recusam); `OPERACAO.md`; publicação em transação quando possível (Fix 3) | F4 | `00d423e` (F4) |
| **R4-04** backfill sem afirmação de regravação (D04) | apagar a partição antes do backfill no `make ci` e afirmar as contagens (Fix 1) | F4 | `4f00eab` (F4) |
| **R4-05** dedup de raiz sem `error_if`, desempate parcial | `error_if` (> 100 raízes) e desempate total; linha "fantasma" nas fixtures (Fix 7, D08) | F4 | `3387a3d` (F4) |
| **R4-06** estado/retenção só locais com s3 | documentar em `OPERACAO.md` e na spec UPD AC 1 (comportamento aceito) | F4 | `c59cbf4` (F4) |
| **R4-07** spec/tasks desatualizados | emendas OPS AC 1, CORE AC 1/6, ING AC 1; tasks T30/T31 marcadas | líder | `0f6ad0d` |
| **R4-08** guia manda `temp_directory` em `settings` | alinhar guia e exemplos a `config_options` (decisão do B8) | F4 | `f7d96b7` (F4) |
| **R4-09** workflow sem `permissions:`, actions por tag, `uv sync` sem `--locked` | `permissions: contents: read`, actions fixadas por SHA, `uv sync --locked` | F4 | `db6a98e` (F4) |
| **R4-10** ajuda do `rfb sincronizar` desatualizada | corrigir o texto | F4 | `bed1af7` (F4) |
| Fix 6 sobrevivência sem caso de borda | unit test com estabelecimento sem `dat_inicio_atividade` | F4 | `0a9bfc3` (F4) |
| PIB warn 0,01 % repetindo 477 linhas/mês | tolerância absoluta de R$ 1.000 + relativa (sugestão da R4) | F4 | `6e2be5b` (F4) |
| Sugestões R4-11a..e | avaliar no F4 se triviais; senão registrar no RETRO | F4 | F4: 11a `6e2be5b`, 11d `3387a3d`, 11b (OSError) e 11e (`.gitignore`) `60acf5d`; pendentes para o RETRO: 11b (warn de C1), 11c, 11e (gitleaks, teto de zip bomb) |
| P12 | fechada (regra cumprida em todas as revisões) | — | — |
| P22 | reaberta em parte → R4-02/R4-04 no F4 | F4 | `4f00eab`, `a0239f2` (F4) |

**F4 (2026-10-01).** Validação do R4-01 no dado real de 2026-09 (cópia do raw, gold do B8 intacto):
`bh_empresas` antes 12.162.451 nomes distintos com CPF válido → depois 0 (12.499.073 linhas mascaradas,
inclusive 908 CPFs no meio do nome; 259 trechos de 12+ dígitos ficam); `mart_fornecedores_proximos` 0 → 0;
`paridade_bh_empresas` PASS; `sem_cpf_no_nome` PASS (1,8 s); custo da máscara ≈ 2 s sobre 71,4 M nomes.
Mutações do F4 (D04, D08, máscara desligada, marcador que fica, backfill direto no gold): 5/5 mortas.
