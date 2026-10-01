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
| AD-007 | `RAIZ_DADOS` local ou `s3://`; sync via boto3; testes com moto (ADR-0007) | active | 2026-09-28 |
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
| AD-018 | Extrato real de fev/2025 (mesmo mês do MVP; CSVs do projeto v1, só leitura) entra no B8 para paridade **numérica** com os resultados publicados no notebook 4 do original, além da execução real de 2026-09 | active | 2026-09-29 |
| AD-019 | Emendas da R2: `bh_empresas.nome` com trim declarado como adaptação (ADR-0005); idade fora de [0,200] = warn com error_if >100 (spec Original AC 12) | active | 2026-09-29 |
| AD-020 | Emendas da R3: resumo mensal sem `ano_inicio_atividade`/`natureza` e capital só de matrizes (ADR-0013, BI-02 AC 5); `dim_data` desde 1900 com −1/−2 sentinela (BI-01 AC 2); notebook 4 q4 com `upper` = adaptado; `data_nao_futura` fora das exclusões do Simples (DQ-01 AC 2); `DBT_THREADS` × `DUCKDB_THREADS` | active | 2026-10-01 |
| AD-021 | Guia dbt (B9b) reescrito/ampliado por **Gemini 3.8 Flash high via OpenRouter** a pedido do usuário (exceção ao roteamento AD-014); cinco partes + índice, foco em qualidade antes/depois de cada etapa; correção técnica garantida pela R5 (Opus alto) | active | 2026-10-01 |
| AD-022 | Pedido do usuário: revisão do projeto à luz das boas práticas do guia (**RBP**, Claude Opus alto, agente novo, `traycer-review`). Roda depois de F3b e do B9b integrados; **absorve a R5** (valida também a correção técnica do guia contra a documentação oficial), para o checklist usado na auditoria ser confiável. Gaps viram lote de correção (nível de origem) antes do B8; o que for adição fica marcado como tal | active | 2026-10-01 |
| AD-023 | Usuário aprovou a **Fase 1** do enriquecimento com a Base dos Dados (ADR-0015): download pela API `downloadTable` (corrige população/PIB defasados), Censo 2022 por município, regiões metropolitanas, vizinhança, mart de área de mercado; antes do B8; Fase 2 (BigQuery) adiada. Artefatos marcados com o incremento `enriquecimento_bd` (`meta.incremento` + tag `incremento_enriquecimento_bd`) a pedido do usuário. Lote B10 (Sonnet médio), em paralelo à RBP | active | 2026-10-01 |
| AD-024 | Triagem da RBP: corrigir os 43 erros do guia (FBPg, Gemini 3.8 Flash — nível de origem, AD-021) e os gaps do projeto RBP-01..11, 13, 14 (FBPa, Sonnet médio, após o B10); `dbt_expectations` passa a ser usado (volume/tipagem) em vez de removido; CI remoto (GitHub Actions) e `selectors.yml` adotados como adição; RBP-12 → B8; groups/access, project-evaluator, Elementary, snapshots: não agora | active | 2026-10-01 |
| AD-025 | Pedido do usuário: publicação opcional no MotherDuck (`rfb publicar --destino motherduck`, desacoplada do dbt, só com `MOTHERDUCK_TOKEN`+`MOTHERDUCK_BANCO`; sem token configurado hoje) e seção "Como o Power BI acessa os dados" (Parquet × DuckDB local/ODBC × MotherDuck/Postgres endpoint) — ADR-0016, PUB-01/02, T42–T43, lote B11 (Sonnet médio) antes do B8; 1ª publicação real só com OK do usuário | active | 2026-10-01 |
| AD-026 | Meta do `make ci` passa de < 120 s para < 180 s (spec, critério de sucesso): o CI agora roda unit + lint + freshness + 105 testes de integração (117 s medidos após FBPa); paralelizar a integração fica como opção futura | active | 2026-10-01 |
| AD-027 | R4: pronto para entrega com ressalvas. Usuário decidiu **mascarar o CPF** no fim da razão social (R4-01; ADR-0008 emendado). Correções F4 (Opus médio, nível do B8): Fix 1–4, 6, 7 + R4-05, 06, 08, 09, 10; Fix 5 (spec) pelo líder | active | 2026-10-01 |
| AD-028 | Pedido do usuário: corrigir a P23 (opção 1) — `mart_concorrencia_area_mercado` passa a incluir pares sem estabelecimento local quando vizinhos/RM têm ativos (vazios de mercado); lote pequeno B12 (Sonnet médio, nível do B10), depois do F4 e antes do RETRO; incremento `enriquecimento_bd` | active | 2026-10-01 |
| AD-029 | Usuário: Fase 2 da Base dos Dados (BigQuery: pirâmide etária, RAIS, exportadoras) fica para **pós-entrega**; a v1 fecha com o escopo atual (até B12, RETRO e relatório de custo). Estimativa registrada: construir ≈ US$ 28–36 equivalente de API (R$ 150–190; R$ 0 real na assinatura), operar ≈ R$ 0/mês (< 10 GB/mês dentro da faixa gratuita do BigQuery) | active | 2026-10-01 |
| AD-030 | **v1 encerrada**: B12 integrado, `RETRO.md` e `docs/CUSTOS_AGENTES.md` produzidos. Pós-entrega: Fase 2 BD, 1ª publicação MotherDuck, Power BI carregado de fato, GitHub Actions, sugestões R4-11, limpeza de worktrees/dados | active | 2026-10-01 |

