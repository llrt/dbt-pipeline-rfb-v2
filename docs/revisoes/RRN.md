# RRN — Revisão independente do lote RN (regras e invariantes de negócio, futuro PR B → v1.3.0)

Revisor: agente RRN (Traycer, Claude Opus), 2026-10-13. Não sou autor de nenhum dos 6 commits. Alvo: branch
`feat/regras-negocio`, HEAD `e75e4d3`, `git diff main...HEAD` (base `af327d4` = v1.2.0). Não alterei código, YAML,
docs nem testes. As mutações foram aplicadas e revertidas com `git checkout`, e `git status --porcelain` ficou vazio
no fim. Nada foi gravado no diretório de dados reais. Usei um `dados/` no meu scratch com links simbólicos para `raw/` e
`gold/`, um `_tmp/` próprio, um clone APFS (`cp -c`) do `warehouse.duckdb` em `CAMINHO_DUCKDB` e
`RFB_EXTERNAL_ROOT` vazio. Contra esse ambiente rodei só `dbt parse --target dev`, `rfb regras --target dev` e
consultas DuckDB `read_only`.

## Veredito

**APROVÁVEL COM RESSALVAS.** Não há bloqueante.

O que está bem:

- **Pedido atendido.** As três regras do usuário viraram checks: CNAE em RN-01 a RN-04, MEI em RN-05 e "ativa sem
  encerramento" em RN-10 a RN-13. A tradução da terceira está explicada e é razoável.
- **Fontes.** Das 13 afirmações legais e de leiaute que conferi nas fontes primárias, 12 conferem.
- **Relatório reproduzível.** O relatório versionado se reproduz byte a byte acima da "Interpretação": `rfb regras`
  no dado real levou 72 s e saiu com 0.
- **Recontagem independente.** Recontei 11 regras com SQL próprio no dado real, e todas batem.
- **Não falha o build.** `rfb regras` sai com 0 havendo violações. O `make ci` está verde, com 4 regras violadas nas
  fixtures, e `make dicionario` não gera diff. O lote não toca modelos, testes de dados nem fixtures.

Há 4 achados importantes. Convém resolvê-los antes do merge, porque três deles mudam números ou o texto do relatório
versionado:

1. **RRN-01, privacidade:** a guarda é só léxica. Um CNPJ **formatado** (`14.141.414/0001-55`) aparece no relatório
   do CI com os 38 testes verdes (mutação M7). Uma raiz de 8 dígitos e o CNPJ alfanumérico também passam.
2. **RRN-02, RN-13:** dá falso positivo estrutural.
   - 1.038 das 1.048 "datas futuras" são **exatamente 2026-09-13**, o dia seguinte ao `_data_referencia`.
   - As outras 10 são opções pelo Simples com data **2027-01-01**, que o próprio projeto documenta como legítimas
     (CGSN 190/194: a opção feita em setembro vale a partir de 1º/1/2027).
   - A interpretação atribui tudo a "erros de data ou atos registrados com data futura".
   - No extrato de outubro, todas as opções para 2027 virarão "violação".
3. **RRN-03, RN-05 e RN-14:** as duas regras contam como violação casos que o próprio catálogo diz não violarem a
   regra.
   - **RN-05** dá 3.247 empresas MEI no resumo, mas só **33** têm mais de um estabelecimento não baixado.
   - **RN-14** dá 404 filiais, mas 245 delas são NULAS, que o catálogo trata como limite da tradução.
4. **RRN-04, testes:** só conferem o total de violações por regra. As 10 mutações que fiz **sobreviveram**, e 8 delas
   nem mudam o relatório das fixtures.

Execução:

- `caffeinate -i make ci`: **verde**.
  - Testes: 292 unitários e 162 de integração.
  - `dbt build`: PASS=354 WARN=5 ERROR=0 nos dois meses. Backfill: PASS=199 WARN=2.
  - `rfb regras` nas fixtures: "24 regras, 4 violadas", saída 0. Lint limpo.
- `make dicionario`: sem diff.
- ADR-0006: todas as 24 analyses têm `meta.escopo: adicao` e a tag `escopo_adicao`, e o `test_escopo_meta` cobre
  analyses.
