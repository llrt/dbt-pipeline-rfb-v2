# ADR-0011 — Processo: equipe de agentes, roteamento de modelos e lotes

**Contexto.** O projeto é executado por uma equipe de agentes coordenada por um agente líder, seguindo o
guia de seleção de agentes do Traycer (`~/.traycer/agent-selection-guide.md`).

**Decisão.** Tarefas classificadas por complexidade (P/M/G) e criticidade (crítica/não crítica); no máximo 4
tarefas críticas ou grandes. Roteamento: planejamento/arquitetura/revisões/auditoria = Opus (alto esforço);
tarefas críticas e E2E = Opus (esforço médio); não críticas grandes = Sonnet (médio); não críticas
médias/pequenas = DeepSeek v4 flash via OpenRouter (esforço alto/baixo). Execução em lotes de até 7 tarefas
do mesmo nível, sequenciais, cada lote num worktree git e agente novo; o líder verifica por evidência (git
log + gates) antes do próximo lote. Documentação em arquivos disjuntos pode correr em paralelo.
**Atualização (2026-09-28, decisão do usuário):** tarefas médias não críticas passam a usar Claude Sonnet (esforço médio), após a falha do worker DeepSeek no lote B2 (estouro de limite de saída sem produzir código). Pequenas continuam em DeepSeek v4 flash (baixo).

Detalhes e tabela de lotes em [docs/PLANO.md](../PLANO.md).
