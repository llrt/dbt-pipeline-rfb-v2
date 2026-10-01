# ADR-0006 — Marcação de escopo original × adição no código

**Decisão.** Todo modelo, seed, teste singular e macro do projeto dbt declara `meta.escopo` ∈
{`original`, `adicao`, `adaptado`} e a tag `escopo_<valor>`. Colunas adaptadas também levam `meta.escopo`.
Assim `dbt ls --select tag:escopo_original` lista o escopo original e o `dbt docs` exibe a origem.
[docs/ESCOPO.md](../ESCOPO.md) é a tabela humana correspondente; um teste de CI (pytest sobre o
`manifest.json`) falha se algum nó do projeto não tiver `meta.escopo`.

**Emenda (2026-10-01, ADR-0015).** Além de `meta.escopo`, um nó pode levar `meta.incremento: <nome>` com a tag
`incremento_<nome>`, para agrupar uma melhoria transversal pedida pelo usuário. Primeiro uso:
`enriquecimento_bd` (novas bases da Base dos Dados).
