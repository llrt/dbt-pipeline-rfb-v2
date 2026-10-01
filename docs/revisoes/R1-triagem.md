# Triagem da R1 (líder, 2026-09-29)

Veredito da R1: **APROVADO COM RESSALVAS** — 0 bloqueantes, 10 importantes, 14 menores, 3 sugestões ([R1.md](R1.md)).
O líder reproduziu R1-05, R1-08, R1-09 e R1-15 antes de aceitar. Todos os importantes serão corrigidos **antes do B5**.

## Decisão por achado

| Achado | Decisão | Onde | Lote de correção | Resolvido em |
|---|---|---|---|---|
| R1-01, R1-02, R1-16, R1-19 | corrigir já — resiliência do download/listagem (teto global, retry no PROPFIND, erro com URL, tamanho ausente = None, `If-Range`) | `rfb_client.py`, `cli.py` | F1a (Sonnet médio) — FX1 | `d45ef8d` |
| R1-03, R1-17, R1-18, R1-20 | corrigir já — completude do mês (falhar/avisar com `--permitir-incompleto`), aviso de `_data_referencia` nula, lock de execução, manifesto incremental por entidade | `cli.py`, `manifest.py` | F1a — FX2 | `fb53801` |
| R1-08, R1-09, R1-26 (+P7) | corrigir já — modo s3 coerente (duckdb/temp locais via `DATA_ROOT_LOCAL`; secret escapado e usado), `.env.example` seguro, env vazia = padrão, `env_var` com padrão nas fontes; atualizar ADR-0007/ARCHITECTURE | `config.py`, `profiles.yml`, `storage.py`, `.env.example`, docs | F1a — FX3 | `7d66721` |
| R1-07 | corrigir já — checksum real no sync (metadado sha256 no objeto) | `storage.py` | F1a — FX4 | `2a03c6e` |
| R1-05, R1-06, R1-12, R1-13, R1-15, R1-25 | corrigir já — datas via `try_strptime`, `not_null`/unicidade sobre `cnpj_completo`, exceção obsoleta detectada, `meta.escopo` em todos os nós, `lpad` sem truncar (teste de tamanho), unicidades BD | dbt | F1a — FX5 | `f264d1f` |
| R1-10 (exceto partes de `test_convert.py`) | corrigir já — testes que afirmam a spec (lista literal de colunas, ligação CLI↔idempotência, sha256 conhecido, `_resolver_mes`) | `tests/` | F1a — FX6 | `59b0480` |
| R1-14 | corrigir já — hook sqlfluff do pre-commit | `.pre-commit-config.yaml` | F1a — FX7 | FX7 (este commit) |
| R1-04, R1-24, R1-23, R1-10 (partes em `test_convert.py`) | corrigir já — falha em entidade com 0 linhas, teste de atomicidade da publicação, zip-slip sem caminho fixo, contrato de colunas afirmado literalmente | `convert.py`, `test_convert.py` | F1b (Opus médio — origem B3) — **resolvido** em `54368a4` `88f9312` `081d8be` (M15, M17, M18, M19 morrem) | — |
| R1-11, R1-21, R1-22 | adiar para **T32** (B6), onde as fixtures ganham o 2º mês e o multi-mês fica testável | dbt | B6 | `b0b1869` |
| R1-27 | corrigido pelo líder: `--data-root` desmarcado/removido de T10 em tasks.md | tasks.md | — | — |

F1a e F1b tocam arquivos disjuntos e rodam em paralelo; merge sequencial com `make ci` verde entre eles.
