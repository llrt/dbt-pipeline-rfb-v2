# RETRO — port do MVP RFB/CNPJ para dbt + DuckDB (v1)

> Retrospectiva do líder (agente Traycer "Migração dbt DuckDB MVP v2", Claude Opus 5.5), 28/09 a 01/10/2026.
> Custos por agente: [docs/CUSTOS_AGENTES.md](docs/CUSTOS_AGENTES.md). Decisões: `.specs/STATE.md` (AD-001..AD-029)
> e `docs/adr/` (0001–0016). Revisões: `docs/revisoes/`.

## 1. O que foi entregue

| Área | Resultado |
|---|---|
| Port do original | Notebooks 1–4 do MVP Databricks reproduzidos em dbt-core + dbt-duckdb sobre Parquet local/S3: `bh_empresas`, `agg_empresas`, estudo de caso (q1–q4) |
| Fidelidade | Paridade linha a linha com a **tradução literal do SQL original**: 0 diferenças em 71,4 M linhas (2026-09) e 62,6 M (fev/2025); números do notebook 4 reproduzidos em fev/2025 (1 ativa + 4 inativas, MICRO; idade 3,8 × 3,9 explicada pela data de referência) |
| Adições | Modelo estrela para Power BI (chaves inteiras, membros −1/−2, `dim_data`, série mensal particionada), análises novas (concorrência, sobrevivência por coorte, dinâmica, fornecedores por distância), DQ (DV de CNPJ, taxa de conversão tipada, reconciliações, histórico de testes, catálogo gerado), relatório gerado |
| Melhorias pedidas no caminho | Atualização mensal (`rfb atualizar`), modelo estrela/guia Power BI, enriquecimento com a Base dos Dados (incremento `enriquecimento_bd`: Censo 2022, regiões metropolitanas, vizinhança, área de mercado com vazios), publicação opcional no MotherDuck, guia dbt ampliado, revisão de boas práticas, máscara de CPF |
| Operação real | `rfb pipeline` em 2026-09: 73,4 M estabelecimentos, PASS=339 WARN=14 ERROR=0, 339 s com o raw presente (download de 7 GB ~21 min); `rfb atualizar` no-op em 0,56 s |
| Qualidade do código | `make ci` ~130 s (unit + lint + freshness + 2 meses + backfill + ~124 testes de integração); 107 ACs da spec com evidência (Verifier da R4); 32 merges em `main`, 256 commits |

## 2. Processo: o que funcionou

- **Lotes pequenos, agente novo por lote, worktree por lote e verificação pelo líder antes de cada merge.**
  Em todo lote o líder reexecutou `make ci`, consultou o gold e rodou ao menos uma **mutação própria**.
  Isso pegou problemas que o relatório do worker não mostrava: referências inventadas no guia (B9b),
  vazios de mercado para CNAE desconhecido (B12), lentidão que era sleep do Mac (B7).
- **Revisões independentes com dados reais.** A R2 reprovou a paridade só por rodar sobre o extrato real
  (espaço nas bordas); a R3 achou o capital social inflado 15,6×, a tabela "leve" de 22 M linhas e o
  calendário desde 1194; a R4 achou CPF completo em 12,5 M nomes. Nenhum desses aparecia nas fixtures.
- **Testes de mutação como métrica de revisão.** Cada revisão rodou de 20 a 28 mutações; as sobreviventes viraram
  testes nos lotes de correção. Ao fim, as mutações sobreviventes das revisões anteriores morrem no próprio dbt/CI.
- **Paridade com tradução literal do SQL original** (EXCEPT ALL → hash por linha) como rede de segurança:
  toda adaptação precisou ser **declarada** (trim, `upper` da q4, dedup de raiz, máscara de CPF) e alinhada.
- **Spec viva com emendas rastreáveis** (EARS + `tasks.md` validado por script + `STATE.md` com decisões).
- **Escada de escalonamento de modelos**: DeepSeek (P/NC) → Sonnet (M/NC) → Opus (crítico/E2E/revisões).

## 3. Achados de produto (dados reais)

1. **O "nada nas imediações" do notebook 4 era um bug**: comparava município em MAIÚSCULAS com a grafia mista
   da Base dos Dados e sempre achava 0. Com a comparação corrigida (adaptação declarada), fev/2025 mostra
   1 fabricante na microrregião de Fundão, 12 atacadistas e 155 estabelecimentos com CNAE de fornecedor.
2. **Fundão perdeu sua única loja de tintas ativa** entre fev/2025 e 2026-09 (0 ativas, 5 inativas), mas a área
   de mercado tem 57 ativas nos vizinhos e 182 na RM Grande Vitória.
3. **Dados pessoais escondidos em dado "de empresa"**: 12,5 M razões sociais de EI/MEI terminam em CPF completo
   (e 908 o trazem no meio). Mascarado no gold por decisão do usuário (ADR-0008).
4. **A RFB mudou sob nossos pés**: primeiro CNPJ alfanumérico real (Banco do Brasil), raiz de CNPJ duplicada,
   bytes C1 no latin-1, datas de 1194; Base dos Dados com caminho de download congelado em 2023 (população e PIB
   em 2021 — corrigido para 2025/2023 pela API atual) e um município criado em 2025 sem código RFB.

