# RIBG — Revisão independente do enriquecimento IBGE (lotes IBG1 e IBG2, futura v1.4.0)

Revisor: agente RIBG (Traycer, Claude Opus), 2026-10-14. Não sou autor de nenhum dos 22 commits.

- **Alvo:** branch `feat/enriquecimento-ibge`, `git diff d5fdce9..ad40df5`. O IBG1 vai até `d222fb0`, e o IBG2 vem
  depois.
- **O que não toquei:** não alterei código, YAML, docs nem testes.
- **Mutações:** aplicadas por script e revertidas com `git checkout -- <arquivo>`. `git status --porcelain` ficou
  vazio no fim.
- **Dado real:** nada foi gravado no diretório de dados reais. Lá só li o gold Parquet e o `raw/bd/pib`, com DuckDB em
  memória.
- **Raw IBGE:** o raw real do IBG1 foi **copiado** para o meu scratch.
- **Downloads novos**, cada um numa pasta nova do scratch:
  - o zip de ligações da REGIC 2018, para ler a aba "Descrição das variáveis" e o "Leia me";
  - a apresentação do CEMPRE 2024;
  - o texto do Decreto 8.777.
- **Simulação de quem atualiza da v1.3:** feita sobre cópias de `.tmp/ci/dados` no scratch.

## Veredito

**NÃO APROVÁVEL COMO MINOR ATÉ CORRIGIR O RIBG-01** (bloqueante). O resto é aprovável com ressalvas: um achado alto,
um médio e oito baixos.

O que está bem:

- **Pedido atendido.**
  - As quatro fontes chegam ao gold de graça e direto da origem:
    - CEMPRE (SIDRA 9528);
    - renda do Censo 2022 (SIDRA 10295);
    - REGIC 2018 (geoftp);
    - VA por atividade, que já estava no raw da BD.
  - Há cinco analyses de cenário, a analysis do caso e `docs/CENARIOS_DE_USO.md`.
- **Dados certos.**
  - Recontei por SQL próprio, no raw IBGE real e no gold real, **todos** os números ilustrativos que conferi nas
    docs, incluindo a RN-30 (2.107 de 1.073.321). Batem todos, menos uma afirmação qualitativa (RIBG-06).
  - Os símbolos SIDRA têm teste e o sigilo nunca é imputado.
  - O Total do CEMPRE fica num modelo à parte, guardado por teste.
  - A classe de 5 dígitos casa com os 5 primeiros dígitos da subclasse (`dim_cnae.codigo_classe` vem com `lpad`).
  - `ano_va` é independente de `ano_pib`.
  - O VA está em R$, e não em R$ mil.
- **Docs fiéis à fonte.**
  - O texto sobre a REGIC não promete mais do que o dado diz.
  - A exclusão do MEI no CEMPRE está confirmada na fonte primária.
- **Gold aditivo.**
  - Nenhuma coluna, grão, métrica, saved query, alvo `make`, variável de ambiente ou opção de CLI foi removido ou
    alterado.
  - Todo `-` do diff de código é docstring, texto de ajuda ou a vírgula da última coluna.
  - O manifesto do mês só ganhou a chave `ibge`, com padrão `()` na leitura.
- **Testes fortes.** De 13 mutações próprias, 11 morreram.

O que pesa:

1. **RIBG-01, bloqueante.** Uma instalação da v1.3 que atualiza o código para a v1.4 **quebra** antes de uma ingestão
   em rede de um mês novo.
   - `rfb regras` sai com 1 e não gera o relatório.
   - `rfb pipeline --sem-ingestao` falha no `dbt build`, com 10 erros, e deixa o gold marcado como misto.
   - Motivo: `raw/ibge/` não existe e as fontes dbt leem `read_parquet(.../raw/ibge/...)`.
   - O `dados/` real do usuário está nesse estado hoje: só tem `raw/bd` e `raw/rfb`.
   - `rfb atualizar` sem mês novo é no-op e não cria o `raw/ibge`.
2. **RIBG-02, alta.** Em rede, `rfb ingerir`/`pipeline`/`atualizar` passam a depender da SIDRA e do geoftp em todo
   mês novo, sem opção de desligar.
   - Uma falha do IBGE derruba o mês inteiro depois de a RFB e a BD estarem convertidas.
   - A primeira execução depois do upgrade embute de 1 a 2 horas do CEMPRE nacional no pipeline mensal.
