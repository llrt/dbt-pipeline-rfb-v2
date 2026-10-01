# Operação: pipeline real e atualização mensal

Como rodar o pipeline sobre os dados reais da RFB, manter a base atualizada todo mês e agendar a
execução. A atualização mensal, a retenção e a publicação no MotherDuck são **melhorias pedidas pelo
usuário** (ADR-0012, ADR-0016); o original carregava um único mês à mão.

## Comandos

| Comando | O que faz |
|---|---|
| `make pipeline MES=2026-09` (`rfb pipeline --mes 2026-09`) | Ingestão → `dbt source freshness` → `dbt build --vars mes_referencia` → relatório (`docs/RELATORIO_ESTUDO_CASO.md`) → publicação no MotherDuck (se configurada) → estado. Sai ≠ 0 na primeira etapa que falhar. Sem `MES`, usa o mês completo mais recente. |
| `make atualizar` (`rfb atualizar`) | Consulta o WebDAV (só listagem), escolhe o **mês completo mais recente** e compara com `RAIZ_DADOS/_estado/ultima_execucao.json`. Mês novo → `rfb pipeline` daquele mês + retenção. Senão imprime `nenhum mês novo` e sai com 0 **sem baixar nada**. |
| `rfb pipeline --mes 2025-02 --mes 2026-09` | Vários meses: sempre do **mais antigo ao mais novo** (ver "Ordem dos meses"). |
| `rfb pipeline --sem-ingestao --mes AAAA-MM` | Usa o raw que já está em `RAIZ_DADOS` (útil para refazer só o dbt). |

Opções comuns a `pipeline` e `atualizar`: `--origem-local DIR` (fixtures, sem rede),
`--permitir-incompleto`, `--forcar` (reconverte), `--target` (padrão: o do profile; `s3` com
`RAIZ_DADOS=s3://`), `--saida-relatorio ARQ`, `--sem-relatorio`, `--sem-publicar`. O `make ci` usa
exatamente esses comandos sobre as fixtures (pipeline 2026-08 → atualizar 2026-09 → atualizar no-op →
backfill de 2026-08).

Cada etapa imprime `== etapa <nome>: <segundos>s` e o fim do mês imprime o resumo
`pipeline <mês> [corrente|backfill] concluído em …`.

## Estado e ordem dos meses (P22)

- `_estado/ultima_execucao.json` (`mes_referencia`, `data_referencia`, `concluido_em`) só é gravado
  quando **todas** as etapas do mês terminam bem (build, relatório e publicação). Falha do dbt deixa o
  estado como estava: a próxima `rfb atualizar` tenta o mesmo mês de novo.
- O build de um mês regrava os marts `external` de `gold/` (dimensões, `fct_estabelecimentos`, marts,
  `agg_empresas`). Por isso o mês do estado é o **gold corrente**, e um mês **mais antigo** que ele roda
  como **backfill**: o dbt usa um `external_root` temporário (`RFB_EXTERNAL_ROOT`) e um `.duckdb`
  temporário em `RAIZ_DADOS/_tmp/backfill-*`, e só a partição do mês de `fct_resumo_mensal` e o
  histórico de DQ chegam ao gold real. O seletor `backfill_resumo_mensal` (`transform/selectors.yml`)
  constrói **e testa** `+fct_resumo_mensal` (staging, dimensões, fato e resumo, menos os dois testes
  que comparam com o gold corrente). A partição é gravada numa raiz temporária (`RFB_RAIZ_SERIE`,
  macro `raiz_serie`) e o `rfb pipeline` só a move para `gold/fct_resumo_mensal/mes_referencia=AAAA-MM/`
  (`rename` no mesmo disco, substituindo a anterior) **depois** de o build inteiro passar (R4-02). Um
  teste `error` no backfill deixa a partição do gold como estava.
- O teste `fct_resumo_mensal_gold_corrente` (warn) acusa um gold corrente **atrasado**: se a série
  mensal tem um mês mais novo que o do build, alguém rodou um mês antigo por cima do corrente (por exemplo,
  `dbt build --vars mes_referencia` à mão). Correção: reprocesse o mês mais novo.
- Um `flock` em `_estado/pipeline.lock` impede dois `pipeline`/`atualizar` simultâneos na mesma
  `RAIZ_DADOS` (a ingestão tem a sua trava, `_estado/rfb.lock`).

