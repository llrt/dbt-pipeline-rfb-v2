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
| `rfb pipeline --sem-ingestao --mes AAAA-MM` | Usa o raw que já está em `RAIZ_DADOS` (útil para refazer só o dbt). Se faltar o raw do IBGE (um `RAIZ_DADOS` da v1.3), publica-o vazio antes do dbt; ver "Depois de atualizar da v1.3". |
| `make regras` (`rfb regras`) | Executa os checks das regras de negócio ([REGRAS_NEGOCIO.md](REGRAS_NEGOCIO.md), ADR-0020) no warehouse de `RAIZ_DADOS`, **só lendo** (a única escrita é o raw do IBGE vazio, quando ele falta: a RN-30 lê a fonte do CEMPRE), e regrava `docs/RELATORIO_REGRAS_NEGOCIO.md` (`SAIDA=ARQ` muda o destino). Sai com 0 mesmo com violações. Não faz parte do `pipeline`: rode depois de um mês novo concluído e revise a seção "Interpretação de AAAA-MM": no mesmo mês ela é preservada; num mês novo, o texto antigo vai para "Interpretação anterior (AAAA-MM)" e o comando avisa (`aviso:` na saída de erro) até que ela seja reescrita e a seção anterior apagada. Recusa rodar com o gold misto, como `rfb relatorio`. No dado real de 2026-09 levou 88 s com as 29 regras (`DUCKDB_MEMORY_LIMIT=16GB`, `DUCKDB_THREADS=4`). |

Opções comuns a `pipeline` e `atualizar`: `--origem-local DIR` (fixtures, sem rede),
`--permitir-incompleto`, `--forcar` (reconverte), `--renovar-ibge` e `--sem-ibge` (ver abaixo; excludentes), `--target` (padrão: o do profile; `s3` com
`RAIZ_DADOS=s3://`), `--saida-relatorio ARQ`, `--sem-relatorio`, `--sem-publicar`. O `make ci` usa
exatamente esses comandos sobre as fixtures (pipeline 2026-08 → atualizar 2026-09 → atualizar no-op →
backfill de 2026-08).

Cada etapa imprime `== etapa <nome>: <segundos>s` e o fim do mês imprime o resumo
`pipeline <mês> [corrente|backfill] concluído em …`.

## Fontes do IBGE (incremento `enriquecimento_ibge`)

`rfb ingerir` (e, por ele, `pipeline`/`atualizar`) também baixa, direto do IBGE, o CEMPRE por município ×
classe CNAE (API SIDRA, tabela 9528), a renda per capita do Censo 2022 (SIDRA 10295) e a REGIC 2018
(planilhas do geoftp), para `raw/ibge/<tabela>/<tabela>.parquet` (detalhes em `src/rfb_pipeline/ibge.py`).

- **Não rebaixa todo mês.** São fontes anuais ou estáticas: uma tabela já no raw com o mesmo período
  (SIDRA) ou o mesmo arquivo (REGIC) é pulada (`ibge.<tabela>: pulada (...)`), conforme
  `_manifestos/ibge/manifesto.json` (origem, período, bytes, sha256 quando há arquivo, requisições, linhas). Só o
  CEMPRE consulta a SIDRA para saber se saiu um ano novo (uma requisição leve), e no máximo **uma vez a
  cada 30 dias**: a data da última consulta fica em `sonda_cempre_em` no manifesto IBGE. O manifesto do mês
  (`_manifestos/AAAA-MM.json`) copia essas entradas em `ibge`.
- **Falha do IBGE não derruba o mês.** Se a SIDRA ou o geoftp falharem (depois das retentativas, que
  incluem o 429 de limite de taxa), a tabela que falhou fica com o raw anterior, ou vazia (só o esquema) se
  não havia, a ingestão avisa na saída de erro (`aviso: ibge.<tabela>: não atualizada (...)`) e segue: a RFB,
  a BD, o manifesto do mês e o dbt correm como sempre. A falha fica em `falhas` no manifesto IBGE e sai dele
  quando a tabela é atualizada. Tente de novo com `rfb ingerir --renovar-ibge` (ou espere o próximo mês). Só
  é erro se o raw vazio não puder ser gravado. Planilha da REGIC ilegível (por exemplo, uma página de erro
  servida com HTTP 200, ou um zip sem a planilha esperada) conta como falha: o arquivo baixado sai de
  `_baixados/ibge/regic/`, para a próxima execução baixar de novo.
- **Renovar à força:** `rfb ingerir --renovar-ibge` (também em `pipeline`/`atualizar`). É uma opção
  separada de `--forcar` porque o CEMPRE nacional leva de 1 a 2 horas (~340 requisições de ≤ 50.000
  valores), e `--forcar` serve para reconverter um mês RFB sem rede. Em `rfb atualizar` **sem mês novo**,
  `--renovar-ibge` renova só o IBGE e reconstrói o gold do mês corrente (sem tocar no raw da RFB e da BD); se
  nenhuma tabela do IBGE for renovada, nada é reconstruído.