3. **RIBG-03, média.** Quando o polo de compras do município do caso fica em outra UF, o relatório afirma que o
   município "não tem polo de compras na REGIC 2018".
   - Isso vale para 314 dos 5.503 municípios com questionário.
   - Exemplo: Iúna/ES, cujo polo é Manhuaçu/MG, com 56,7 %.

Execução:

- **`caffeinate -i make ci`:** verde duas vezes, antes e depois das mutações.
  - Testes: 334 unitários e 235 de integração.
  - `dbt build`: PASS=451, WARN=6, ERROR=0 nos dois meses. Backfill: PASS=259, WARN=2.
  - `rfb regras`: "30 regras, 7 violadas", com saída 0. Lint limpo.
  - O 6º WARN, novo, é `destino_compras_soma_100`, com 5 linhas nas fixtures (RIBG-11).
- **`make dicionario`:** verde e sem diff (`git status --porcelain` vazio).
- **`make semantica`:** verde com `RAIZ_DADOS=.tmp/ci/dados` (ERRORS: 0, WARNINGS: 0 em todas as validações). Sem o `RAIZ_DADOS`, o padrão `./dados` não existe no worktree e as métricas falham por falta do `warehouse.duckdb`, o que é ambiente e não achado.
- **`uvx pre-commit run --all-files`:** verde.

## Achados

Severidade: **bloqueante** (impede o merge), **alta** (corrigir antes do merge), **média** (corrigir no lote de
correções), **baixa** (pode ir para pendências).

### RIBG-01 — sem `raw/ibge/`, o dbt e o `rfb regras` quebram numa instalação da v1.3 (bloqueante, compatibilidade)

- **Onde:**
  - `transform/models/staging/ibge/_ibge__sources.yml:26` (e linhas 116, 173, 240, 365, 625):
    `external_location: read_parquet('{{ env_var('RAIZ_DADOS') }}/raw/ibge/<tabela>/*.parquet')`. Sem arquivo, o
    DuckDB levanta `IO Error: No files found`.
  - `transform/analyses/regras_negocio/rn_30_cempre_coerente_com_rfb.sql:11`: lê a fonte, e o
    `docs/REGRAS_NEGOCIO.md:584` justifica isso como "para rodar sobre um warehouse que ainda não tem os modelos do
    IBGE". O warehouse pode não ter os modelos, mas o **raw** precisa existir.
  - O raw vazio só é publicado dentro de `ingerir_ibge` (`src/rfb_pipeline/ibge.py:491-527`), e só no modo
    `--origem-local`.
  - `rfb atualizar` sem mês novo retorna antes da ingestão (`src/rfb_pipeline/orquestracao.py:453-456`).
- **Evidência:** simulação no scratch. Copiei `.tmp/ci/dados` (gold e warehouse completos) e apaguei `raw/ibge`,
  que é o estado de um `RAIZ_DADOS` da v1.3.
  - `rfb pipeline --sem-ingestao --mes 2026-09 --target ci --sem-publicar --sem-relatorio` sai com **1**.
    - "Completed with 10 errors": `stg_ibge__cempre_municipio_total`, `stg_ibge__renda_municipio` e os 8 testes de
      fonte do IBGE.
    - O erro é `IO Error: No files found that match the pattern ".../raw/ibge/cempre_municipio_cnae/*.parquet"`.
    - Fica o marcador `_estado/em_andamento.json`, e daí em diante o `rfb regras` recusa: "o gold pode estar misto".
  - `rfb regras --target ci` numa cópia limpa sai com **1** e não grava o relatório: "analysis
    rn_30_cempre_coerente_com_rfb falhou: IO Error: No files found …".
  - `ls dados/raw` do usuário: `bd`, `rfb`. Logo, `make regras` e `rfb pipeline --sem-ingestao`
    (`docs/OPERACAO.md:14`, "útil para refazer só o dbt") quebram no ambiente real assim que a v1.4 for instalada. O
    mesmo vale para qualquer `dbt build` direto.
- **Por que é bloqueante:** é a mesma promessa da condição 1b do IBG2 ("espelho da v1.3 continua funcionando"), só
  que no caminho sem `--origem-local`. O teste `test_pipeline_offline_sem_ibge_sai_0_e_constroi_o_gold` só cobre o
  caso em que a ingestão roda.
