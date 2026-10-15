# RSEM — Revisão independente do PR #1 (camada semântica, contexto de negócio e ontologia)

Revisor: agente RSEM (Traycer, Claude Opus), 2026-10-10. Não sou autor de nenhum dos 12 commits. Alvo: branch
`feat/camada-semantica`, HEAD `d9b6a92`, `git diff main...HEAD` (base `314c299`), PR
[#1](https://github.com/llrt/dbt-pipeline-rfb-v2/pull/1). Autores dos lotes: `1374daa` (líder), `d0b45ba`..`2d45e6c`
(FSEM) e `bb05085`..`d9b6a92` (FNEG). Não alterei código, YAML, docs nem testes. As mutações foram aplicadas e
revertidas com `git checkout`, e `git status --porcelain` ficou vazio no fim. Nada foi gravado no diretório de dados
reais: usei uma cópia do `warehouse.duckdb` no meu scratch, com links simbólicos só de leitura para `raw/` e `gold/`, e
rodei só `dbt parse --target dev`, `mf validate-configs` e `mf query`.

## Veredito

**APROVÁVEL COM RESSALVAS.** Não há bloqueante. A camada valida (`mf validate-configs`: 0 erros, nas fixtures e no
dado real), as métricas cobertas por teste batem com SQL direto, e os três comentários do Greptile foram resolvidos de
fato. A dinâmica bate com `mart_dinamica_mercado` também no dado real, de 2022 a 2026. Das 20 afirmações de negócio que
conferi nas fontes primárias, 16 estão corretas.

Há 4 achados importantes. Convém resolvê-los antes do merge, ou pelo menos registrá-los na doc:

1. **RSEM-01:** a "fotografia mensal" devolve um mês **antigo** quando o filtro da consulta esvazia o último mês. A doc
   promete o último mês do período. Reproduzi o caso: 1 loja ativa em vez de 0.
2. **RSEM-02:** 7 das minhas 8 mutações sobreviveram. Os testes comparam diretamente 10 das 25 métricas. Ninguém testa
   `qtd_ativos_mei`, `pct_ativos`, `pct_mei_entre_ativos`, `variacao_mensal_ativos_pct` nem as taxas de 1 e 5 anos. A
   fotografia dos numeradores dos ratios também fica sem teste.
3. **RSEM-03:** a doc e a ontologia definem sobrevivente como "ainda ativo". O mart conta também quem foi encerrado
   **depois** do horizonte.
4. **RSEM-04:** no dado real, 44 % dos `encerramentos` de 2026 são **inaptidões** (1,88 M, um lote administrativo). Com
   isso, o saldo de 2026 cai para 63 mil, contra 2,27 M em 2025. O ano e o mês correntes também são parciais (extrato de
   12/09). A doc não avisa nenhum dos dois.

Execução:

- `caffeinate -i make ci`: **verde em 2 min 31 s**. 249 unit + 135 integração; `dbt build` PASS=354 WARN=5 ERROR=0 nos
  dois meses; backfill PASS=199 WARN=2; lint limpo.
- `make semantica RAIZ_DADOS=$PWD/.tmp/ci/dados`: validação com 0 erros, 25 métricas listadas.
- `scripts/verificar_doc_semantica.py`: 291 itens conferidos, 0 pendências.
- **Dado real (2026-09):**
  - `mf query` dá 73.366.147 estabelecimentos, 28.263.121 ativos, 70.085.592 matrizes, 13.738.467 ativos MEI e idade
    média de 7,50 anos.
  - O total de estabelecimentos é o do `EXECUCAO_REAL.md` e da R4.
  - `estudo_caso_fundao_tintas` devolve MICRO, 5 estabelecimentos e 0 ativos: é o "0 ativos e 5 inativos" do
    `RELATORIO_ESTUDO_CASO.md`.
  - `aberturas`/`encerramentos`/saldo por ano (2022–2026) são idênticos à soma do `mart_dinamica_mercado` real.
  - As consultas levam 1,6 s a 3,8 s.

## Achados

Severidade: **bloqueante** (impede o merge), **importante** (corrigir antes de fechar), **menor**, **sugestão**.

### RSEM-01 — fotografia mensal devolve mês antigo quando o filtro esvazia o último mês (importante, métrica)

- **Onde:** `transform/models/marts/core/_core__models.yml:741` e seguintes (`non_additive_dimension: { name: mes,
  window_agg: max }` nas 6 contagens do resumo). A promessa está em `docs/CAMADA_SEMANTICA.md:509`
  ("num período maior que o mês, vale o **último** mês"), `:669-673` e `docs/adr/0018-camada-semantica-metricflow.md:18`.
- **Problema:** o MetricFlow calcula o `MAX(mes)` sobre as linhas **já filtradas** pelo `--where`. Se o filtro não
  deixa nenhuma linha no último mês, ele escolhe o mês mais recente que sobrou e devolve essa fotografia velha, em vez de
  0 (ou vazio). Vale para consultas sem `metric_time` e para grão de ano. O SQL gerado mostra o `MAX` com o mesmo `WHERE`:

  ```text
  $ uv run mf query --metrics qtd_ativos --group-by metric_time__year,municipio__sigla_uf \
      --where "{{ TimeDimension('metric_time','month') }} <= '2026-08-01'" --explain
  ... INNER JOIN (SELECT metric_time__year, MAX(mes__month) AS mes__month__complete FROM (...)
                  WHERE metric_time__month <= '2026-08-01' GROUP BY metric_time__year) ...
  ```

- **Reprodução** (cópia do warehouse das fixtures no scratch). No cenário, a única loja de tintas ativa de Fundão passa
  a BAIXADA em 2026-09; a view `fct_resumo_mensal` da cópia foi redefinida com essa troca:

  ```text
  W="Fundão" + cnae 4741500 + situacao_cadastral__rotulo_situacao_cadastral = 'ATIVA'
  --- por mês:   2026-08-01   qtd_estabelecimentos 1      (2026-09 não aparece: correto)
  --- por ano:   2026-01-01   qtd_estabelecimentos 1      (errado: a fotografia de 2026 é 2026-09, com 0)
  --- sem tempo:              qtd_estabelecimentos 1      (errado: "quantas lojas ativas há?" → 1)
  --- qtd_ativos sem o filtro de situação, por ano: 0     (correto: a linha BAIXADA de 2026-09 existe)
  ```

  A pergunta "quantas lojas ativas há em Fundão?" é a pergunta-guia do projeto. Os padrões da A6 também levam a ela
  (filtro `ATIVA`, recortes finos de município × CNAE × porte × MEI). Ainda não aparece no dado real porque o resumo
  real só tem 2026-09, mas aparece a partir do segundo mês de série.
- **Correção sugerida:** o MetricFlow não oferece um `MAX` fora do filtro, então o caminho é documentar e guiar:
  1. Na B3, na A6 e no ADR, trocar "vale o último mês do período" por "vale o último mês **em que o recorte filtrado
     tem linhas**".
  2. Recomendar, para estoque atual, agrupar por `metric_time__month` ou filtrar `metric_time` no mês desejado.
  3. Preferir `qtd_ativos` a `qtd_estabelecimentos` com filtro `ATIVA`: o resumo guarda as linhas zeradas das outras
     situações, e por isso esse caso dá o número certo.
  4. Acrescentar um teste de integração com um recorte que só existe no penúltimo mês. A fixture tem a filial de Serra
     só em 2026-09; o caso inverso exige uma linha nova na fixture.

### RSEM-02 — 15 das 25 métricas sem comparação direta; 7 de 8 mutações sobrevivem (importante, teste)

- **Onde:** `tests/integration/test_camada_semantica.py:59-95` e a lista de garantias em `docs/CAMADA_SEMANTICA.md:720-739`.
  A doc diz "métricas mensais iguais ao SQL direto no gold".
- **Problema:** os testes comparam com SQL `qtd_estabelecimentos`, `qtd_ativos`, `idade_media_anos` e
  `capital_social_medio` só no grão mensal. A fotografia só é provada em `qtd_ativos`/`qtd_estabelecimentos`. Também
  entram `qtd_ativos_mes_anterior`, `variacao_mensal_ativos`, a dinâmica e a `taxa_sobrevivencia_3a`. Ficam sem teste:
  `qtd_ativos_mei`, `pct_ativos`, `pct_mei_entre_ativos`, `variacao_mensal_ativos_pct`, `capital_social_total`,
  `soma_idade_anos_ativos` fora do grão mensal, as taxas e contagens de 1 e 5 anos e as 3 *saved queries* além de
  Fundão e da dinâmica. Mutações sobreviventes (tabela em [Mutações](#mutações)): M1, M2, M3, M4, M6, M7.
- **Por que importa:**
  - M3 e M7 tiram o `non_additive_dimension` do **numerador** de um ratio (`soma_idade_anos_ativos`,
    `capital_social_total`). A idade média e o capital médio por ano passam a somar os meses no numerador e a dividir
    pelo último mês: o valor quase dobra com 2 meses, e os testes não percebem.
  - M1 transforma `qtd_ativos_mei` em `qtd_ativos` e passa.
- **Correção sugerida:**
  1. Estender `test_metricas_mensais_batem_com_o_resumo` a **todas** as métricas do resumo, com o SQL equivalente.
  2. Estender `test_fotografia_mensal_nao_soma_meses` a todas as contagens e aos 4 ratios, por ano e sem tempo. A
     fixture já discrimina: 2026-08 ≠ 2026-09.
  3. Comparar as taxas de 1 e 5 anos como a de 3 e checar `variacao_mensal_ativos_pct`.
  4. Corrigir a B6 para listar só o que está provado.

### RSEM-03 — "sobrevivente" definido como "ainda ativo" na doc e na ontologia (importante, negócio)

- **Onde:** `docs/CAMADA_SEMANTICA.md:357` ("Quantos sobrevivem? | `taxa_sobrevivencia_3a` etc. | ainda ativos entre os
  elegíveis da coorte de abertura") e `docs/ontologia/rfb_cnpj.ttl:453` ("elegíveis e sobreviventes (ainda ativos)").
- **Problema:** a regra do mart (`_analytics__models.yml:80-81`, unit test
  `test_mart_sobrevivencia_coorte_elegibilidade_e_sobrevivencia`) é outra: "sobrevive quem está ativo **ou foi encerrado
  após `dat_inicio + N anos`**". Um estabelecimento aberto em 2015 e baixado em 2024 sobrevive aos 3 e aos 5 anos, mas
  não está "ainda ativo". Quem ler a Parte A, que existe justamente para dar o significado, vai entender a
  `taxa_sobrevivencia_5a` como "% ainda ativo". O número real é maior que isso.
- **Correção sugerida:** "elegíveis que seguiam ativos N anos depois da abertura (ativos hoje ou encerrados depois do
  aniversário de N anos)", nas duas fontes. Na descrição das métricas `sobreviventes_*a` (`_analytics__models.yml:109`
  e seguintes), trocar "sobrevivem" pela mesma definição.

### RSEM-04 — `encerramentos` no dado real: 44 % de 2026 são inaptidões, e o ano corrente é parcial (importante, negócio)

- **Onde:** `docs/CAMADA_SEMANTICA.md:351-361` (tabela "Ligação com as métricas") e `:749-755` (B7); saved query
  `dinamica_anual_por_secao_cnae`.
- **Evidência** (dado real, 2026-09):

  ```text
  $ uv run mf query --metrics encerramentos --group-by metric_time__year,situacao_cadastral__rotulo_situacao_cadastral \
      --where "{{ TimeDimension('metric_time','year') }} >= '2025-01-01'"
  2025  BAIXADA 2.876.437 | SUSPENSA 45.693 | NULA 2.454 | INAPTA 629
  2026  BAIXADA 2.324.471 | INAPTA 1.883.442 | SUSPENSA 34.231 | NULA 1.632
  $ ... --metrics aberturas,encerramentos,saldo_aberturas_encerramentos --group-by metric_time__year
  2025  5.195.238  2.925.213  2.270.025
  2026  4.306.795  4.243.776     63.019
  $ ... --metrics aberturas --group-by metric_time__month (2026-07..09)
  510.701 | 522.738 | 179.463     (o extrato é de 12/09: setembro tem só 12 dias)
  ```

- **Problema:** a regra é a do mart e está documentada ("não só baixada"). A doc, porém, não avisa duas coisas:
  1. A inaptidão chega em **lotes administrativos** (ADE da RFB, IN 2.119, arts. 39 e 46) e é reversível (art. 47).
     Um lote derruba o saldo de um ano inteiro: 2026 parece "mercado estagnado", com saldo de 63 mil, por causa de 1,88 M
     inaptidões com data em 2026.
  2. O ano e o mês do extrato são **parciais**.

  A `dinamica_anual_por_secao_cnae` mostra 2026 lado a lado com anos completos.
- **Correção sugerida:**
  - Na A3 e na B7, avisar dos lotes de inaptidão e do período parcial, com o exemplo acima.
  - Sugerir a quebra por `situacao_cadastral__rotulo_situacao_cadastral`, ou uma métrica `baixas` (só BAIXADA), para
    quem quer "fechamentos definitivos".
  - Na saved query, filtrar `metric_time` até o último ano completo, ou dizer no `description` que o último ano é
    parcial.

### RSEM-05 — prazo de opção pelo Simples desatualizado pela Resolução CGSN 190/2026 (menor, fonte)

- **Onde:** `docs/CAMADA_SEMANTICA.md:185-186` ("formalizada até o último dia útil de janeiro, com efeito desde 1º de
  janeiro [CGSN 140, art. 6º, § 1º]").
- **Evidência:** o texto multivigente da CGSN 140 na RFB (acessado em 2026-10-10) traz, no art. 6º e no § 1º, "[Vide
  modificação prevista para 01/01/2027, nos termos do(a) Resolução CGSN nº 190, de 4 de agosto de 2026]". A nova
  redação muda a formalização para "o período de 01 (um) de setembro a 30 (trinta) de setembro", com efeitos "a partir
  do primeiro dia do ano-calendário seguinte", e cria um § 1º-B (cancelamento até 30/11). A imprensa contábil noticia
  prorrogação da janela de 2026 até 15/10 (Res. CGSN 194/2026); não conferi na fonte primária. Ou seja, a opção para
  2027 já está sendo feita em setembro e outubro de 2026.
- **Correção sugerida:** manter a regra vigente e acrescentar a ressalva da CGSN 190/2026, como foi feito com o PLP
  186/2026 no MEI.

### RSEM-06 — MEI: definição legal simplificada e afirmações sem fonte que as sustente (menor, negócio)

- **Onde:** `docs/CAMADA_SEMANTICA.md:143-144` e `:189-199`; `docs/ontologia/rfb_cnpj.ttl:226`.
- **Problemas:**
  1. "O MEI é um empresário individual [LC 123, art. 18-A, § 1º]". Desde a LC 188/2021, o § 1º inclui também "o
     empreendedor que exerça" atividades extrativistas (§ 4º-A), as autorizadas pelo CGSN (§ 4º-B) e as rurais (inc.
     III). A CGSN 140, art. 100, repete isso. A afirmação continua certa para a imensa maioria, mas está incompleta.
  2. A natureza "213-5 Empresário (Individual)" do MEI é atribuída a [CONCLA-NJ], mas a tabela da CONCLA não fala de MEI.
     No dado real a afirmação se sustenta quase toda: dos 17.527.414 estabelecimentos com `opcao_mei`, 17.526.176 são
     2135. Mas 1.237 são "Sociedade Empresária Limitada" (2062) e 1 é "em Nome Coletivo" (2070).
  3. A doc diz que o MEI tem "um único estabelecimento" (regra legal correta, art. 18-A, § 4º, II). No dado há 3.749
     **filiais** de empresas MEI. Isso importa para a leitura de `qtd_ativos_mei`, que conta estabelecimentos.
- **Correção sugerida:** citar o § 1º completo; trocar a fonte da natureza por "observação do projeto no dado real
  (99,99 %)" e registrar as exceções; avisar que o dado tem MEI com filial e com natureza de sociedade.

### RSEM-07 — citações que não sustentam exatamente a frase e faculdades lidas como automáticas (menor, fonte)

- **Onde e evidência** (texto multivigente da IN RFB 2.119/2022):
  - `docs/CAMADA_SEMANTICA.md:110-111` e `:334` ("A inscrição da entidade corresponde à matriz [IN 2.119, art. 9º]") e
    `rfb_cnpj.ttl:78`. O art. 9º diz só que "a inscrição no CNPJ da entidade ou do estabelecimento filial pode ser
    enquadrada" nas cinco situações; não fala de matriz. O mais próximo é o art. 4º, § 1º (entes federativos "na
    condição de estabelecimento matriz"). A leitura do projeto é razoável, mas é inferência, não citação.
  - `:239-240` e o diagrama da A3: os arts. 38 e 31 dizem "**Pode** ser declarada inapta" e "**Pode** ser baixada de
    ofício". A tabela os apresenta como "quando ocorre", e o diagrama como transição certa ("180 dias sem regularizar").
    Os prazos estão corretos (90 dias, 1 ano, 180 dias, 5 anos), mas são condições necessárias, não gatilhos
    automáticos. Isso reforça o RSEM-04: a inaptidão chega por ADE, em lote.
  - `:112`: "baixa da matriz implica a baixa de todas as filiais [art. 24, § 2º]" confere.
- **Correção sugerida:** marcar a frase da matriz como leitura do projeto (art. 4º, § 1º, e art. 9º); trocar "quando
  ocorre" por "pode ocorrer quando".

### RSEM-08 — a ontologia é OWL válido, mas o teste só prova existência, e há dois desvios conceituais (menor, ontologia)

- **O que conferi:**
  - Parse Turtle com rdflib: 416 triplas. O fechamento OWL-RL (`owlrl`) passa sem inconsistência (1.056 triplas após a
    inferência).
  - Toda classe tem pelo menos um mapeamento. Domínios e imagens declarados. Única propriedade não declarada:
    `dcterms:source`; o OWL 2 DL estrito pede `owl:AnnotationProperty`.
  - Conceitualmente, empresa × estabelecimento, porte, natureza e Simples/MEI na empresa e situação no estabelecimento
    estão certos e coerentes com o leiaute.
  - `pertenceAEmpresa` funcional e `Matriz owl:disjointWith Filial` corretos. O "1..*" de `possuiEstabelecimento` está
    só no comentário (sem restrição de cardinalidade), o que é aceitável para documentação.
- **Problemas:**
  1. **O teste não prova o mapeamento certo, só o existente.** A mutação M5 move `qtd_ativos_mei` e
     `pct_mei_entre_ativos` de `OpcaoMEI` para `Porte`, e os 3 testes passam. A B6 descreve o teste corretamente ("cobre
     a camada nos dois sentidos"), então isso não é uma alegação falsa. Mas o mapeamento conceito → métrica não tem
     guarda. Errado hoje, o que pegou: RSEM-03 (`CoorteDeAbertura`, "ainda ativos").
  2. `OpcaoSimplesNacional` mistura "registro no arquivo Simples" (`temOpcaoSimples` 0..1, inclusive com opção `N`) com
     "opção pelo regime". Uma empresa com registro `N` seria instância da classe "Opção pelo Simples".
- **Correção sugerida:** declarar `dcterms:source` como `owl:AnnotationProperty`. Separar `RegistroSimples` de
  `OpcaoSimplesNacional` ou ajustar o comentário. Opcionalmente, um teste de "afinidade": toda métrica mapeada num
  conceito usa um modelo semântico que o conceito também anota (`rfbo:entidadeSemantica`/`modeloDbt`), o que pegaria M5.

### RSEM-09 — equivalência DAX × MetricFlow vale só no grão mensal (menor, documentação)

- **Onde:** `docs/CAMADA_SEMANTICA.md:645-646` ("são as **mesmas medidas DAX**") e `:715-717` ("Use `mf query --csv` ou
  `--explain` para conferir um número do painel"); `docs/POWER_BI.md:208-210`.
- **Problema:** `Qtd Ativos = SUM ( fct_resumo_mensal[qtd_ativos] )` soma os meses num visual por ano. Fica a cargo de
  quem monta o painel lembrar do "Não some meses", em `POWER_BI.md:277`. A métrica usa o último mês. Quem conferir um
  total anual do painel com o `mf` acha números diferentes e pode concluir que um dos dois está errado.
- **Correção sugerida:** na B3, dizer que a equivalência vale no grão mensal. Em grão maior, o DAX precisa de
  `LASTNONBLANK`/`CALCULATE(..., LASTDATE(...))` para dar o mesmo número. Opcionalmente, sugerir essa versão no guia.

### RSEM-10 — `verificar_doc_semantica.py` não roda no CI e não confere os números da prosa (menor, operação)

- **Onde:** `scripts/verificar_doc_semantica.py`; citado só em `docs/adr/0018-camada-semantica-metricflow.md:63`
  (`git grep` não acha chamada no `Makefile`, nos testes nem em `.github/workflows/ci.yml`).
- **Problema:** o script passa hoje (0 pendências), mas ninguém o roda. Mesmo com `--executar-exemplos`, ele só exige
  saída 0, não confere os números da prosa (por exemplo "11 ATIVA, 1 INAPTA, 5 BAIXADA" ou "10 matrizes ativas"). Os
  números estão certos hoje (conferi A2, A6 e B5 nas fixtures). Na próxima recalibração de fixture, como a linha Q do
  FSEM, envelhecem sem aviso.
- **Correção sugerida:** chamar a parte estática do script no `make ci` (é rápida) ou envolvê-la num teste de
  integração. Para os números, um teste que rode as consultas da A6 e compare com a prosa, ou trocar a prosa por
  "veja a saída do comando".

### RSEM-11 — *time spine* expõe as datas sentinela como `metric_time` (sugestão)

- **Onde:** `transform/models/marts/core/_core__models.yml:404` (`time_spine` em `dim_data`).
- **Evidência:** `uv run mf query --group-by metric_time__day --order metric_time__day --limit 3` devolve `1899-12-30`,
  `1899-12-31` e `1900-01-01`. Isso não afeta nenhuma métrica: as derivadas de tempo ficam no resumo (de 2026 em
  diante), e `aberturas`/`encerramentos` filtram as datas nulas. Mas consultas de dimensão pura e futuras métricas com
  `join_to_timespine` ou `cumulative` veriam dois "dias" que não existem.
- **Correção sugerida:** registrar no ADR-0018 ou na B7; se um dia incomodar, um modelo `time_spine` próprio (view de
  `dim_data` sem os membros `-1` e `-2`).

### RSEM-12 — sugestões

- **Dependências:** `dbt-metricflow` e `rdflib` entram sem limite de versão (`pyproject.toml:26`, `:28`). O `uv.lock`
  trava 0.15.0 e 7.6.0, e o `make setup` usa `--locked`, então o CI está seguro. Mas a semântica da camada depende do
  MetricFlow: `non_additive_dimension` (RSEM-01) e o descarte de `fill_nulls_with` contornado com `coalesce`. Um piso
  `dbt-metricflow>=0.15,<0.16` documenta a dependência. Ambas são justificadas no comentário e são só de
  desenvolvimento.
- **Contagem de empresas pelas matrizes:** `docs/CAMADA_SEMANTICA.md:114-115` diz que "o projeto não verificou o dado
  real". Verifiquei: 70.085.592 matrizes para 70.085.591 CNPJs básicos; todo básico tem matriz, e só um (`08314885`) tem
  duas. A frase pode ser trocada pelo número.
- **Ontologia:** `rfbo:codigoRfb` usa `"1"` e `"8"` nas situações, mas `"00"`/`"01"` no porte. O leiaute escreve `01` e
  `08`. Uniformizar.
- **Registro do lote:** `.specs/STATE.md:45` (AD-037) fala em "7 testes de integração". Hoje são 8 em
  `test_camada_semantica.py`, mais 3 de ontologia.
- **dbt v2:** não reproduzi o "verificado com o dbt 2.0.8" do ADR-0018: não há binário do dbt Fusion neste ambiente. As
  duas precauções citadas (`input_metrics` como objetos, *saved queries* sem `order_by`) estão no YAML.

## Comentários do Greptile

| # | Comentário | Status | Evidência |
|---|---|---|---|
| 4235981047 | "Older dbt versions remain allowed" | **Resolvido** | `d0b45ba`: `pyproject.toml` `dbt-core>=1.12,<2` e `dbt_project.yml` `require-dbt-version: [">=1.12.0", "<2.0.0"]`; `uv.lock` em 1.12.5 |
| 4235981050 | "Reports count different closures" (`encerramentos` só BAIXADA ≠ mart) | **Resolvido** (a regra foi alinhada ao mart, não só a descrição) | `e9dc13c`: `encerramentos` usa `not eh_ativa` + data da situação válida; a saved query diz "mesma regra e mesmos números". Conferi nas fixtures (teste por ano × seção) e no **dado real** (2022–2026 idênticos ao mart) |
| 4235981057 | "Event years are not tested" | **Resolvido** | `675b875`: comparações agrupadas por ano e por ano × seção contra o mart, com o saldo; pré-condições exigem inativo com anos de início ≠ situação, ano com eventos de um lado só e datas `-1`/`-2` (linha Q). As mutações M-a..M-e do FSEM cobrem as regras. O que segue sem teste está no RSEM-02 |

## Mutações

Cada mutação: aplicada com substituição exata, `dbt parse --no-partial-parse --target ci`, `pytest -q` de
`tests/integration/test_camada_semantica.py`, `test_ontologia.py` e `test_escopo_meta.py` (14 testes) sobre o gold do
`make ci`, e revertida com `git checkout`. Nenhuma repete as já feitas (M-a..M-e do FSEM, mapeamento removido ou
inexistente no TTL do FNEG, métrica sem conceito do líder). Script: `mutacoes.py` no scratch do revisor.

| # | Mutação | Resultado | Teste que deveria pegar |
|---|---|---|---|
| M1 | `qtd_ativos_mei` sem o `filter` de `opcao_mei` (vira `qtd_ativos`) | **sobreviveu** (14 passed) | comparar `qtd_ativos_mei`/`pct_mei_entre_ativos` com SQL |
| M2 | `pct_ativos` com denominador `qtd_matrizes` | **sobreviveu** | comparar `pct_ativos` com SQL |
| M3 | `soma_idade_anos_ativos` sem `non_additive_dimension` (numerador de `idade_media_anos`) | **sobreviveu** | fotografia dos ratios por ano |
| M4 | `variacao_mensal_ativos_pct` dividindo por `qtd_ativos` em vez do mês anterior | **sobreviveu** | checar a variação % |
| M5 | ontologia: `qtd_ativos_mei` e `pct_mei_entre_ativos` movidas de `OpcaoMEI` para `Porte` | **sobreviveu** | afinidade conceito × modelo (RSEM-08) |
| M6 | `taxa_sobrevivencia_1a` com numerador `sobreviventes_3a` | **sobreviveu** | comparar as taxas de 1 e 5 anos |
| M7 | `capital_social_total` sem `non_additive_dimension` (numerador de `capital_social_medio`) | **sobreviveu** | fotografia dos ratios por ano |
| M8 | controle: `qtd_ativos` com `window_agg: min` | morta (`test_fotografia_mensal_nao_soma_meses`) | — |

Sobreviventes: M1, M2, M3, M4, M5, M6, M7 (7 de 8). M8 mostra que o parse pega a mutação, e que a fixture de 2 meses
discrimina quando há teste.

Além das mutações, reproduzi o bug de *partial parse*. Com um `dbt parse` incremental depois de editar um `label` no
YAML, o resultado é `Compilation Error: dbt found two metrics with the name "pct_ativos"`. O contorno do Makefile
(`PARSE_COMPLETO` nos alvos `ci`, `pipeline`, `atualizar` e `semantica`) funciona, e a B7 ensina o mesmo.

## Afirmações de negócio conferidas

Fontes primárias acessadas em 2026-10-10. A IN 2.119 e a CGSN 140 foram lidas no texto multivigente da RFB
(normasinternet2), a LC 123 no texto compilado do Planalto e o leiaute no PDF `cnpj-metadados.pdf`.

| # | Afirmação (doc / TTL) | Fonte | Resultado |
|---|---|---|---|
| 1 | Situação cadastral: 01 NULA, 2 ATIVA, 3 SUSPENSA, 4 INAPTA, 08 BAIXADA | Leiaute RFB, p. 2 | confere |
| 2 | Porte 00/01/03/05; "05 – Demais" (sem "médio e grande") | Leiaute, p. 1 | confere (a doc já ressalva o rótulo do seed) |
| 3 | Opção Simples/MEI S/N/"em branco – outros"; ente federativo só no grupo 1XXX; CNAEs secundárias por vírgula; CPF dos sócios parcialmente oculto | Leiaute, pp. 1, 3, 4 e 6 | confere |
| 4 | Cinco situações e "não se confundem com a condição de atividade ou inatividade" | IN 2.119, art. 9º e parágrafo único | confere |
| 5 | "A inscrição da entidade corresponde à matriz" | atribuída ao art. 9º | **o art. 9º não diz isso** (RSEM-07) |
| 6 | Hipóteses de suspensão (interrupção, inconsistência, não localização, interposição, inaptidão em curso, ordem judicial) | IN 2.119, art. 37, I a VIII | confere |
| 7 | Inaptidão: omissão ≥ 90 dias; inexistência de fato; suspensa ≥ 1 ano | IN 2.119, art. 38, I, III e X | confere; é faculdade ("pode", RSEM-07) |
| 8 | Baixa de ofício da inapta não regularizada em 180 dias; óbito do MEI; ordem judicial | IN 2.119, art. 31, I, III e V | confere; é faculdade |
| 9 | Suspensão por interrupção comunicada ou ordem judicial vira inapta só após 5 anos; restabelecimento volta à suspensão se o motivo persistir | IN 2.119, art. 46, § 1º, e art. 47, parágrafo único | confere |
| 10 | Baixa da matriz implica baixa das filiais; baixa não impede lançamento posterior | IN 2.119, art. 24, §§ 2º e 4º | confere |
| 11 | Nulidade (duplicidade, vício, não obrigado), com efeito desde o início; restabelecimento da baixada | IN 2.119, arts. 34 e 26 | confere |
| 12 | Formato alfanumérico a partir de julho de 2026; filial pode virar matriz; definição de estabelecimento | IN 2.119, art. 2º, parágrafo único, art. 4º, § 3º, e art. 5º | confere |
| 13 | Primeiro CNPJ alfanumérico em 31/07/2026 | notícia da RFB de 31/07/2026 | confere |
| 14 | ME até R$ 360.000,00; EPP acima disso e até R$ 4.800.000,00 | LC 123, art. 3º, I e II (redação da LC 155/2016) | confere |
| 15 | MEI: até R$ 81.000,00; R$ 6.750,00/mês no ano de início; um estabelecimento; sem outra empresa; um empregado | LC 123, art. 18-A, §§ 1º, 2º e 4º (II e III), e art. 18-C | confere; o § 1º inclui também o "empreendedor" (LC 188/2021, RSEM-06) |
| 16 | Transportador autônomo de cargas: R$ 251.600,00; empregado do MEI; desenquadramento do SIMEI não exclui do Simples | CGSN 140, art. 100, § 1º-A, I, art. 105 e art. 115, § 1º | confere |
| 17 | Opção pelo Simples até o último dia útil de janeiro, com efeito desde 1º de janeiro | CGSN 140, art. 6º, § 1º | **vigente, mas já alterada** para setembro pela CGSN 190/2026, com efeito em 01/01/2027 (RSEM-05) |
| 18 | PLP 186/2026: Poder Executivo, apresentado em 29/06/2026, "Aguardando Despacho do Presidente", último andamento em 24/08/2026 | ficha de tramitação da Câmara | confere |
| 19 | Códigos CONCLA 101-5, 103-1, 124-4, 204-6, 205-4, 206-2, 213-5, 399-9 e os 5 grupos | CONCLA, Natureza Jurídica 2021 | confere |
| 20 | MEI tem natureza 213-5 | atribuída a [CONCLA-NJ] | **a fonte não sustenta**; o dado real dá 99,99 %, com 1.238 exceções (RSEM-06) |

Conferências no dado real, além das fontes:

- Uma matriz por CNPJ básico: vale, com 1 exceção (RSEM-12).
- 3.749 filiais de empresas MEI (RSEM-06).
- Situação × data: todo inativo tem data da situação; 115.651 ativos não têm.
- `encerramentos` de 2026 com 44 % de INAPTA (RSEM-04).
