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

## Handoff

- Feature: `rfb-dbt-port` — spec e tasks aprovados pelo líder.
- Próximo passo: lote B1 (T1–T3).