## Retenção

Após um `rfb atualizar` bem-sucedido:

- `RFB_MESES_RETIDOS` (padrão **2**: o mês atual e o anterior, para comparação e rollback): mantém em
  `raw/rfb/<entidade>/` só as partições dos N meses mais recentes; as demais são apagadas. A série
  `fct_resumo_mensal` não depende do raw e preserva todos os meses.
- `RFB_MANTER_ZIPS` (padrão `false`): com `false`, apaga `_baixados/<mês processado>/` (~7 GB de zips em
  2026-09); zips de meses fora da janela são sempre apagados.

`rfb pipeline` não aplica retenção (é a ferramenta de reprocessamento e backfill).

## Publicação e S3

- **MotherDuck (P25, ADR-0016):** com `MOTHERDUCK_TOKEN` **e** `MOTHERDUCK_BANCO` definidos, o
  pipeline publica o gold no fim (`rfb publicar --destino motherduck`); no backfill publica só
  `fct_resumo_mensal`. Sem as duas variáveis imprime `MotherDuck não configurado; nada publicado`.
  `--sem-publicar` desliga. A publicação lê o gold **local**: com `RAIZ_DADOS=s3://` ela é pulada com
  aviso.
- **S3/Tigris (ADR-0007):** com `RAIZ_DADOS=s3://…` o pipeline ingere em `RAIZ_DADOS_LOCAL`, roda
  `rfb sincronizar` (envia o raw) antes do dbt, usa o target `s3` (o dbt grava o gold direto no bucket)
  e o relatório lê os marts pelo `httpfs` com um secret temporário (R3-06).

## Requisitos de máquina (P14)