- **Desligar o IBGE: `--sem-ibge`** (em `ingerir`, `pipeline` e `atualizar`). Não consulta a SIDRA nem o
  geoftp nesta execução; o raw IBGE existente fica como está e o ausente é publicado vazio (colunas do IBGE
  NULL). Serve para rede que só libera a RFB e a Base dos Dados e para adiar o primeiro download.
- **Primeiro download longo.** A primeira ingestão em rede depois de instalar a v1.4 baixa o CEMPRE nacional
  inteiro: de 1 a 2 horas a mais, dentro do `rfb atualizar` agendado do mês. Para não pegar o agendamento de
  surpresa, rode antes, fora da janela, `rfb atualizar --renovar-ibge`: sem mês novo, ele baixa só o IBGE
  (não os zips da RFB) e reconstrói o gold do mês corrente com as colunas novas. Ou adie: agende o mensal
  com `--sem-ibge` até ter a janela.
- **Ano do CEMPRE:** `RFB_CEMPRE_PERIODO=AAAA` fixa o ano (padrão: o mais recente publicado).
- **Retomada:** o CEMPRE grava cada fatia em `_baixados/ibge/sidra/cempre_municipio_cnae/<ano>/` assim
  que ela chega; uma execução interrompida continua de onde parou. As fatias somem depois de publicado o
  raw.
- **`--origem-local DIR`** lê `DIR/ibge/` em vez da rede:
  `cempre_categorias_cnae.json`, `cempre_municipio_cnae.json` e `renda_censo_2022_municipio.json`
  (respostas da SIDRA: lista JSON de objetos `NC`, `MC`, `V`, `D1C`…; as categorias com nomes, `/f/a`;
  todas as linhas num arquivo só), `REGIC2018_Municipios_Hierarquia_e_regiao.xlsx` e
  `REGIC2018_Municipios_Ligacoes_e_atracao_xlsx.zip`, como publicados no geoftp. Uma tabela só é
  reconvertida se o sha256 do arquivo mudar. `scripts/gerar_fixtures.py` gera esse layout.
- **Espelho offline sem `ibge/` (compatibilidade com a v1.3).** Um `--origem-local` montado antes do
  incremento não tem a pasta `ibge/`. A ingestão **não falha**: para cada arquivo IBGE ausente, avisa
  (`ibge.<tabela>: AVISO ... ausente; publicada vazia`) e publica `raw/ibge/<tabela>/<tabela>.parquet` só com
  o esquema (as colunas da fonte dbt, sem linhas). Se a tabela já existir no raw (de uma ingestão anterior),
  ela é mantida (`mantido o raw existente`). Nada entra no manifesto IBGE, então a próxima execução com os
  arquivos converte tudo. O `dbt build` segue igual: as colunas novas de `dim_municipio` saem NULL, o polo de
  compras sai NULL, `bridge_municipio_destino_compras` sai vazia, `mart_emprego_setor_municipio` tem só os
  pares com ativo na RFB e a RN-30 avalia esses pares sem violação. Nenhum teste dbt depende de haver dado do
  IBGE: os de linhas e de soma do incremento passam vazios ou são `warn`. Detalhe do dbt-duckdb: o Parquet de
  um modelo `external` vazio (a ponte, aqui) traz uma linha toda NULL, que a view do warehouse filtra; quem lê
  o Parquet direto (Power BI) deve ignorar essa linha. O teste
  `test_pipeline_offline_sem_ibge_sai_0_e_constroi_o_gold` roda o pipeline nesse cenário.
- **Depois de atualizar da v1.3.** O `RAIZ_DADOS` de quem já rodava a v1.3 não tem `raw/ibge/`, e as fontes
  dbt do IBGE leem `raw/ibge/<tabela>/*.parquet`. Por isso toda chamada ao dbt (`pipeline`, inclusive
  `--sem-ingestao`, e `atualizar`) e `rfb regras`/`rfb relatorio` publicam antes o raw IBGE vazio que faltar,
  sem rede e sem tocar num raw existente (`ibge: AVISO raw ausente de ...`). `rfb atualizar` sem mês novo também
  o garante. O gold continua o da v1.3 até o próximo build, que traz as colunas novas NULL; para tê-las
  preenchidas sem esperar um mês novo, `rfb atualizar --renovar-ibge` (ver "Primeiro download longo"). Com `RAIZ_DADOS=s3://` a garantia fica com a ingestão:
  o raw do bucket pode ter o IBGE que a cópia local não tem. O teste
  `test_raiz_dados_da_v1_3_sem_raw_ibge_roda_regras_atualizar_e_pipeline_sem_ingestao` cobre o cenário.
