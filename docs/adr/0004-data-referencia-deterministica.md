# ADR-0004 — Data de referência determinística no lugar de `now()`

**Contexto.** O original calculava `idade_atual` com `datediff(now(), dat_inicio_atividade)/365.25`.
O resultado muda a cada execução e torna testes não determinísticos.

**Decisão.** Idade (e toda métrica temporal) é relativa a `data_referencia`: var dbt, com padrão igual à
data do extrato da RFB (`_data_referencia`, extraída do nome interno dos arquivos, ex. `D60912` → 2026-09-12).

**Consequências.** Mesma entrada ⇒ mesma saída. Em `bh_empresas` isso é a única divergência intencional
da regra original, marcada `escopo: adaptado` na coluna.