- **Correção sugerida:**
  1. Garantir o raw IBGE vazio (só o esquema, `_publicar_vazia`) **antes de toda chamada ao dbt** e no início de
     `rfb regras`, não só na ingestão offline. Por exemplo, um `garantir_raw_ibge(configuracao)` chamado por
     `executar_pipeline` (inclusive com `--sem-ingestao`), por `rfb regras` e por `rfb relatorio`. Ele não pode
     sobrescrever um raw existente.
  2. Teste de integração: `RAIZ_DADOS` com o gold pronto e **sem** `raw/ibge`. Tanto o `pipeline --sem-ingestao`
     quanto o `rfb regras` têm de sair com 0.
  3. Em `docs/OPERACAO.md`, documentar como obter o IBGE depois do upgrade sem esperar um mês novo, por exemplo
     `rfb ingerir --mes <último>`. Ver RIBG-04: `rfb atualizar --renovar-ibge` não serve para isso.

### RIBG-02 — dependência mensal e obrigatória da SIDRA e do geoftp, sem desligamento (alta, compatibilidade e robustez)

- **Onde:**
  - `src/rfb_pipeline/cli.py:334`: `ingerir_ibge(...)` roda depois da RFB e da BD e antes de gravar o manifesto
    completo do mês (`cli.py:346`), sem tratamento de erro.
  - `src/rfb_pipeline/ibge.py:632-641`: em rede, a consulta das categorias do CEMPRE vai à SIDRA **em toda
    ingestão**, mesmo com o CEMPRE do mesmo ano no raw. É a "consulta leve por mês" de `docs/OPERACAO.md`.
  - Não há opção nem variável que pule o IBGE.
- **Efeito:**
  - **Instabilidade da SIDRA ou do geoftp:** um `SidraErro` ou `ErroDownload` depois das retentativas derruba
    `rfb atualizar`/`pipeline` no mês em que a RFB publicou. A RFB e a BD já estão convertidas, mas o manifesto fica
    com `concluido_em` nulo e o dbt não roda.
    - Na v1.3, o mesmo comando não falhava por causa do IBGE.
    - É comportamento novo de um comando existente, contra a regra "nenhum comportamento existente alterado" da
      minor.
  - **Primeira execução em rede depois do upgrade:** o CEMPRE nacional (337 requisições, 2,1 GB de JSON e 15 M de
    linhas no manifesto do IBG1) entra **dentro** do `rfb atualizar` agendado, com 1 a 2 horas a mais.
  - **Rede restrita:** quem roda numa rede que só libera a RFB e a Base dos Dados passa a falhar.
- **Correção sugerida:**
  - Tratar falha do IBGE em rede como **aviso**:
    - manter o raw anterior se existir, ou publicar o vazio (o mesmo mecanismo do RIBG-01);
    - seguir com o mês;
    - registrar no manifesto que a tabela não foi atualizada.

    Só `--renovar-ibge` explícito deveria falhar duro.
  - Pular a consulta de categorias quando o CEMPRE está no raw e não se pediu renovação, ou checar ano novo no
    máximo uma vez por mês.
  - Oferecer `--sem-ibge` (ou `RFB_IBGE=0`) para quem não quer as fontes novas.
  - Registrar a dependência e o tempo da primeira execução em "Consequências" do ADR-0022 (linha 87) e em
    `docs/OPERACAO.md`.

### RIBG-03 — polo de compras em outra UF some do caso e o relatório diz que não há polo (média, corretude)

- **Onde:**
  - `transform/analyses/estudo_caso_enriquecimento_ibge.sql:44`: o CTE `municipios` filtra
    `mun.sigla_uf = caso_uf`.
  - Linha 81: a linha "polo de compras" junta `municipios` com `caso.id_municipio_polo_compras`. Um polo de outra UF
    não está em `municipios`, e a linha some.
  - `src/rfb_pipeline/relatorio.py:423`: sem a linha do polo, o relatório escreve "_<local> não tem polo de compras
    na REGIC 2018._", embora `pct_compras_no_polo` venha preenchido na linha do caso.
- **Evidência (REGIC real):**
  - Das 5.503 origens com polo, **314** (5,7 %) têm o polo noutra UF: MG 58, TO 27, GO 27, MA 24…
  - No ES, por exemplo:
    - Iúna → Manhuaçu/MG, 56,7 %;
    - Ibatiba → Manhuaçu/MG, 56,7 %;
    - São José do Calçado → Bom Jesus do Itabapoana/RJ, 73,3 %.
  - As vars `caso_*` são documentadas como parâmetros (`docs/CENARIOS_DE_USO.md:11-18`). Com
    `caso_municipio: IÚNA`, a seção do IBGE afirmaria uma falsidade.