## 4. O que não funcionou ou custou caro

| Problema | Efeito | Lição |
|---|---|---|
| DeepSeek no B2 (`finish=length`) | lote perdido, refeito em Sonnet | modelo pequeno + arquivo grande numa resposta = falha; pedir escrita incremental sempre |
| Gemini 3.8 Flash no guia (B9b) | caminhos, checks e SQL "compilado" inventados; 43 erros técnicos na RBP | modelo rápido para texto longo exige verificação por script (caminhos/nomes contra o manifesto) e revisão técnica independente; com protocolo explícito ele corrigiu bem |
| Brief do líder com nome errado (`paridade` como domínio) | retrabalho (P13/R2-08) | a convenção de idioma (ADR-0014) vale também para os briefs; o líder errou e o usuário apontou |
| Mac em sleep com DarkWake a cada 15 min | `make ci` de 20 s levando 16 min; diagnósticos falsos de lentidão | `caffeinate -i` em todo comando longo; olhar `pmset -g log` antes de culpar o código |
| Testes que afirmavam fixtures, não regras | mutações sobrevivendo em R3/RBP/R4 | unit tests de regra + invariantes no dbt, não só pytest sobre fixtures |
| Gold "corrente" × backfill (P22) | três rodadas (B7b, B8, F4) até ficar seguro | caminho alternativo que grava no destino final precisa dos mesmos gates e de área temporária + promoção atômica (lição L-003) |
| `temp_directory` (RBP-01 → B8) | a correção da RBP quebrou com spill no DuckDB 1.5; virou `config_options` | conferir o efeito real (`current_setting`) e rodar em dado real antes de fechar |
| Meta de CI < 120 s | ultrapassada ao incluir unit + lint + freshness + integração | metas de tempo mudam com o escopo do CI; revisar a meta junto (AD-026) |

## 5. Lições para os próximos projetos

1. **Verificação por evidência do líder em todo merge** (gates + consulta ao dado + mutação própria) é barata e
   pegou erro em ~1/3 dos lotes.
2. **Rodar em dado real cedo** (já na R2): fixtures sintéticas não mostram espaços, CPFs, códigos novos, datas absurdas.
3. **Declarar adaptações** em vez de "corrigir" o original em silêncio; a paridade literal obriga isso.
4. **Para documentação gerada por modelo, script de verificação contra o repositório** (caminhos, nomes no manifesto,
   linhas citadas) antes de qualquer revisão humana.
5. **Uma pendência por linha com dono e lote** (`pendencias.md`) evita que achados se percam entre revisões.
6. **Lições do Verifier** (`.specs/LESSONS.md`): provar regravação apagando antes (L-001); emenda de fixture
   atualiza todos os ACs que citam o valor (L-002); caminho alternativo de build com os mesmos gates (L-003).

## 6. Custo (resumo)

Detalhe por agente em [docs/CUSTOS_AGENTES.md](docs/CUSTOS_AGENTES.md). Total **US$ 247,38 ≈ R$ 1.295**
(câmbio R$ 5,2353), dos quais **US$ 236,83 são equivalente de API da assinatura Claude** (sem desembolso adicional)
e **US$ 10,55 foram cobrança real do OpenRouter** (Gemini 3.8 Flash US$ 10,23; DeepSeek v4 Flash US$ 0,32).

| Papel | US$ | % |
|---|---:|---:|
| Líder (planejamento, verificação de cada merge, triagens, docs) | 88,11 | 36 % |
| Implementação (17 lotes) | 77,74 | 31 % |
| Correções pós-revisão (9 lotes) | 42,46 | 17 % |
| Revisões independentes (5) | 39,07 | 16 % |

Leituras: revisão + correção ≈ um terço do custo e foram responsáveis pelos achados mais valiosos; o lote mais caro
foi o B8 (US$ 16,25, E2E real); Opus 5.5 respondeu por 69 % do custo (líder, críticos e revisões).

## 7. Pós-entrega (fora da v1)

- **Fase 2 da Base dos Dados** (BigQuery: pirâmide etária, RAIS, exportadoras) — AD-029; estimativa construir
  ≈ US$ 28–36 equivalente (R$ 150–190), operar ≈ R$ 0/mês.
- **1ª publicação real no MotherDuck** (P25) e confirmação da transação no `md:`.
- **Power BI de fato carregado** (único Success Criterion sem evidência na R4) e medidas DAX testadas.
- Mês real seguinte (2026-10) via `rfb atualizar`.
- *(Resolvido após a entrega)* **GitHub Actions**: o 1º run no repositório publicado falhou porque o Makefile usava `set -o pipefail` e o `/bin/sh` do Ubuntu é `dash` (no macOS é bash); corrigido com `SHELL := /bin/bash`, run verde em ~6,5 min. Lição: o CI local roda no mesmo SO do desenvolvedor — fixe o shell do make.
- Sugestões R4-11 pendentes: warn de controles C1 nos nomes, raiz alfanumérica em teste de unidade,
  gitleaks/detect-secrets, teto de descompressão contra zip bomb.
- Limpeza: dados reais nos worktrees (`lote-b8…/dados` ~51 GB) e worktrees integrados (`traycer-housekeeping`).
