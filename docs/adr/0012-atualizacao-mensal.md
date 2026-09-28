# ADR-0012 — Atualização mensal com detecção de mês novo, retenção e série histórica

**Contexto.** A RFB publica um novo extrato por mês (pastas `YYYY-MM/` no WebDAV), preenchidas ao longo de
alguns dias. O desenho inicial já pegava o mês mais recente e particionava o raw por mês, mas não havia
comando para detectar novidade, checagem de completude, retenção, histórico nem receita de agendamento
(pedido do usuário em 2026-09-28).

**Decisão.**
1. **`rfb atualizar`** (e `make atualizar`): consulta o WebDAV, escolhe o **mês completo mais recente**
   (pasta com todos os arquivos esperados: `Empresas0–9`, `Estabelecimentos0–9`, `Simples` e os 6 domínios);
   compara com o último mês processado com sucesso (`DATA_ROOT/_estado/ultima_execucao.json`, gravado só
   após `dbt build` sem erro); se houver mês novo roda ingest → `dbt build --vars mes_referencia` →
   relatórios (→ `sync` se `s3://`); senão sai com 0 e "nenhum mês novo".
2. **Retenção:** mantém as partições raw dos últimos `RFB_MESES_RETIDOS` meses (padrão 2 — o atual e o
   anterior, para comparação/rollback) e apaga os zips baixados após sucesso (salvo `RFB_MANTER_ZIPS=true`).
3. **Série histórica:** `fct_resumo_mensal` grava **uma partição Parquet por mês**
   (`gold/fct_resumo_mensal/mes_referencia=YYYY-MM/`); reprocessar um mês substitui só a partição dele. O
   histórico não depende do `warehouse.duckdb` (que continua descartável, ADR-0001) nem da retenção do raw.
4. **Agendamento:** fora do escopo como orquestrador; `docs/OPERACAO.md` traz receitas prontas (cron,
   launchd, GitHub Actions). O comando é idempotente, então pode rodar diariamente.
5. O pipeline sempre passa `mes_referencia` explícito ao dbt (determinismo e localização da partição).

**Consequências.** Testes de unicidade nas fontes passam a ser por mês. Fixtures ganham um segundo mês
(2026-08) com diferença conhecida para testar a série e a detecção de novidade. SCD2 por estabelecimento
continua fora do escopo (volume ~65 M × meses); a série agregada cobre as análises de tendência.