- **Correção sugerida:**
  - Ler a linha do polo de `dim_municipio` sem o filtro de UF, numa CTE própria para o polo.
  - No relatório, só dizer "não tem polo" quando `polo_compras` (ou `id_municipio_polo_compras`) for NULL.
  - Teste: injetar o polo noutra UF nas fixtures, ou um unit test da analysis.

### RIBG-04 — `rfb atualizar --renovar-ibge` é ignorado quando não há mês novo (baixa, operação)

- **Onde:**
  - `docs/OPERACAO.md:37`: "`rfb ingerir --renovar-ibge` (também em `pipeline`/`atualizar`)".
  - `src/rfb_pipeline/orquestracao.py:453-456`: sem mês novo, `atualizar` imprime "nenhum mês novo" e retorna antes
    de ingerir.
- **Efeito:** quem roda `rfb atualizar --renovar-ibge` para buscar o CEMPRE do ano novo não recebe nada nem aviso.
- **Correção:**
  - Avisar ("`--renovar-ibge` ignorado: nenhum mês novo; use `rfb ingerir --renovar-ibge`"),
  - ou fazer `atualizar` honrar a opção.
  - Ajustar a doc.

### RIBG-05 — lacunas de teste: 2 mutações sobreviventes e dois cenários sem teste (baixa, testes)

- **P4:** tirar o 429 da lista de retentativa da SIDRA (`ibge.py:242`) não derruba nenhum teste. A SIDRA limita
  taxa e o CEMPRE faz 337 requisições, então a retentativa no 429 é a que mais importa.
  - Sugestão: um unit test com 429, depois 200, como o de 5xx.
- **D4:** trocar a renda da UF ponderada por moradores (`estudo_caso_enriquecimento_ibge.sql:91`) por `avg` simples
  passa no CI inteiro.
  - O teste confere só a linha do polo e o número de linhas. A linha "UF" (renda, unidades e pessoal) não é
    conferida em lugar nenhum.
  - Sugestão: conferir também a linha da UF em `ANALISES`.
- **Cenários sem teste:**
  - polo em outra UF (RIBG-03);
  - `RAIZ_DADOS` sem `raw/ibge` fora do modo offline (RIBG-01).

### RIBG-06 — a doc afirma que o IBGE marca `...` a mediana de alguns municípios, mas o dado real não tem nenhum (baixa, documentação)

- **Onde:**
  - `docs/CAMADA_SEMANTICA.md:404`: "O IBGE marca `...` (não disponível) a mediana de alguns municípios, que fica
    NULL".
  - `transform/models/marts/core/_core__models.yml:263`, propagado para `docs/DICIONARIO_DADOS.md`
    (`renda_per_capita_mediana_2022`): "o IBGE marca `...` em alguns municípios".
- **Evidência:** na 10295 real (16.710 valores), os 5.570 valores de cada variável são numéricos. Não há nenhum
  `...`, `..`, `X` ou `-`, e nenhum nulo.
  - O `...` vem da fixture sintética: `scripts/gerar_fixtures.py:1112`, `"2200202": ("16800", "610.15", "...")`.
- **Correção:** reescrever como possibilidade ("se o IBGE publicar um símbolo, o valor fica NULL") ou retirar a
  frase. O tratamento do símbolo continua certo e testado.

### RIBG-07 — o ADR-0022 cita a redação revogada do art. 4º do Decreto 8.777 (baixa, documentação)

- **Onde:** `docs/adr/0022-enriquecimento-fontes-gratuitas-ibge.md:76-79`.
- **Evidência (texto do Planalto):** "bem como qualquer informação de transparência ativa, são de livre utilização
  pelo Governo federal e pela sociedade" é a redação **original**. O Decreto nº 9.903/2019 deu nova redação: "Os
  dados disponibilizados pelo Poder Executivo federal e as informações de transparência ativa são de livre utilização
  pelos Poderes Públicos e pela sociedade".
  - Incluiu também o § 1º: "Fica autorizada a utilização gratuita das bases de dados … cujo detentor de direitos
    autorais patrimoniais seja a União".
  - A conclusão do ADR, de livre uso com crédito da fonte, não muda. A citação literal, sim.
  - A definição do art. 2º, III, está correta.
- **Correção:** citar a redação vigente (Decreto 9.903/2019) e notar que o IBGE é fundação, fora do § 1º, que fala
  da União, e que o caput basta.

