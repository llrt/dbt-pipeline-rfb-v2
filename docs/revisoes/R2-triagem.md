# Triagem da R2 (líder, 2026-09-29)

Veredito da R2: **REPROVADO** por 1 bloqueante (R2-01); RN isolado APROVADO COM RESSALVAS ([R2.md](R2.md)).
Evidência nova e decisiva: o revisor rodou `bh_empresas` e os testes sobre o **extrato real de fev/2025**
(62,6 M linhas; mesmo mês do MVP original; CSVs do projeto v1 nesta máquina, só leitura). O líder reproduziu
R2-01 (1.685 razões sociais com espaço na borda; 753 estabelecimentos sem nome fantasia afetados) e R2-02
(4 inícios de atividade antes de 1800; menor = 1194-08-15) diretamente no raw real.

## Decisões do líder

| Achado | Decisão | Lote | Resolvido em |
|---|---|---|---|
| **R2-01** paridade × trim | **Adaptação declarada** (ADR-0005, emenda): `bh_empresas.nome` mantém o `trim` do staging (espaço de borda é artefato do arquivo, não informação) e passa a `meta.escopo: adaptado`. A paridade continua literal e só **alinha** esse ponto no select final (`trim` sobre `nome`), como já faz com o CNAE — comentado. Novo teste **warn** que conta os casos afetados (fev/2025 real ≈ 752). Fixture nova: razão social com espaço à esquerda e sem nome fantasia (não altera as respostas conhecidas da spec). | F2a | `6469a40` |
| **R2-02** idade [0,200] | **Spec emendada** (Original AC 12): severidade `warn` com `error_if: ">100"` (linhas); + teste de fonte/staging `warn` para `dat_inicio_atividade < 1800-01-01`. Dado absurdo da RFB é registrado, não derruba o pipeline; não anular no staging (quebraria a paridade). | F2a | `23c68d5` |
| **R2-03** `_data_referencia` NULL silencioso | `not_null` (error) em `_data_referencia` nas fontes RFB do mês e em `stg_rfb__estabelecimentos`. | F2a | `75ada4f` |
| **R2-04** filtro de mês de estabelecimentos | unit test equivalente ao de empresas. | F2a | `381ec81` |
| **R2-05** "3 descartes" não afirmado | teste de integração afirmando exatamente K, L, M. | F2a | `381ec81` |
| **R2-06** emulação do inferSchema sem exercício | unit test dbt no modelo de auditoria com códigos que só casam via cast (ex.: `'0001'` × `'1'`, CNAE `'0111301'` × `111301`). | F2a | `381ec81` |
| **R2-07** guarda de contatos por nome exato | padrão por regex (`email|e_mail|tel|telefone|ddd|fax|contato`) em todas as colunas do banco, severidade error. | F2a | `381ec81` |
| **R2-08 = P13** `paridade/`, `paridade__` | renomear para `models/audit/` e `audit__bh_empresas_sql_original`; atualizar listas da guarda. | F2a | `7660cad` |
| **R2-12** custo da paridade | adotar comparação por `(cnpj_completo, hash(colunas))` — mesmo resultado, 3,4× mais rápida. | F2a | `aade503` |
| **R2-13** limpezas | (a) remover `nullif(...,'0')` redundante; (b) padronizar `id_municipio_rf` com lpad em `stg_bd__municipios` e remover a duplicação. | F2a | `aade503` (a, b; c fora do escopo F2a) |
| **R2-09** nomes estruturais fora do ADR-0014 | `data/`→`dados/`; `part-*`→`parte-*`; `extract-*`→`extracao-*`; `_rfb_rejeitos_scan`→`_rfb_rejeitos_varredura`; `DBT_DUCKDB_PATH`→`CAMINHO_DUCKDB`; `_no_implementado`→`_nao_implementado`. **Mantidos** e acrescentados à lista do ADR-0014: `warehouse` (arquivo `warehouse.duckdb`, vocabulário dbt/data warehouse) e nomes de targets dbt `dev`/`ci`/`s3`. | F2b | — |
| **R2-10** guarda não cobre env vars | guarda passa a verificar variáveis de ambiente do projeto (lista permitida) e corrige a regex de alvos do Make; nomes após prefixo, macros, testes e seeds ficam fora (exigiriam dicionário — registrado como limitação). | F2b | — |
| **R2-11** variáveis antigas ignoradas | erro claro se `DATA_ROOT`/`DATA_ROOT_LOCAL` estiverem definidas, com instrução de migração. | F2b | — |

Nota F2a (worker, 2026-09-30). Mutações D01, M06, M07b e M15 agora morrem; M11, M12, M16 e o trim continuam
mortas pela paridade por hash. Validação no extrato real de fev/2025 (`dbt build --target dev -s +bh_empresas
+paridade_bh_empresas`, `DUCKDB_MEMORY_LIMIT=16GB`): PASS=68 WARN=5 ERROR=0 em 93 s (pico de RSS ≈ 26 GiB com
8 threads); `paridade_bh_empresas` PASS (8,5 s isolada, RSS ≈ 16 GiB); warns: trim 752, idade fora de
[0, 200] 2, início < 1800 4, descartes 1.961.509, CNAEs sem par 3; `_data_referencia` not_null PASS.

## Nova decisão de projeto (AD-018)
O extrato real de **fev/2025** (mesmo mês do MVP original) está disponível localmente no projeto v1. O B8 passa a
incluir, além da execução real de 2026-09: converter fev/2025 (só leitura do v1) e **comparar os números do estudo
de caso com os publicados no notebook 4 do original** (ex.: Fundão/ES, CNAE 4741500: 1 ativa + 4 inativas; idade
3,9 anos) — paridade **numérica**, não só lógica, para o mês original.

## Sequência
F2a (Opus médio — origem T14/T15) → merge → F2b (Sonnet médio — origem T37; toca a mesma guarda) → merge → B6.
