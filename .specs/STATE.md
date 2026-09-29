# STATE

## Decisions

Decisões de arquitetura completas em `docs/adr/`. Aqui ficam as decisões de projeto/processo que restringem features futuras.

| ID | Decision | Status | Date |
|---|---|---|---|
| AD-001 | Stack: dbt-core + dbt-duckdb, DuckDB ≥1.5, Parquet em todas as camadas, Python 3.12 via uv (ADR-0001) | active | 2026-09-28 |
| AD-002 | EL em Python fora do dbt; raw all-VARCHAR particionado por `mes_referencia` (ADR-0002) | active | 2026-09-28 |
| AD-003 | Fonte RFB = WebDAV público, mês padrão = mais recente; referência 2026-09 (ADR-0003) | active | 2026-09-28 |
| AD-004 | Métricas temporais relativas a `data_referencia`, nunca `now()` (ADR-0004) | active | 2026-09-28 |
| AD-005 | `bh_empresas`/`agg_empresas` em paridade com o original; melhorias só no star schema (ADR-0005) | active | 2026-09-28 |
| AD-006 | Todo nó dbt com `meta.escopo` ∈ {original, adicao, adaptado} + tag (ADR-0006) | active | 2026-09-28 |
| AD-007 | `DATA_ROOT` local ou `s3://`; sync via boto3; testes com moto (ADR-0007) | active | 2026-09-28 |
| AD-008 | Sem `Socios`; contatos descartados no staging (ADR-0008) | active | 2026-09-28 |
| AD-009 | Testes em camadas; estrutura = error, conteúdo = warn + error_if (ADR-0009) | active | 2026-09-28 |
| AD-010 | Fixtures sintéticas determinísticas com respostas conhecidas definidas na spec (ADR-0010) | active | 2026-09-28 |
| AD-011 | Execução por lotes com roteamento de modelos do guia Traycer; worktree por lote; líder verifica gates (ADR-0011) | active | 2026-09-28 |
| AD-012 | Usuário delegou autonomia total ao líder; escalar só decisões críticas/irreversíveis. Confirmações do tlc-spec-driven (spec/tasks/oferta de sub-agentes) são feitas pelo líder | active | 2026-09-28 |
| AD-013 | Sem `design.md` separado: `ARCHITECTURE.md` + ADRs são o design do feature `rfb-dbt-port` | active | 2026-09-28 |
| AD-014 | Por decisão do usuário (2026-09-28), tarefas médias não críticas passam a usar Claude Sonnet (esforço médio) em vez de DeepSeek v4 flash; vale para B4, B6, B7, B9b e correções dessas tarefas. Pequenas seguem DeepSeek v4 flash (baixo); críticas/E2E seguem Opus (médio) | active | 2026-09-28 |
| AD-015 | Atualização mensal: `rfb atualizar` com completude do mês, estado de última execução, retenção de 2 meses no raw e histórico em `gold/fct_resumo_mensal/mes_referencia=*/`; testes de fonte por mês (ADR-0012; pedido do usuário) | active | 2026-09-28 |
| AD-016 | Modelo estrela para BI: `sk_*` inteiras, membro -1, `dim_data`, hierarquias, `fct_resumo_mensal` para Import no Power BI, `docs/POWER_BI.md` + exposure (ADR-0013; pedido do usuário) | active | 2026-09-28 |
| AD-017 | Convenção de idioma (decisão do usuário 2026-09-29): inglês só no vocabulário padrão do dbt/ferramentas (lista fechada no ADR-0014); todo o resto em português; lote RN aplica as renomeações após o B5 | active | 2026-09-29 |

## Handoff

**Retomado em 2026-09-29 após a 2ª pausa.** Verificação ok (`main` limpo em `86fa2e5`; `make ci` PASS=45 WARN=1 ERROR=0). F1a concluída e integrada (`b5012a6`). Próximo: B5 (T14–T15, Opus médio).

- **main** = `7530018` (+ commit deste handoff), verde: 106 unit + 5 integração; `make ci` PASS=45 WARN=1 ERROR=0; lint ok.
- **Integrado:** P0, B1, B2, B3, B4, B9a, **R1** (relatório `docs/revisoes/R1.md`, triagem `docs/revisoes/R1-triagem.md`) e **F1b** (R1-04, R1-10 parte convert, R1-23, R1-24).
- **Interrompido: F1a** (correções R1 FX1–FX7; agente `eba62c6d`, Claude Sonnet médio, **parado, não arquivado**). Worktree `~/.traycer/worktrees/local__dbt-pipeline-rfb-v2__5a2294e72f/correcao-f1a-r1-ingestao-dbt`, branch `correcao/f1a-r1-ingestao-dbt` (base `a6ed57c`, **não** contém F1b):
  - Commitados (ainda não verificados pelo líder): FX1 `d45ef8d` (R1-01/02/16/19), FX2 `fb53801` (R1-03/17/18/20), FX3 `7d66721` (R1-08/09/26, P7), FX4 `2a03c6e` (R1-07).
  - **WIP** `622fbc9`: FX5 parcial (dbt: R1-05/06/12/13/15/25) salvo pelo líder na pausa — gates não rodados; deve ser revisado/completado e reescrito como `fix(dbt)` definitivo.
  - Faltam: concluir FX5, **FX6** (testes que afirmam a spec — R1-10 exceto convert; re-rodar mutações M4, M14, M18/M19 em test_schemas, M20) e **FX7** (pre-commit sqlfluff — R1-14), e anotar "resolvido em" na triagem.

### Como retomar (líder)
1. `git status` (limpo) e `make ci` em `main` → PASS=45 WARN=1.
2. Reativar o agente `eba62c6d` (mensagem com o brief original da F1a + este estado: FX1–FX4 feitos, FX5 em WIP `622fbc9`, faltam FX5/FX6/FX7; pedir para primeiro fazer `git rebase main` ou `merge main` para incorporar F1b, depois completar). Se indisponível, criar Sonnet médio novo no mesmo worktree com o mesmo brief + triagem do diff herdado.
3. Verificar por evidência (make ci, make lint, mutações), integrar F1a, e disparar **B5** (T14–T15, Opus médio).
4. Sequência restante: B5 → R2 → B6 (T32 + R1-11/21/22, T16–T18, T33, T19–T20) → B7 → B7b → R3 → B8 (T28, T36) ∥ B9b → R4 → R5 → RETRO + billing.

### Contexto importante para os próximos briefs
- Roteamento: AD-014 (médias → Sonnet médio). Melhorias do usuário: AD-015/ADR-0012 (atualização mensal) e AD-016/ADR-0013 (estrela para Power BI).
- Pendências: P1, P2 (guia → R5), P8 (→ B9b) em `docs/revisoes/pendencias.md`; R1-11, R1-21, R1-22 adiados para T32 (B6); teste de CLI para `EntidadeVaziaError` (F1b) ainda sem cobertura.
- Lições: escrever arquivos grandes incrementalmente; unit tests dbt sobre fontes `external_location` exigem `format: sql`; rejeitos do DuckDB acumulam por conexão; hive automático em `mes_referencia=` (fontes usam `hive_partitioning=false` + `_mes_referencia`); `lpad` do DuckDB trunca; `strptime` falha em data inválida (usar `try_strptime`).
- WebDAV da RFB trava downloads — B8 deve monitorar. Worktrees já integrados (b1, b2, b3, b4, b9a, r1, f1b) podem ser limpos com `traycer-housekeeping`.