### RIBG-08 — o guia do Power BI não conhece os modelos novos nem a linha toda NULL (baixa, documentação)

- **Onde:**
  - `docs/POWER_BI.md:177-178` lista as relações opcionais do incremento BD (`bridge_municipio_vizinho`), mas não
    tem nada de `bridge_municipio_destino_compras` nem de `mart_emprego_setor_municipio`. O diff não toca o arquivo.
  - A ressalva da linha toda NULL no Parquet de modelo `external` vazio está só em `docs/OPERACAO.md:58-60`.
- **Correção:**
  - Acrescentar as relações:
    - `dim_municipio[sk_municipio]` → `bridge_municipio_destino_compras[sk_municipio_origem]`;
    - uma cópia para o destino;
    - `mart_emprego_setor_municipio[sk_municipio]`.
  - Repetir a ressalva da linha NULL ali: é quem lê o Parquet direto que a encontra. Ver também "Linha toda NULL",
    abaixo.

### RIBG-09 — classes do CEMPRE sem par na CNAE da RFB (baixa, corretude)

- **Evidência (real):** 2 das 673 classes do CEMPRE não estão em `dim_cnae.codigo_classe`:
  - 70.10-7, "Sedes de empresas e unidades administrativas locais", com 92 unidades no Brasil;
  - 47.90-3, com 0 unidades.
- **Efeito:**
  - Em `mart_emprego_setor_municipio`, esses pares saem com `descricao_classe` NULL (`left join classes`, linha 95).
  - Na RN-30, os **6** pares de 70.10-7 com 3 ou mais unidades são violações **estruturais**: nunca haverá ativo
    RFB nessa classe.
  - São 6 de 2.107, o que não muda a leitura.
- **Correção:**
  - Usar o nome da classe do próprio CEMPRE (`nome_classe_cnae` já está no staging) como alternativa em
    `descricao_classe`.
  - Na RN-30, tirar do universo as classes sem par na `dim_cnae`, ou documentar.

### RIBG-10 — a saved query promete o % no polo, mas não o traz (baixa, semântica)

- **Onde:** `transform/models/marts/_marts__saved_queries.yml:68-72`. A descrição de `polo_compras_concorrencia_caso`
  diz "o polo de compras … e o % dos deslocamentos que vão a ele", mas o `group_by` não tem
  `Dimension('municipio__pct_compras_no_polo')`, que existe no modelo semântico.
- **Correção:** acrescentar a dimensão ou ajustar a descrição.

### RIBG-11 — `destino_compras_soma_100` vira WARN permanente no CI (baixa, testes)

- **Evidência:**
  - Em todo `make ci`, `WARN 5 destino_compras_soma_100`, nos dois meses. As fixtures da REGIC são um subconjunto
    das ligações reais (`scripts/gerar_fixtures.py:1449-1550`), então as somas não chegam a 100.
  - No dado real, o teste nunca avisa: as 5.503 origens somam 100 ± 1e-12, em Q1 e em Q2.
  - Um aviso que sempre dispara no CI não sinaliza regressão.
- **Correção:** completar as fixtures com linhas "Outros" (destino `0`) que fechem 100 em cada origem, para o WARN
  voltar a ser sinal. Depois, conferir `WARN=5` no CI, como era antes do incremento.

## Mutações

Aplicadas uma a uma por script (troca de um trecho único) e revertidas com `git checkout`.

- **Modo `unit`:** só `pytest tests/unit`. Vale para as mutações P, que mexem no caminho **em rede** da ingestão, e
  esse caminho só os testes unitários exercitam: o CI usa `--origem-local`.
- **Modo `ci`:** os passos do `make ci` sem o lint. São os unitários, as fixtures, o `dbt parse`, os dois `pipeline`,
  o `atualizar`, o no-op, o backfill, o `rfb regras` e os testes de integração.

Uma mutação **morre** quando algum passo falha.