- ADR-0014: subcomando, alvo e módulo em português, nas listas de `test_convencao_nomes.py`. O ADR-0014 só enumera os
  nomes renomeados, então não precisava mudar.
- Escopo: `git diff main...HEAD --stat` não toca `transform/models`, `transform/tests`, `transform/macros`, `scripts/`
  nem `tests/fixtures`. `relatorio.py` só ganhou os parâmetros `subpasta` e `padrao`, com padrão compatível.
- Performance: 72,4 s de parede no dado real (`DUCKDB_MEMORY_LIMIT=16GB`, `DUCKDB_THREADS=4`). O
  `docs/OPERACAO.md` diz 73 s.

## Achados

Severidade: **bloqueante** (impede o merge), **importante** (corrigir antes de fechar), **menor**, **sugestão**.

### RRN-01 — a guarda de privacidade é léxica: CNPJ formatado, raiz e CNPJ alfanumérico passam (importante, privacidade)

- **Onde:**
  - `src/rfb_pipeline/regras.py:59`: `_RE_IDENTIFICADOR` só pega 11 ou 14 **dígitos** seguidos.
  - `src/rfb_pipeline/regras.py:163-169`: a única checagem de valor das quebras.
  - `tests/integration/test_regras_negocio.py:85-93`: o mesmo regex, mais a busca das raízes de 8 dígitos
    **sem pontuação**.
- **Evidência:**
  - **Mutação M7.** Na RN-17, troquei a quebra `situacao` por
    `rotulo || ' ' || <cnpj formatado XX.XXX.XXX/XXXX-XX>` nas linhas violadas. O relatório do CI passou a ter a
    linha `| ATIVA 14.141.414/0001-55 | 1 | 1 | 100,00 % |`, e `38 passed`.
  - **Mutação M8.** Na RN-14, `rotulo || ' ' || cnpj_raiz` passa pela guarda. Nas fixtures a RN-14 não tem violação,
    então nada é renderizado e o teste não vê. No dado real ela tem 404 violações, e as 20 primeiras linhas sairiam
    com a raiz.
  - **CNPJ alfanumérico.** O formato vale desde julho de 2026 (IN 2.119, art. 2º, parágrafo único) e a própria RN-17 o
    testa com `9000001700019Z`. Ele nunca casa com `[0-9]{14}`.
  - **Nomes.** Um nome numa coluna permitida (`situacao`, `uf`…) passa, porque a lista fechada é de nomes de coluna,
    não de valores.
- **Por que importa:** o ADR-0008 e o ADR-0020 prometem "só contagens". A guarda é a única barreira entre um erro de
  SQL numa analysis e um relatório **versionado** com identificadores. Hoje ela barra só a forma mais óbvia.
- **Correção sugerida:**
  1. Normalizar o valor antes do regex, tirando `.`, `-`, `/` e espaços.
  2. Recusar qualquer sequência de 8 ou mais caracteres `[0-9A-Z]` com pelo menos 2 dígitos. Isso pega a raiz, o CNPJ
     numérico, o alfanumérico e o CPF.
  3. Recusar analysis com mais de N linhas (por exemplo, 200), porque uma quebra por entidade explode no dado real.
     O `LIMITE_QUEBRAS` só limita a renderização.
  4. Para as quebras de domínio (`situacao`, `porte`, `uf`), validar o valor contra o seed ou a lista conhecida.
  5. No teste, aplicar a mesma normalização e incluir um caso formatado e um alfanumérico.

### RRN-02 — RN-13: as "datas futuras" são o dia seguinte ao extrato e opções legítimas para 2027 (importante, regra)

- **Onde:**
  - `transform/analyses/regras_negocio/rn_13_datas_nao_futuras.sql:17,27,47,57`: compara as datas com
    `_data_referencia`, o token do nome do arquivo, sem folga.
  - `docs/REGRAS_NEGOCIO.md:260-262`: "A opção pelo Simples pode anteceder os efeitos [CGSN 190], mas não o extrato".
  - `docs/RELATORIO_REGRAS_NEGOCIO.md:225-227`: a interpretação.
