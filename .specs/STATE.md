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

## Handoff

**Pausado pelo usuário em 2026-09-28** (desligamento do computador). Nenhum agente em execução; nenhum trabalho não commitado.

- **main** = `a3b2d38` (+ commit deste handoff), verde: 90 unit + 5 integração; `make ci` ≈ 7 s (dbt PASS=45 WARN=1 ERROR=0); `make lint` ok.
- **Concluído e integrado:** P0, B1 (T1–T3), B2 (T4–T7), B3 (T8), B4 (T9–T13), B9a (T29). Status detalhado: `docs/PLANO.md`.
- **Interrompido:** R1 (revisão fases 1–4). Agente `a84e9afe` (Claude Opus alto) **parado, não arquivado**, sem nenhum arquivo gravado; worktree `~/.traycer/worktrees/local__dbt-pipeline-rfb-v2__5a2294e72f/revisao-r1-fases-1-4`, branch `revisao/r1-fases-1-4` = `00af9fd` (código idêntico ao main atual; main só avançou em docs).

### Como retomar (líder)
1. `git -C <repo> status` e `git log --oneline -5` (esperado: limpo, main no commit do handoff); `uv sync --all-extras && (cd transform && uv run dbt deps) && make ci` → deve reproduzir PASS=45 WARN=1.
2. Retomar a R1: mandar mensagem ao agente `a84e9afe` pedindo que reinicie a revisão conforme o brief original (entregável `docs/revisoes/R1.md` + commit + resposta com veredito). Se o agente não estiver disponível, criar um Opus alto novo no mesmo worktree com o mesmo brief (escopo T1–T13, critérios: spec, robustez dados reais, segurança, ADRs, qualidade; confirmar/refutar P6/P7 de `docs/revisoes/pendencias.md`).
3. Após a R1: triar achados → correções por agente novo no nível do lote de origem (Sonnet para B2/B4, Opus para B3) → merge → **B5** (T14–T15, Opus médio).
4. Sequência restante: B5 → R2 → B6 (T32, T16–T18, T33, T19–T20) → B7 (T21–T27) → B7b (T34–T35) → R3 → B8 (T28, T36) ∥ B9b (T30–T31) → R4 (+ auditoria + Verifier) → R5 → RETRO.md + relatório de billing.

### Contexto importante para os próximos briefs
- Roteamento vigente: AD-014 (médias → Sonnet médio). Melhorias do usuário: AD-015/ADR-0012 (atualização mensal) e AD-016/ADR-0013 (estrela para Power BI).
- Pendências abertas: P1, P2 (guia → R5), P6, P7 (→ R1), P8 (→ B9b) em `docs/revisoes/pendencias.md`.
- Lições para os briefs: workers devem escrever arquivos grandes incrementalmente (falha do DeepSeek no B2 por `finish=length`); unit tests dbt sobre fontes `external_location` exigem `format: sql`; tabelas de rejeitos do DuckDB acumulam por conexão; hive automático em caminhos `mes_referencia=` (fontes usam `hive_partitioning=false` + `_mes_referencia`).
- Dados reais já validados em amostra (Empresas1/Estabelecimentos1 de 2026-09, 0 rejeitos). O WebDAV da RFB trava downloads — B8 deve monitorar.
- Worktrees de lotes já integrados (b1, b2, b3, b4, b9a) podem ser removidos com `traycer-housekeeping` quando conveniente.