| # | Arquivo | Mutação | Resultado |
|---|---|---|---|
| P1 | `ibge.py` (`_reaproveitavel`) | ignora o período: reaproveita o CEMPRE de outro ano | morta: `test_cempre_do_mesmo_periodo_nao_rebaixa_salvo_renovar` |
| P2 | `ibge.py` (`cempre_municipio`) | não pede o Total (117897) | morta: `test_cempre_baixa_so_classes_e_total_e_retoma_sem_refazer_fatias` |
| P3 | `ibge.py` | não apaga as fatias depois de publicar | morta: o mesmo teste |
| **P4** | `ibge.py:242` | 429 deixa de ser retentado | **sobreviveu** (334 unitários verdes) |
| P5 | `ibge.py` (`_ausente_local`) | offline sem arquivo sobrescreve o raw existente com o vazio | morta: `test_origem_local_sem_um_arquivo_mantem_o_raw_existente_e_converte_os_demais` |
| D1 | `valor_ibge.sql` | `..` e `...` viram 0 | morta: unit tests dbt `stg_ibge__renda_municipio_pivo` e `stg_ibge__cempre_municipio_classe_simbolos` |
| D2 | `stg_ibge__cempre_municipio_classe.sql` | `tem_sigilo` só olha a variável 706 (nunca `X`) | morta: `test_stg_ibge__cempre_municipio_classe_simbolos` |
| D3 | `mart_concorrencia_area_mercado.sql` | `ativos_no_polo` sem `coalesce` (NULL em vez de 0) | morta: `test_mart_concorrencia_area_mercado_polo_de_compras` |
| **D4** | `estudo_caso_enriquecimento_ibge.sql:91` | renda da UF por `avg` simples em vez de ponderada | **sobreviveu** (CI inteiro verde, 235 de integração) |
| D5 | `stg_ibge__regic_hierarquia.sql` | código da hierarquia sem a letra (`1C` → `1`) | morta: `test_stg_ibge__regic_hierarquia_codigo` |
| D6 | `mart_emprego_setor_municipio.sql` | `ativos_rfb` conta também os não ativos | morta: `test_mart_emprego_setor_municipio_sigilo_mei_e_pares` |
| D7 | `cenario_renda_concorrencia.sql` | `<=` → `<` na mediana da densidade | morta: `test_analise_roda_nas_fixtures_com_as_colunas_e_a_linha_esperadas[cenario_renda_concorrencia]` |
| D8 | `int_regic__destinos_compras.sql` | `pct > 0` → `pct >= 0` (ligações zeradas entram na ponte) | morta: `test_int_regic_destinos_compras_posto_empate_e_outros` |

Não repeti as mutações já relatadas pelos implementadores:

- **IBG1:**
  - `X` vira 0;
  - fatia acima de 50.000;
  - Total junto das classes;
  - Q1 trocado com Q2.
- **IBG2:**
  - polo por Q1;
  - "Outros" como polo;
  - `ano_va` igual a `ano_pib`;
  - sigilo imputado;
  - RN-30 com MEI;
  - limiar `>3`.

## Conferências

### Fonte primária: o CEMPRE exclui o MEI (RN-30)

Fonte: a apresentação "Estatísticas do Cadastro Central de Empresas 2024" (IBGE, a [IBGE-CEMPRE] do catálogo). Baixei
o PDF e extraí o texto com `pypdf`.

- **Slide 7, nota (1):** "São excluídos do presente estudo: Microempreededores Individuais-MEI's; e Entidades com
  data de fundação superior a 31.12.2024". **Confere.**
- **Slide 8:** os critérios de unidade ativa. **Confere** com o catálogo da RN-30 e com a CAMADA_SEMANTICA.
  - eSocial;
  - pesquisas estruturais "independentemente da situação cadastral";
  - "situação cadastral ativa em 31.12 na Receita Federal" sem indicativo de inatividade;
  - a quebra de comparabilidade a partir de 2022.
- **Slide 14:** "7,6 milhões sem pessoas assalariadas (71,6%)". **Confere.**
- **Slide 6:** "Os dados oriundos das pesquisas anuais do IBGE prevalecem sobre os dos registros administrativos".
  **Confere** com o "O que não se sabe" da RN-30.

A RN-30 está boa no resto:

- o limiar 3 vem justificado;
- `rfb regras` sai com 0 havendo violações (`make ci`: 7 violadas, saída 0);
- as quebras `uf` e `faixa` estão na lista fechada (`regras.py:41-51`);
- os dois testes de privacidade cobrem a analysis.

### Fonte primária: o que é o % da REGIC

Baixei de novo a planilha `REGIC2018_Quest_Ligacoes_entre_Municipios.xlsx`. O sha256 do zip é o mesmo do manifesto do
IBG1 (`4c6ed5b8…`).

- **Aba "Descrição das variáveis":** Q2 é o "Percentual estimado de participação do destino sobre o total de
  deslocamentos dos moradores do município de origem para compra de móveis e eletroeletrônicos".
