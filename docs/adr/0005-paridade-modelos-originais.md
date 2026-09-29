# ADR-0005 — Paridade dos modelos originais; adições no star schema

**Contexto.** O original tem `bh_empresas` (flat granular) e `agg_empresas` (flat agregada) com inner joins
que descartam silenciosamente estabelecimentos sem CNAE/município correspondente na Base dos Dados.

**Decisão.** `bh_empresas` e `agg_empresas` reproduzem as colunas e regras do notebook 3 (inclusive inner
joins), com nomes em snake_case minúsculo. Um modelo de paridade traduz o SQL original literalmente para
DuckDB e um teste exige diferença zero. Os descartes passam a ser **medidos** por teste (warn). Melhorias de
modelagem (left joins com membro "não informado", região imediata/intermediária, Simples/MEI, CNAEs
secundários explodidos) vão para o star schema `marts/core` — atendendo o "trabalho futuro" citado no original.

**Emenda (2026-09-29, R2-01).** O staging aplica `trim` aos textos; o Spark do original não
(`ignoreLeadingWhiteSpace=false`). Em dados reais (fev/2025), ~752 estabelecimentos sem nome fantasia têm razão social
com espaço à esquerda. Decisão: `bh_empresas.nome` mantém o `trim` (`meta.escopo: adaptado`); o modelo de auditoria
continua literal e só alinha `trim(nome)` no select final (como o lpad do CNAE); um teste `warn` conta os casos.

**Consequências.** Quem conhece o MVP encontra as mesmas tabelas; quem precisa de completude usa o core.