- **Uso das bases novas:** [cenários de uso](CENARIOS_DE_USO.md), com as analyses `cenario_*` e o caso.

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
- **Gold misto (R4-03).** Os marts `external` são regravados um a um durante o `dbt build` do mês
  corrente, e um teste `error` só pula os **filhos** do modelo testado. Se o build falhar no meio, parte
  do gold fica com o mês novo e parte com o anterior (por exemplo, `bh_empresas` novo e `agg_empresas`
  antigo), e a partição nova do resumo pode já estar gravada. Para isso não passar calado, o pipeline
  grava `_estado/em_andamento.json` (mês e hora) **antes** do `dbt build` e o apaga **só** quando ele
  termina bem. Enquanto o marcador existir, `rfb relatorio`, `rfb regras` e `rfb publicar` (e a publicação no fim de um
  backfill) recusam rodar com uma mensagem que diz o mês. **Como sair:** corrija a causa e rode
  `rfb pipeline --mes <mês do marcador>` de novo até concluir; o build completo regrava todo o gold e
  apaga o marcador. Um BI que leia o gold nessa janela pode misturar dois meses: agende a atualização
  do BI depois do pipeline, não durante.
- Um `flock` em `_estado/pipeline.lock` impede dois `pipeline`/`atualizar` simultâneos na mesma
  `RAIZ_DADOS` (a ingestão tem a sua trava, `_estado/rfb.lock`).

## Retenção

Após um `rfb atualizar` bem-sucedido:

- `RFB_MESES_RETIDOS` (padrão **2**: o mês atual e o anterior, para comparação e rollback): mantém em
  `raw/rfb/<entidade>/` só as partições dos N meses mais recentes; as demais são apagadas. A série
  `fct_resumo_mensal` não depende do raw e preserva todos os meses.
- `RFB_MANTER_ZIPS` (padrão `false`): com `false`, apaga `_baixados/<mês processado>/` (~7 GB de zips em
  2026-09); zips de meses fora da janela são sempre apagados. Só diretórios de mês (`AAAA-MM`) entram
  na retenção: `_baixados/ibge/` (fatias do CEMPRE guardadas para retomar) nunca é apagado por ela.

`rfb pipeline` não aplica retenção (é a ferramenta de reprocessamento e backfill).

## Publicação e S3

- **MotherDuck (P25, ADR-0016):** com `MOTHERDUCK_TOKEN` **e** `MOTHERDUCK_BANCO` definidos, o
  pipeline publica o gold no fim (`rfb publicar --destino motherduck`); no backfill publica só
  `fct_resumo_mensal`. Todas as tabelas são recriadas numa **única transação** (`BEGIN … COMMIT` na
  conexão DuckDB com o banco anexado): uma falha no meio desfaz tudo e o MotherDuck fica com a
  publicação anterior inteira (R4-03). Testado com destino `.duckdb` local (`test_publicacao.py`); o
  MotherDuck aceita transações com DDL, mas isso só é confirmado na 1ª publicação real (P25). Sem as duas variáveis imprime `MotherDuck não configurado; nada publicado`.
  `--sem-publicar` desliga. A publicação lê o gold **local**: com `RAIZ_DADOS=s3://` ela é pulada com
  aviso.
- **S3/Tigris (ADR-0007):** com `RAIZ_DADOS=s3://…` o pipeline ingere em `RAIZ_DADOS_LOCAL`, roda
  `rfb sincronizar` (envia o raw) antes do dbt, usa o target `s3` (o dbt grava o gold direto no bucket)
  e o relatório lê os marts pelo `httpfs` com um secret temporário (R3-06).
- **Estado e retenção no modo s3 ficam no disco local (R4-06, comportamento aceito).** O estado
  (`_estado/ultima_execucao.json`, travas e o marcador `em_andamento.json`) é gravado em
  `RAIZ_DADOS_LOCAL/_estado/`, não no bucket. Num runner efêmero ele some entre execuções: preserve-o
  (ver "GitHub Actions") ou o `rfb atualizar` reprocessa o mês mais recente a cada dia. A retenção
  (`RFB_MESES_RETIDOS`, `RFB_MANTER_ZIPS`) apaga só o raw e os zips **locais**; as partições
  `raw/rfb/<entidade>/mes_referencia=*` que o `rfb sincronizar` enviou ao bucket ficam lá e o bucket
  cresce um mês por atualização. Como o staging lê `mes_referencia=*` mas filtra o mês do build, isso
  custa só armazenamento; apague as partições antigas do bucket à mão (ou por regra de ciclo de vida
  do bucket) quando quiser. Lembre que o raw tem e-mail e telefone como publicados (ADR-0008): o bucket
  precisa ser privado.

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