- **"Leia me":** o questionário levanta os destinos "quando estes se deslocam para busca de bens e serviços em outras
  localidades". Foi aplicado em 5.503 municípios.

Logo, a leitura das docs está certa: o % é a divisão **entre destinos de fora**, não a evasão total. Isso está em
`docs/CENARIOS_DE_USO.md:92-95` e `:172`, na analysis `cenario_polo_compras_evasao.sql`, na CAMADA_SEMANTICA e no
ADR-0022.

- **Soma por origem:** no dado real, Q1 e Q2 somam 100 ± 1e-12 em cada uma das 5.503 origens, contando "Outros".
- **Sem questionário:** as 67 origens sem questionário são todas de nível 1 ou 2. No ES são Serra, Vila Velha e
  Vitória. **Confere.**
- **Empates:** 111 origens têm empate no topo de Q2, resolvido pelo menor código, como documentado.

Ressalva menor de redação: o percentual é uma **estimativa** de informantes, como a CAMADA_SEMANTICA explica. Frases
como "98 % de quem sai de Colatina para comprar móveis vai a Vitória" (`CENARIOS_DE_USO.md:92`) soam como fluxo
medido. Sugiro "os informantes estimam que 98 %…".

### Números do dado real (SQL próprio, somente leitura)

Bases: raw IBGE real (cópia), gold real de 2026-09 e `raw/bd/pib` real.

| Afirmação (onde) | Recontado | |
|---|---|---|
| Fundão: renda média 1.406,78, mediana 1.040,00, 17.961 moradores; Vitória 3.351,64 / 1.750,00; Serra 1.541,03 / 1.100,00 | idem (10295, variáveis 13431/13534/13604) | confere |
| Polo de Fundão = Serra, 45 % em Q2 (Vitória 38,33; Aracruz 16,67; Q1 de Serra 46,67) | idem | confere |
| Fundão 1C, Metrópole, integrante do Arranjo Populacional de Vitória/ES | `hierarquia_3` = "1C - Integrante de Arranjo Populacional" | confere |
| `ano_va` = 2021 | VA completo nos 5.570 municípios em 2019–2021 e em 0 em 2022–2023 | confere |
| Fundão VA 2021: agro 8,88 %, indústria 25,68 %, serviços 37,93 %, adm. pública 27,51 % (cenário 4) | 37.339 / 420.573 = 8,88 %; 115.714 / 420.573 = 27,51 % | confere |
| Unidade do VA: R$, não R$ mil | PIB 2021 de Fundão = 468.483.000 | confere |
| VA negativo: indústria de Cachoeira Dourada/GO em 2021 | 5204250, −477.324.000; é o único município | confere |
| CEMPRE 2024, 47.41-5: Serra 33 / 196 / 167 (salários 6.358 mil); Vitória 25 / 164; Fundão `-`; Iconha 5 com `X` | idem | confere |
| Salário médio aprox. de Serra: 2.928,60 | 6.358.000 / 167 / 13 = 2.928,60 | confere |
| RFB 4741500: Serra 45 ativos (34 sem MEI); Vitória 28; Colatina 18; Linhares 23; Iconha 4/4 | idem (gold) | confere |
| Sigilo da 47.41-5 em 1.099 municípios; unidade local nunca `X` | 1.099; `X` na variável 706 = 0 | confere |
| Total do CEMPRE de Fundão: 1.054 unidades, 5.125 pessoas | idem | confere |
| ES, 47.41-5: 281 unidades, 1.207 pessoas (com sigilo), 391 ativos; renda da UF ponderada 1.650,72 | idem; 30 células `X` | confere |
| Cenário 1: mediana da renda do ES 1.256,01; 39 acima dela, 8 sem loja; Fundão 18.898 hab.; Domingos Martins 1.477,15 / 38.236 / 1 / 0,26 | idem | confere |
| Cenário 2: Colatina → Vitória 98,3 %, 2 destinos; Linhares → Vitória 88,3 %, 2 destinos | idem | confere |
| CEMPRE × RFB: 0,83 unidade por ativo sem MEI nos pares com as duas bases | Σ unidades ÷ Σ ativos sem MEI = 0,8264, em 738.765 pares | confere |
| **RN-30 Brasil: 2.107 violações em 1.073.321 avaliados; 1.935 sem nenhum ativo** | idem; com o limiar `>3`, seriam 1.114 | confere |
| Categorias 1.067; classes 673; CEMPRE com 15.016.720 linhas | idem | confere |
| "O IBGE marca `...` a mediana de alguns municípios" | nenhum símbolo nos 16.710 valores | **não confere** (RIBG-06) |