- **Evidência** (dado real, `_data_referencia` = 2026-09-12; distribuição das datas acima dela):

  | Campo | Data | Quantidade |
  |---|---|---:|
  | situação cadastral | 2026-09-13 | 386 |
  | início de atividade | 2026-09-13 | 227 |
  | opção pelo MEI | 2026-09-13 | 213 |
  | opção pelo Simples | 2026-09-13 | 212 |
  | opção pelo Simples | 2027-01-01 | 10 |

  - **Nenhuma** data passa de D+1, salvo as 10 de 1º/1/2027. Isso aponta para um corte do extrato posterior ao token,
    não para erro de digitação: erros de digitação se espalhariam por datas.
  - As 10 opções em 2027-01-01 batem com a `CAMADA_SEMANTICA.md:202-207`: pela CGSN 190/2026 e pela 194, a opção para
    2027 é feita de 1º/9 a 15/10/2026 e vale a partir de 1º/1/2027.
  - Ou seja, o campo do arquivo Simples guarda a **data de efeito**, e a opção feita em setembro de 2026 aparece com
    data futura **legítima**.
  - Não reconferi a CGSN 190/194 na fonte. Usei a A7 do projeto e o dado.
- **Por que importa:**
  - A interpretação inventa causa para 100 % dos casos.
  - No extrato de outubro, com a janela de opção encerrada em 15/10, a RN-13 vai contar como violação todas as opções
    para 2027, potencialmente centenas de milhares.
  - O alerta perde sentido justamente quando o dado está certo.
- **Correção sugerida:**
  1. Tirar a opção pelo Simples (e a do MEI, se o mesmo valer) da RN-13, ou aceitar `<= 1º de janeiro do ano
     seguinte`.
  2. Para os demais campos, comparar com `_data_referencia + 1` e documentar o corte, ou reportar a quebra "D+1" à
     parte.
  3. Reescrever a interpretação com a distribuição acima.

### RRN-03 — RN-05 e RN-14 contam como violação o que o catálogo diz não ser violação (importante, regra)

- **Onde:**
  - `transform/analyses/regras_negocio/rn_05_mei_estabelecimento_unico.sql:29`: `coalesce(emp.qtd > 1, false) as
    viola`.
  - `transform/analyses/regras_negocio/rn_14_matriz_baixada_filiais_baixadas.sql:15`: `situacao_codigo is distinct
    from 8`, inclusive para a filial NULA.
  - O catálogo diz o contrário em `docs/REGRAS_NEGOCIO.md:147-148`: o estabelecimento baixado "não contraria a lei".
    Em `:283-285`, a filial NULA é "um limite da tradução".
- **Evidência** (recontagem independente no dado real):
  - **RN-05:** 17.523.665 empresas MEI.
    - 3.247 têm mais de um estabelecimento. Em 3.214 delas, só um não está baixado (nenhuma tem todos baixados).
    - **33** têm mais de um não baixado, e 26 têm mais de um ATIVO.
    - As 3.749 filiais de MEI da RSEM conferem, mas só 38 delas não estão baixadas.
    - O resumo do relatório mostra **3.247 (0,02 %)** para a regra legal que o usuário citou. Pela leitura do próprio
      catálogo, são 33.
  - **RN-14:** 404 = 245 NULA + 78 SUSPENSA + 53 ATIVA + 28 INAPTA. O resumo mostra 404, e a interpretação corrige
    para 159.
- **Por que importa:** o resumo e a contagem "14 regras violadas" são o que o leitor vê primeiro. A regra mais citada
  pelo usuário aparece com 100 vezes mais violações do que a leitura legal sustenta. A correção fica escondida na
  quebra e no texto manual, que não acompanha o próximo mês (RRN-07).
- **Correção sugerida:**
  - **RN-05:** `viola = qtd_nao_baixados > 1`. A faixa "mais de um, no máximo um não baixado" continua como quebra
    informativa, com 0 violações. Se o projeto quiser ver a "sujeira" do cadastro, separe numa regra de coerência.
  - **RN-14:** tirar a filial NULA do universo (ou contá-la com 0 violações) e dizer isso no enunciado.

### RRN-04 — os testes não fixam universo nem quebra: 10 de 10 mutações sobrevivem (importante, teste)

- **Onde:**
  - `tests/integration/test_regras_negocio.py:71-74`: só o total de `violacoes` por regra, mais duas linhas de quebra.
  - `tests/integration/test_regras_negocio.py:196-217`: todas as injeções aplicadas **juntas**, com a checagem
    `depois > antes`.
  - Nenhum teste confere `avaliados`.