## Handoff

**3ª pausa, 2026-09-29 18:40 (pedido do usuário).** `main` limpo em `66d221f` (+ commit deste handoff); último verde: 164 unit + 22 integração; `make ci` PASS=92 WARN=2 ERROR=0; lint ok.

- **Integrado:** P0, B1–B5, B9a, R1, F1a, F1b, RN, **R2** (relatório `docs/revisoes/R2.md`, triagem `docs/revisoes/R2-triagem.md`, emendas ADR-0005/0014/spec AC 12, AD-018/019).
- **Interrompido: F2a** (correções R2 no dbt; agente `36922fe0`, Claude Opus médio, **parado, não arquivado**). Worktree `~/.traycer/worktrees/local__dbt-pipeline-rfb-v2__5a2294e72f/correcao-f2a-r2-dbt`, branch `correcao/f2a-r2-dbt` (base `3148b45`):
  - Commitados pelo worker (gates rodados por ele a cada grupo; **ainda não verificados pelo líder**): `7660cad` P13 (`models/audit/`, `audit__`), `6469a40` R2-01 (trim adaptado + warn + fixture), `23c68d5` R2-02 (idade warn/error_if>100, warn <1800), `75ada4f` R2-03 (`not_null` `_data_referencia`), `381ec81` R2-04..07 (testes), `aade503` R2-12/13 (paridade por hash, limpezas).
  - **WIP** `cee196e` (salvo pelo líder na pausa): triagem R2 com notas "resolvido em" parcial + 1 linha em branco removida no ADR-0014 — revisar e reescrever/squash no commit final.
  - Faltam: **validação real fev/2025** (foi interrompida ~1 min após começar; ~24 GB RSS; raw do revisor em `/private/tmp/claude-501/-Users-llrt--traycer-worktrees-local--dbt-pipeline-rfb-v2--5a2294e72f-revisao-r2-b5-rn/3c78c3e8-ce3b-418d-b4d2-f6db20f5861c/scratchpad/real` — só leitura; se `/private/tmp` tiver sido limpo pelo reboot, reconverter do v1 `/Users/llrt/dev/workspaces/code-to-learn/vibe/traycer/dbt-pipeline-rfb/data/raw`, também só leitura), gates finais (`make lint && make ci`, `uvx pre-commit run --all-files`), commit final da triagem e relatório (hashes, PASS/WARN/ERROR, mutações D01/M06/M07b/M15, números reais: paridade PASS, warn trim ~752, idade 2, datas <1800 = 4, tempo/memória, custo da paridade por hash).

### Como retomar (líder)
1. `git status` (limpo) e `make ci` em `main` → PASS=92 WARN=2.
2. Reativar o agente `36922fe0` com: estado acima, pedir para conferir o WIP `cee196e`, rodar a validação real fev/2025 e os gates finais, e entregar o relatório. Se indisponível, Opus médio novo no mesmo worktree com o brief original (ver transcript) + este estado.
3. Verificar por evidência (make ci, lint, mutações, números reais), integrar F2a, atualizar PLANO/triagem e disparar **F2b** (Sonnet médio: R2-09..11 — `data/`→`dados/`, `part-`→`parte-`, `extract-`→`extracao-`, `_rfb_rejeitos_scan`→`_rfb_rejeitos_varredura`, `DBT_DUCKDB_PATH`→`CAMINHO_DUCKDB`, `_no_implementado`→`_nao_implementado`; guarda cobrindo env vars + regex do Make; erro se `DATA_ROOT`/`DATA_ROOT_LOCAL` definidos; manter `warehouse.duckdb` e targets dev/ci/s3).
4. Sequência restante: F2b → B6 (T32 + R1-11/21/22, T16–T18, T33, T19–T20) → B7 → B7b → R3 → B8 (T28 + paridade numérica fev/2025 AD-018, P9–P12; T36) ∥ B9b → R4 → R5 → RETRO + billing.

### Contexto importante para os próximos briefs
- Roteamento: AD-014 (médias → Sonnet médio). Melhorias do usuário: AD-015/ADR-0012 (atualização mensal) e AD-016/ADR-0013 (estrela para Power BI).
- Pendências: P1, P2 (guia → R5), P8 (→ B9b), P9–P12 (→ B8), P13 (→ F2a) em `docs/revisoes/pendencias.md`; R1-11, R1-21, R1-22 adiados para T32 (B6); teste de CLI para `EntidadeVaziaErro` (F1b) ainda sem cobertura.
- Lições: escrever arquivos grandes incrementalmente; unit tests dbt sobre fontes `external_location` exigem `format: sql`; rejeitos do DuckDB acumulam por conexão; hive automático em `mes_referencia=` (fontes usam `hive_partitioning=false` + `_mes_referencia`); `lpad` do DuckDB trunca; `strptime` falha em data inválida (usar `try_strptime`).
- WebDAV da RFB trava downloads — B8 deve monitorar. Worktrees já integrados (b1, b2, b3, b4, b9a, r1, f1b) podem ser limpos com `traycer-housekeeping`.