### Linha toda NULL no Parquet de modelo `external` vazio (pergunta do brief)

- **Comportamento confirmado no dbt-duckdb:**
  - Em `dbt/include/duckdb/macros/materializations/external.sql`, as linhas 62–73 gravam, com a relação vazia, "a
    non-empty table with column names and null values".
  - As linhas 96–140 fazem a view do warehouse filtrar essa linha.
  - O comportamento é do adaptador, não desta branch.
- **Onde aparece:** só em `bridge_municipio_destino_compras`, e só no modo offline sem `ibge/`.
  - `mart_emprego_setor_municipio` não fica vazio, porque fica com os pares da RFB.
  - `dim_municipio` também não, porque tem todos os municípios.
- **Modelos que já existiam:** nenhum muda. Um modelo só ganharia a linha se ficasse vazio, o que já valia na v1.3, e
  a branch não esvazia nenhum.
- **Para quem lê o Parquet direto** (Power BI):
  - aparece uma linha a mais, com todas as chaves NULL;
  - na relação com `dim_municipio`, ela vira um membro em branco e soma 1 na contagem de linhas;
  - as somas de `pct` não mudam.
- **Impacto:** baixo. Está documentado só em `docs/OPERACAO.md` (RIBG-08).

### Robustez da ingestão

- **Fatiamento:** 2 classes por requisição, 2 × 4 × 5.600 = 44.800 ≤ 50.000. Há teste, e o IBG1 relatou a mutação.
- **Retomada:**
  - cada fatia tem o nome do hash da URL;
  - é publicada por `replace`, com o `.bytes` gravado antes;
  - os resíduos `.tmp-*` são limpos no início.
  - P2 e P3 confirmam a cobertura.
- **Timeout:** o `httpx` usa o `tempo_limite_s` existente, de 60 s; o IBG1 mediu de 4 a 27 s por requisição.
- **Retentativas:** rede, 5xx, 408 e 429, com recuo. O 429 não tem teste (P4).
- **Erro em texto** "excedeu o limite": tratado com HTTP 200 e com 400.
- **Allowlist:** ganhou `apisidra.ibge.gov.br` e `geoftp.ibge.gov.br` e confere o host antes de cada GET.
- **Manifesto IBGE:** regravado atomicamente a cada tabela concluída (`tmp` + `replace`).
- **Falha parcial:** mantém o raw anterior e as fatias. É o comportamento certo para a tabela, mas derruba o mês
  (RIBG-02).
- **Arquivos temporários:**
  - `_tmp/extracao-ibge-*` é removido no `finally` e também por `_limpar_residuos`.
  - `_baixados/ibge/regic` não é removido por `ibge.py`; quem o apaga é `aplicar_retencao`, só no `atualizar`.
  - Isso funciona porque o nome `ibge` não é um mês e cai em "fora da janela" (`orquestracao.py:420-426`). Funciona
    por acaso. Fica como observação, não como achado.
- **`--renovar-ibge`:** separado de `--forcar`, com razão documentada. Na ingestão funciona; no `atualizar` sem mês
  novo, ver RIBG-04.

### Compatibilidade (interface pública × `d5fdce9`)

| Superfície | Situação |
|---|---|
| Colunas e grão do gold | só acréscimos: 23 colunas no fim de `dim_municipio` (contrato atualizado, `-1` com NULL) e 4 no fim de `mart_concorrencia_area_mercado` (o grão segue, a junta com o polo é 1:1); 2 modelos novos |
| `bh_empresas`, `agg_empresas`, `fct_resumo_mensal` | intocados |
| CLI e opções | só `--renovar-ibge` novo; nenhuma opção removida |
| Alvos `make` | inalterados |
| Variáveis de ambiente | só `RFB_CEMPRE_PERIODO` nova |
| Métricas e saved queries | 25 → 29 métricas e 4 → 5 saved queries; nenhuma alterada |
| Formato de `--origem-local` | `ibge/` opcional, e sem ela tudo funciona (teste de integração) |
| Manifesto do mês | chave `ibge` nova, com padrão vazio na leitura |
| Instalação | dependência nova `openpyxl>=3.1,<4` (pura Python), com `uv.lock` |
| **`RAIZ_DADOS` da v1.3 sem ingestão nova** | **quebra** (RIBG-01) |
| **Comando mensal em rede** | **dependência nova do IBGE** (RIBG-02) |
