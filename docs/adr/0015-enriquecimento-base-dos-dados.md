# ADR-0015 — Enriquecimento com novas bases da Base dos Dados (Fase 1)

**Contexto.** Pedido do usuário (2026-10-01): avaliar outras bases da Base dos Dados (BD) para enriquecer os
dados das empresas. O levantamento (artefato Traycer "Propostas: novas bases da Base dos Dados") mostrou
que (a) o EL baixa a BD por um caminho legado (`one-click-download/…`) congelado em dez/2023 — população e
PIB param em 2021 —, enquanto a API atual da BD (`basedosdados.org/api/tables/downloadTable`) serve as
mesmas tabelas atualizadas (população até 2025, PIB até 2023), grátis até 100 MB; e (b) há tabelas pequenas e
gratuitas que dão perfil de mercado e noção de área de mercado. O usuário aprovou a **Fase 1** e adiou a
Fase 2 (tabelas que só saem de graça via BigQuery).

**Decisão.**
- **Download da BD pela API `downloadTable`** (parâmetros em base64: dataset, tabela, `true`, `free`), para
  todas as tabelas BD do projeto; o caminho legado sai. Host permitido: `basedosdados.org`.
- **Novas tabelas no raw** (all-VARCHAR, mesmo contrato do ADR-0002):
  - `br_ibge_censo_2022.municipio` — população do Censo 2022, domicílios, área (km²), taxa de alfabetização,
    idade mediana, razão de sexo, índice de envelhecimento;
  - `br_geobr_mapas.regiao_metropolitana_2017` — região metropolitana de cada município (a geometria não é
    usada e pode ser descartada no staging);
  - `br_bd_vizinhanca.municipio` — pares de municípios vizinhos (usar o ano mais recente).
- **Modelo**: `dim_municipio` ganha os atributos do Censo 2022 e a região metropolitana (`NÃO PERTENCE` quando
  não há); uma tabela de vizinhança conformada; um mart novo de **concorrência na área de mercado**
  (município, vizinhos e região metropolitana) com indicadores por mil domicílios e por km²; o estudo de caso
  ganha a visão de área de mercado.
- Tudo é **adição** (ADR-0006), marcado `meta.escopo: adicao`; nada muda nos modelos do original.
- **Marcação própria do incremento (pedido do usuário):** além do escopo, todo artefato deste incremento
  leva um segundo marcador, para ser identificado como "enriquecimento com bases externas":
  - nós dbt (fontes, modelos, seeds, testes, unit tests, analyses): `meta.incremento: enriquecimento_bd` e tag
    `incremento_enriquecimento_bd` — `dbt ls --select tag:incremento_enriquecimento_bd` lista tudo; a guarda
    de escopo passa a exigir coerência entre `meta.incremento` e a tag;
  - Python: tabelas novas em `esquemas.TABELAS_BD` com o atributo `incremento="enriquecimento_bd"`;
    funções/testes novos com o comentário `# incremento: enriquecimento_bd`;
  - documentação: coluna/selo **"Incremento: enriquecimento BD"** em `docs/ESCOPO.md`, nas tarefas T38–T41 e
    no `ARCHITECTURE.md`.

**Fora (Fase 2, adiada pelo usuário para depois da entrega da v1 — AD-029).** Pirâmide etária municipal, RAIS, CAGED, exportadoras/importadoras,
diretório de CEP — exigem BigQuery (conta Google Cloud).

**Consequências.** Dados de população/PIB atualizados mudam números reais (densidade por 10 mil hab. passa a
usar 2025); fixtures ganham as três tabelas novas com respostas conhecidas; `rfb ingerir` baixa 3 tabelas a
mais (~5 MB). Se a API da BD mudar, o download quebra — mitigado pelo `--origem-local` e pelo manifesto.
