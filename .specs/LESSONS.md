# LESSONS - auto-maintained by scripts/lessons.py

> Machine-owned. Do NOT hand-edit. Changes are overwritten on the next `lessons.py` write.
> Canonical state lives in `.specs/lessons.json`. Edit lessons only via the script.
> promote_threshold=2 distinct features · window_days=45 · quarantine_threshold=2

## Confirmed (load these at Specify/Design)

Corroborated across multiple features. Safe to apply as guidance.

_none_

## Candidates (under observation - do NOT load as guidance yet)

Seen once or not yet corroborated. Tracked, not trusted.

### L-001 - Para provar que um passo regrava um artefato, apague-o (ou mude-o) antes do passo e afirme que voltou com o conteúdo esperado; checar só a existência não discrimina.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `tests/integration` · harmful: 0
- features: rfb-dbt-port
- evidence: transform/models/marts/core/fct_resumo_mensal.sql:2 (R4-D04) (tests/integration)
- last seen: 2026-10-01T16:41:21Z

### L-002 - Quando uma emenda muda fixture, prazo ou contagem, atualize no mesmo commit todo AC e teste independente da spec que cite o valor antigo.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `.specs` · harmful: 0
- features: rfb-dbt-port
- evidence: spec.md:200,205,265 (CORE AC 1/6, OPS AC 1) (.specs)
- last seen: 2026-10-01T16:41:21Z

### L-003 - Um caminho alternativo de build (backfill, reprocesso) que grava no destino final precisa dos mesmos testes error a montante do caminho normal, ou gravar em área temporária e promover só após passar.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `transform/selectors.yml` · harmful: 0
- features: rfb-dbt-port
- evidence: transform/selectors.yml:6-20 (R4-02) (transform/selectors.yml)
- last seen: 2026-10-01T16:41:21Z

## Quarantined (failed when applied - ignore)

A confirmed lesson that recurred alongside failure. Kept for the maintainer to review.

_none_