Medido no `dbt build` completo de 2026-09 (73,4 M estabelecimentos; detalhes em
[EXECUCAO_REAL.md](EXECUCAO_REAL.md#memória-e-threads-p14)):

| `DBT_THREADS`/`DUCKDB_THREADS` | `DUCKDB_MEMORY_LIMIT` | `dbt build` | Pico de RSS |
|---|---|---|---|
| 8 / 8 | 24 GB (padrão `dev`) | 318 s | 25,9 GB |
| 4 / 4 | 24 GB | 383 s | 24,9 GB |
| 4 / 4 | 12 GB | 431 s | 18,7 GB |
| 4 / 4 | 8 GB | 460 s | 13,8 GB |

- **O que manda na memória é o `DUCKDB_MEMORY_LIMIT`**, não as threads: o pico fica ~1–2 GB acima do
  limite (buffers de leitura, dbt, Python). O excedente vai para disco em `RAIZ_DADOS/_tmp`.
- **RAM:** com os padrões (`dev`: 8/8, 24 GB) use máquina com **≥ 32 GB**. Regra prática:
  `DUCKDB_MEMORY_LIMIT` ≈ metade da RAM física. Em **16 GB**: `DUCKDB_MEMORY_LIMIT=8GB`,
  `DBT_THREADS=4`, `DUCKDB_THREADS=4` (pico 13,8 GB medido numa máquina maior; feche outros programas).
- **Disco:** ~32 GB por mês processado (zips 6,7 GB, raw 4,9 GB, gold 6,6 GB, `warehouse.duckdb`
  14 GB) mais o spill do DuckDB; com a retenção padrão (2 meses de raw, zips apagados) reserve
  **≥ 50 GB** livres em `RAIZ_DADOS`.
- **Tempo:** ~24 min de download e conversão na 1ª vez + ~6 min de `dbt build` (8/8) num laptop Apple
  Silicon de 15 núcleos.

## Execuções longas: manter a máquina acordada (P20)

Um mês real leva dezenas de minutos (download de ~7 GB + conversão + build). No macOS, com a tampa
fechada ou a máquina ociosa, o sistema entra em sono e só acorda em *DarkWake* a cada ~15 min: o processo
fica congelado e a execução parece travada (observado no `make ci`, que levou ~16 min de parede com
dbt/pytest em segundos). Para execuções longas:

- **macOS:** prefixe com `caffeinate -i` (impede o sono por ociosidade enquanto o comando roda):
  `caffeinate -i make pipeline MES=2026-09`. Com a tampa fechada, mantenha a fonte de energia ligada
  (o `caffeinate -i` não impede o sono por tampa fechada sem energia/monitor externo).
- **Linux:** `systemd-inhibit --what=idle:sleep make atualizar`.
- **Windows:** desative a suspensão no plano de energia durante a execução (`powercfg`).
- Agendadores (cron/launchd) não acordam a máquina dormindo: agende num horário em que ela fica ligada,
  ou use `pmset repeat wakeorpoweron` no macOS.

O cliente WebDAV retoma downloads interrompidos (`Range`) e aborta transferências lentas
(`RFB_VELOCIDADE_MINIMA_BPS`, `RFB_JANELA_LENTIDAO_S`, `RFB_MAX_RETOMADAS`, `RFB_TEMPO_LIMITE_TOTAL_S`);
uma nova execução reaproveita os zips já baixados com o tamanho anunciado.

## Agendamento

`rfb atualizar` é idempotente (no-op sem mês novo) e pode rodar **diariamente**: a RFB publica o mês ao
longo de alguns dias e o comando só processa um mês quando ele está completo. Nos exemplos,
`/caminho/do/projeto` é a raiz do repositório e o `.env` dele define `RAIZ_DADOS` e afins.

### cron (Linux/macOS)

```cron
# todo dia às 03:15; log por dia
15 3 * * * cd /caminho/do/projeto && /usr/bin/env PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin" make atualizar >> dados/logs/atualizar-$(date +\%F).log 2>&1
```

(Crie `dados/logs/` antes. No cron, `%` precisa de escape.)

### launchd (macOS)

`~/Library/LaunchAgents/br.rfb.atualizar.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>br.rfb.atualizar</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/caffeinate</string><string>-i</string>
    <string>/usr/bin/make</string><string>-C</string><string>/caminho/do/projeto</string>
    <string>atualizar</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>/Users/SEU_USUARIO/.local/bin:/opt/homebrew/bin:/usr/bin:/bin</string></dict>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>3</integer><key>Minute</key><integer>15</integer></dict>
  <key>StandardOutPath</key><string>/caminho/do/projeto/dados/logs/atualizar.log</string>
  <key>StandardErrorPath</key><string>/caminho/do/projeto/dados/logs/atualizar.log</string>
</dict>
</plist>
```

Ative com `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/br.rfb.atualizar.plist`. O launchd
roda a tarefa perdida quando a máquina acorda (diferente do cron).

### GitHub Actions

Só faz sentido com o gold num bucket (`RAIZ_DADOS=s3://…`) ou publicado no MotherDuck: o runner é
efêmero. Runners hospedados têm 16 GB de RAM e ~14 GB livres de disco em `/` — **insuficientes** para um
mês real (ver "Requisitos de máquina"); use um runner auto-hospedado (`runs-on: self-hosted`) ou maior.

```yaml
name: atualizar
on:
  schedule: [{ cron: "15 6 * * *" }]   # 03:15 em Brasília
  workflow_dispatch:
jobs:
  atualizar:
    runs-on: self-hosted
    timeout-minutes: 240
    env:
      RAIZ_DADOS: s3://meu-bucket/rfb
      RAIZ_DADOS_LOCAL: ${{ runner.temp }}/dados
      AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
      AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
      AWS_ENDPOINT_URL_S3: ${{ secrets.AWS_ENDPOINT_URL_S3 }}
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - run: make setup
      - run: make atualizar
```

Num runner efêmero o `_estado/ultima_execucao.json` local some entre execuções: preserve-o (cache do
Actions ou cópia no bucket) ou o comando reprocessará o mês mais recente a cada dia.

## Peculiaridades dos dados reais

- **Bytes de controle C1 (0x80–0x9F)** aparecem em raros campos do extrato (2026-09: 5 bytes em
  `Estabelecimentos0`, `4` e `7`). O leitor latin-1 do DuckDB os recusa ("File is not
  latin-1 encoded"); a conversão então transcodifica o CSV latin-1 → UTF-8 em Python (que mapeia todo
  byte) e relê, com um aviso. Nenhuma linha é perdida.
- `Estabelecimentos0.zip`/`Empresas0.zip` são bem maiores que as demais partes (2,2 GB e 0,56 GB
  compactados em 2026-09; o CSV de `Estabelecimentos0` tem 7,1 GB).