- **Evidência:** veja a [tabela das mutações](#mutações).
  - Duas mudanças de universo mexem no relatório das fixtures e passam: M1, a RN-14 com a matriz no universo
    (`avaliados` 0 → 5), e M2, a RN-05 contando só não baixados.
  - As outras 8 nem mudam o relatório. As fixtures não têm motivo nulo, raiz sem matriz, filial NULA de matriz
    baixada, opção futura nem raiz com DV inválido e outro estabelecimento. A injeção conjunta aceita qualquer aumento,
    venha de onde vier.
  - O controle (a RN-05 invertida, que é a mutação do autor) morre em `test_violacoes_por_regra_batem_com_as_fixtures`.
    Então o harness funciona; o que falta é discriminação.
- **Por que importa:** os erros de regra mais prováveis estão na borda do universo (nulos, NULA, 0 matrizes, join),
  e os testes não os veem. A RRN-02 e a RRN-03 passariam despercebidas se fossem introduzidas depois.
- **Correção sugerida:**
  1. Fixar `(avaliados, violacoes)` de toda regra nas fixtures, consultando o gold.
  2. Injetar **uma regra por vez**, numa cópia nova ou com rollback, e conferir o delta exato (+1 violação, +k
     avaliados).
  3. Acrescentar injeções na borda: filial NULA de matriz baixada (não viola), MEI com filial baixada (não viola), raiz
     sem matriz, motivo nulo num inapto, opção pelo MEI futura, DV inválido numa raiz com 2 estabelecimentos.
  4. Testar a privacidade com CNPJ formatado e alfanumérico (RRN-01).

### RRN-05 — RN-09: a interpretação atribui uma causa que o dado contradiz (menor, relatório)

- **Onde:** `docs/RELATORIO_REGRAS_NEGOCIO.md:218-219`: "Leitura provável: nova opção registrada sobre uma exclusão
  antiga."
- **Evidência:** nos 6 registros, o indicador do regime está **N**.
  - Simples: 3 com `opcao_simples = false`.
  - MEI: 3 com `opcao_mei = false`, 2 deles com `opcao_simples = true`.

  Uma reopção deixaria o indicador em S. Nenhum dos 6 é um optante atual.
- **Correção sugerida:** dizer o que o dado mostra ("exclusão anterior à opção em registros hoje excluídos do
  regime") e deixar a causa em aberto.

### RRN-06 — RN-20 e RN-06: interpretações genéricas onde o dado já mostra a concentração (menor, relatório)

- **Onde:** `docs/RELATORIO_REGRAS_NEGOCIO.md:236-238` (RN-20) e `:207-209` (RN-06). Quebra só por grupo em
  `rn_20_ente_federativo_natureza_publica.sql:15`.
- **Evidência (RN-20):**
  - 262 das 318 empresas sem ente (82 %) têm natureza **1210, Consórcio Público de Direito Público (Associação
    Pública)**. São 262 de 1.687 consórcios desse tipo (15,5 %).
  - Na sequência vêm 1031, órgão do Executivo municipal (28 de 12.004), e 1279, fundação pública de direito privado
    municipal (9 de 172).
  - O consórcio público é interfederativo e não tem um único ente responsável óbvio. "Órgão sem ente no cadastro" não
    descreve o caso principal.
- **Evidência (RN-06):** 467 das 469 empresas MEI sem opção pelo Simples têm a **exclusão do Simples já vigente**
  (≤ 12/09/2026). O leitor mais provável é o desenquadramento do MEI não registrado depois da exclusão do Simples. É
  mais preciso que "erro de dado ou defasagem".
- **Correção sugerida:**
  - RN-20: quebra por `natureza_juridica` (as linhas violadas são poucas).
  - Interpretação: citar as duas concentrações.

### RRN-07 — a interpretação manual é preservada sem o mês: no próximo mês fica texto velho sob números novos (menor, operação)

- **Onde:** `src/rfb_pipeline/regras.py:270-278` e `:356`. O texto depois do marcador é copiado sem checagem.
- **Problema:** em 2026-10, `make regras` regrava o relatório com os números de outubro e mantém frases como "3.247
  empresas MEI" ou "1.048 datas posteriores ao extrato de 12/09/2026". O `docs/OPERACAO.md` pede revisão, mas nada
  avisa que ela falta.
- **Correção sugerida:**
  1. Incluir o mês no marcador (`Interpretação de 2026-09`).
  2. Quando o mês do relatório mudar, mover a interpretação antiga para "Interpretação anterior (2026-09)", ou
     imprimir um aviso na saída do comando.

### RRN-08 — cobertura: regras verificáveis que faltam e uma regra que a fonte sustenta mais forte (sugestão, cobertura)

Medidas no dado real de 2026-09. Fontes conferidas por mim em 2026-10-13.

| Regra proposta | Fonte | Tipo | Dado real |
|---|---|---|---|
| A opção pelo Simples Nacional não é anterior a 1º/7/2007 | LC 123, art. 88: "o regime de tributação das microempresas e empresas de pequeno porte, que entra em vigor em 1º de julho de 2007" | legal | 0 violações (mínimo = 2007-07-01) |
| A opção pelo MEI não é anterior a 1º/7/2009 | início do SIMEI (LC 128/2008; **não conferida por mim**) | legal, se confirmada | 0 violações (mínimo = 2009-07-01) |
| A filial não começa atividade depois da baixa, inaptidão ou nulidade da matriz | IN 2.119, art. 21, IV: impede a inscrição de filial quando a inscrição da matriz é "inexistente, baixada, inapta ou nula" | coerência do projeto (o início de atividade não é a data de inscrição) | 1.785 filiais de matriz baixada, 279 de inapta e 363 de nula com início após o evento da matriz |
| A opção pelo Simples ou pelo MEI não antecede o início de atividade da matriz | regra do projeto | coerência do projeto | 1.648 (Simples) e 103 (MEI) |

- **RN-08 e a decisão do líder.** O líder decidiu tratar a natureza do MEI como observação. A LC 123, art. 18-A, § 1º
  (redação da LC 188/2021), diz que o MEI "seja empresário individual que se enquadre na definição do art. 966 [...]
  ou o empreendedor que exerça" certas atividades. O § 4º, III, veda o MEI que "participe de outra empresa como
  titular, sócio ou administrador".
  - **"Natureza = 213-5"** continua observação.
  - **"O MEI não é sociedade"** é legal: as 1.236 empresas MEI com natureza 2062 ou 2070 contrariam o § 1º.
  - Fica para o líder decidir se vira uma regra legal à parte.
- **Não sugiro** a regra "suspensa há 1 ano ou mais vira inapta" (IN 2.119, art. 46). É competência do auditor e tem
  exceção de 5 anos no § 1º (a RSEM já a leu como faculdade), e 64 % a 99 % das suspensas pelos principais motivos já
  passam de 1 ano.
- A RDIC-09 listava 12 grãos sem teste. RN-22 a RN-24 cobrem 11. Fica de fora `stg_bd__vizinhanca`, que é a mesma
  vizinhança da fonte, como publicada. Não é preciso acrescentar.

### RRN-09 — `rfb relatorio` passou a compilar também as 24 analyses de regras (sugestão, eficiência)

- **Onde:** `src/rfb_pipeline/relatorio.py:65`. Com `subpasta=""`, a seleção continua `path:analyses`, que inclui
  `analyses/regras_negocio/`. O `glob` só lê a raiz, então o resultado está certo, mas o `dbt compile` do estudo de
  caso compila 24 analyses a mais.
- **Correção sugerida:** na chamada do estudo de caso, `--select path:analyses --exclude path:analyses/regras_negocio`,
  ou selecionar pelo prefixo.

### RRN-10 — RN-08 rotula como "NÃO INFORMADA" um código sem descrição (sugestão, legibilidade)

- **Onde:** `transform/analyses/regras_negocio/rn_08_mei_natureza_empresario_individual.sql:8`. O
  `coalesce(codigo || ' ' || descricao, 'NÃO INFORMADA')` vira "NÃO INFORMADA" quando o **código existe** mas falta no
  domínio de naturezas.
- **Correção sugerida:** `coalesce(codigo, '—') || ' ' || coalesce(descricao, '(fora do domínio)')`.

## Mutações

Cada mutação foi aplicada, testada com
`uv run pytest -q tests/integration/test_regras_negocio.py tests/unit/test_regras.py` (`RAIZ_DADOS=.tmp/ci/dados`) e
revertida com `git checkout`. A coluna "Muda o relatório das fixtures?" compara `rfb regras --target ci` antes e
depois. Nenhuma repete as do autor (RN-05 invertida, CNPJ numa coluna, saída 1 com violação, seção removida) nem a do
líder (RN-20 num sentido só).

| # | Mutação | Muda o relatório das fixtures? | Resultado | Teste que deveria pegar |
|---|---|---|---|---|
| M1 | RN-14: sem `where matriz_filial_codigo = 2` (a matriz entra no universo) | sim: RN-14 `avaliados` 0 → 5 | **sobreviveu** (38 passed) | `avaliados` por regra (RRN-04) |
| M2 | RN-05: `por_empresa` só com `situacao_codigo != 8` | sim: quebra "um" vira "nenhum no extrato" | **sobreviveu** | quebra completa da RN-05 |
| M3 | RN-13: opção pelo MEI com folga de 1 ano | não | **sobreviveu** | injeção de opção pelo MEI futura |
| M4 | RN-10: sem `coalesce` (motivo nulo some do check) | não | **sobreviveu** | injeção de inapto com motivo nulo |
| M5 | RN-16: `matrizes > 1` (raiz sem matriz deixa de violar) | não | **sobreviveu** | injeção de raiz só com filial |
| M6 | RN-17: join por `cnpj_raiz` em vez do CNPJ completo | não | **sobreviveu** | DV inválido numa raiz com 2 estabelecimentos |
| M7 | RN-17: CNPJ **formatado** na quebra das linhas violadas | sim: `ATIVA 14.141.414/0001-55` no relatório | **sobreviveu** | privacidade normalizada (RRN-01) |
| M8 | RN-14: `rotulo \|\| ' ' \|\| cnpj_raiz` na quebra (8 dígitos) | não (RN-14 sem violação nas fixtures; no dado real vazaria) | **sobreviveu** | guarda contra 8+ dígitos (RRN-01) |
| M9 | RN-11: universo `situacao_codigo in (3, 4, 8)` (a NULA sai) | não | **sobreviveu** | injeção de NULA sem data |
| M10 | RN-03: só o ATIVO viola | não | **sobreviveu** | injeção num estabelecimento não ativo |
| C | controle: RN-05 com `qtd <= 1` | sim | morta (`test_violacoes_por_regra_batem_com_as_fixtures`) | — |

Sobreviveram 10 de 10. M7 e M8 são vazamentos de identificador que a guarda e o teste deixam passar.

## Regras conferidas nas fontes

Conferidas em 2026-10-13, com o texto lido na fonte:

- o leiaute `cnpj-metadados.pdf`, baixado de gov.br;
- a LC 123, no texto compilado do Planalto;
- a IN RFB 2.119/2022, no texto multivigente do Sijut, lido no navegador.

| # | Regra (afirmação do catálogo) | Fonte | Resultado |
|---|---|---|---|
| 1 | RN-05: MEI "que possua mais de um estabelecimento" não pode optar | LC 123, art. 18-A, § 4º, II | confere ("II - que possua mais de um estabelecimento") |
| 2 | RN-06: MEI é "optante pelo Simples Nacional" | LC 123, art. 18-A, § 1º (redação da LC 188/2021) | confere |
| 3 | RN-07: "O MEI é modalidade de microempresa" | LC 123, art. 18-E, § 3º (incluído pela LC 147/2014) | confere |
| 4 | RN-07: códigos de porte 00, 01, 03, 05 | leiaute, Empresas | confere |
| 5 | RN-08: a natureza do MEI é só observação | LC 123, art. 18-A, § 1º e § 4º, III | **a fonte é mais forte**: o MEI é empresário individual ou empreendedor, nunca sociedade (RRN-08) |
| 6 | RN-10/RN-11: hipóteses de baixa (motivos 01 a 04 = extinção; 05 = falência) e efeitos desde o evento | IN 2.119, art. 24, caput, I, a a d, II e § 1º | confere |
| 7 | RN-14: "A baixa da inscrição do estabelecimento matriz no CNPJ implica baixa de todas as inscrições dos estabelecimentos filiais da entidade" | IN 2.119, art. 24, § 2º | confere, literal |
| 8 | RN-14: a nulidade vale desde o início | IN 2.119, art. 34, parágrafo único | confere com nuance: "a partir do termo inicial de vigência do **ato cadastral** declarado nulo", que pode não ser a inscrição |
| 9 | RN-14/RN-16: filial pode virar matriz; os entes se inscrevem "na condição de estabelecimento matriz" | IN 2.119, art. 4º, §§ 1º e 3º | confere |
| 10 | RN-17: formato alfanumérico de 14 posições | IN 2.119, art. 2º, parágrafo único (incluído pela IN 2.229/2024) | confere (o FAQ do módulo 11 não foi reconferido) |
| 11 | RN-20: ente federativo só no grupo 1XXX, em branco nas demais | leiaute, Empresas, e nota 3 | confere, literal |
| 12 | RN-01/RN-02: CNAE fiscal principal (singular); secundárias "separadas por vírgula" | leiaute, Estabelecimentos, e nota 5 | confere |
| 13 | RN-10 a RN-15: campos "data do evento da situação cadastral", "código do motivo", situação especial e data; o leiaute não diz que são obrigatórios | leiaute, Estabelecimentos | confere; por isso "coerência do projeto" está correto em RN-10, RN-11, RN-12, RN-13 e RN-15 |

As classificações "coerência do projeto" e "estrutural" (RN-03, RN-04, RN-09, RN-12, RN-13, RN-15, RN-16, RN-21,
RN-22 a RN-24) estão justificadas no catálogo, com "Não confirmado" explícito. A RN-18 (estrutural, com o leiaute
como apoio) é razoável.

## Reexecuções no dado real

Ambiente: cópia do warehouse de 2026-09 (`_data_referencia` 2026-09-12). Todas as contagens são de consulta própria,
não do relatório.

| Regra | Como reexecutei | Resultado | Bate com o relatório? |
|---|---|---|---|
| todas | `rfb regras --target dev --saida <scratch>` | 72,4 s, saída 0, "24 regras, 14 violadas"; diff vazio acima da "Interpretação" | sim |
| RN-03/RN-04 (maior volume) | `string_split` do texto bruto `stg_rfb__estabelecimentos.cnaes_secundarios`, sem a lista do intermediate | 34.670.077 estabelecimentos, 125.425.117 ocorrências, 3.310 repetem o principal, 3.488 com duplicata | sim |
| RN-05 | contagem por raiz, independente | 17.523.665 / 3.247; 3.214 com um só não baixado; 33 com mais de um não baixado (26 com mais de um ativo); 3.749 filiais de MEI, 38 não baixadas | sim (leitura: RRN-03) |
| RN-06 | `opcao_mei and opcao_simples is distinct from true` | 469, todos `false`; 467 com exclusão do Simples ≤ 12/09 | sim (RRN-06) |
| RN-09 | por indicador do regime | 6 = 3 Simples + 3 MEI, todos com o indicador do regime em N | sim (interpretação: RRN-05) |
| RN-10 | ATIVO × motivo | 1 ATIVO com motivo 24; nenhum não ativo com 00 ou nulo | sim |
| RN-12 | violações por situação e ano; datas sentinela | 1.058; 1 `dat_situacao` e 4 `dat_inicio_atividade` antes de 1900 em todo o cadastro, sem peso | sim |
| RN-13 | distribuição das datas futuras | 1.038 em 2026-09-13 e 10 opções em 2027-01-01 | sim (leitura: RRN-02) |
| RN-14 | recontagem com a data da baixa da matriz | 404 = 245 NULA + 78 SUSPENSA + 53 ATIVA + 28 INAPTA | sim (RRN-03) |
| RN-16 | matrizes por raiz | 70.085.590 com 1 e 1 com 2 | sim |
| RN-20 | grupo × ente, por natureza | 318 no grupo 1, 262 deles na natureza 1210; 0 fora do grupo 1 | sim (RRN-06) |
| RN-24 | vizinhança: linhas × chaves distintas | 522.822 − 522.803 = 19 | sim |

Privacidade do relatório versionado: nenhuma sequência de 11 ou 14 dígitos, nenhuma raiz e nenhum nome. As quebras são
situação, porte, natureza (código e descrição), campo, regime, tabela e faixas.
