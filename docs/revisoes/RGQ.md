# RGQ — Revisão independente das golden queries e do guia para agente (v1.4.1)

Revisor: agente RGQ (Traycer, Claude Opus), 2026-10-15. Não sou autor de nenhum dos commits revisados.

- **Alvo:** branch `docs/retro-custos-v1.4.0` (PR #8), `git diff fdf8573..287a001`: os 5 commits do lote GQ e o
  `dfb831a` (`--parcial` no script de custos).
- **O que não toquei:** não alterei código, YAML, docs nem testes. O único arquivo deste commit é esta revisão.
- **Mutações:** aplicadas por script e revertidas com `git checkout -- <arquivo>`. `git status --short` ficou vazio
  no fim.
- **Dado real:** nada foi gravado em `dados/`. Só li o gold Parquet com DuckDB em memória, por views
  `main.<tabela>` sobre `read_parquet`, o que também testa se o SQL do catálogo roda fora do dbt. O gold real é da
  v1.3, sem IBGE, então as perguntas de CEMPRE, renda e REGIC só rodaram nas fixtures.
- **Gates:**
  - `caffeinate -i make ci`: verde em 5 min 16 s; o `pytest tests/integration` passou com 406 testes.
  - `uvx pre-commit run --all-files`: verde.
  - `make golden`: idempotente, `git status` vazio depois.
  - `make semantica`: verde.

## Veredito

**APROVÁVEL COMO MINOR, COM RESSALVAS.** O lote é só aditivo, as 89 golden queries respondem nas fixtures o que o
cabeçalho promete, e no teste de uso real o guia levou ao SQL certo em 8 de 10 perguntas livres, sem nenhuma resposta
errada. Mas o contrato do pedido é um agente que só recebe o guia, o catálogo e acesso somente leitura ao banco. Com
esse contrato, **RGQ-01** (alta) e **RGQ-02** (média) devem ser corrigidos **antes** de entregar o material ao agente
do outro projeto. Não bloqueiam o merge da v1.4.1. Há ainda dois achados médios e seis baixos.

O que está bem:

- **Pedido atendido.**
  - A matriz tem 22 conceitos × 7 camadas.
  - Cada uma das 154 células tem golden query ou motivo: 72 com query e 82 com motivo. O brief do RGQ fala em 65
    motivos, mas o catálogo tem 82.
  - O catálogo é gerado, e o CI confere que está em dia.
  - O guia cobre o que uma documentação para pessoas não cobria: regra de camada, grão, glossário de ambiguidades,
    armadilhas, privacidade, procedimento e exemplos de ponta a ponta.
- **Corretude.** Conferi 20 golden queries contra os modelos e o YAML; detalhe em
  [Conferências](#golden-queries-conferidas-contra-o-modelo). Não achei query que responda errado à própria pergunta.
  - As armadilhas centrais estão certas e o SQL as evita de fato:
    - fotografia mensal;
    - capital social só das matrizes;
    - membros `-1`/`-2`;
    - sigilo do CEMPRE nunca imputado;
    - CEMPRE sem MEI;
    - "Outros" da REGIC;
    - classe × subclasse;
    - encerramento × baixa;
    - média ponderada da renda;
    - `MAX(mes)` depois do filtro (RSEM-01).
- **Números do guia.** Recontei no gold real, por SQL próprio, todos os números de dado real que pude, e todos batem:
  - Fundão 0/5;
  - Água Branca 1.704/497, 1.280/452 e 4.017/1.505;
  - sobrevivência de tintas no ES: 686 elegíveis, 83,38 % e 78,74 % com 588;
  - ~73,4 milhões de estabelecimentos e ~28,3 milhões ativos.
- **Portabilidade.** O SQL do catálogo (`main.x`, `${RAIZ_DADOS}`) rodou sem o dbt sobre views em memória do gold
  real. Os três blocos SQL dos exemplos do guia rodam nas fixtures.
- **Compatibilidade.**
  - A exclusão de `analyses/golden` em `relatorio.compilar_analises` só vale sem subpasta; `rfb regras` usa a
    subpasta `regras_negocio`.
  - O relatório do caso, o dicionário (verificado no CI) e o `rfb regras` não mudaram.
  - Os testes das golden queries custam **38 s** medidos (o brief estimava ~40 s). É aceitável: 20 deles são
    `mf query` reais.
  - O `dfb831a` está correto. Sem `--parcial`, o script falha listando o que falta. Com `--parcial`, segue sem os
    transcripts que faltam e avisa no topo. Nesta máquina rodou com saída 0.
- **Testes fortes onde importa.** De 11 mutações, 5 morreram, e foram exatamente as de regra de negócio:
  - o "Outros";
  - encerramento × baixa;
  - capital sem matriz;
  - o RSEM-01;
  - CNPJ em texto.

  As 6 que sobreviveram estão em RGQ-04, RGQ-07 e RGQ-08.

O que pesa:

1. **RGQ-01, alta.** A camada que o guia manda preferir, a semântica (`mf query`), não roda no ambiente que o
   próprio guia promete ao agente. Ela exige o repositório, o `uv` e o projeto dbt, e abre o warehouse em modo de
   **escrita**: confirmei que ela falha com `Could not set lock` quando há uma conexão `read_only` aberta. Isso
   contradiz a regra dura "NUNCA abra em modo de escrita" (§3).
2. **RGQ-02, média.** O agente não tem como descobrir:
   - as métricas e dimensões da semântica além das que aparecem nos exemplos;
   - as colunas das relações (o guia não manda rodar `describe`).
3. **RGQ-03, média.** Várias golden queries usam "empresas" na pergunta e contam **estabelecimentos**, sem uma
   armadilha que diga isso. Como o agente recupera as queries por `perguntas`, aprende a misturar os dois, que é
   justamente o que o glossário proíbe.
4. **RGQ-04, média.** A guarda de privacidade do CI é só por nome de coluna e por valor de texto. Um CNPJ básico como
   inteiro e o nome do empresário com outro alias passam. Para o agente em execução, não há guarda nenhuma além do
   texto do guia.

## Teste de uso real: 10 perguntas livres

Método: no papel do agente, li **só** o guia e o `catalogo.json` antes de escrever cada SQL, sem abrir modelo,
YAML nem dicionário. Executei nas fixtures (`.tmp/ci/dados/warehouse.duckdb`, `read_only=True`). Quando as fixtures
não têm o recorte (padaria, transporte, restaurante, ano 2025), executei no gold real da v1.3, também somente
leitura. Script: `scratchpad/perguntas.py` da sessão de revisão.

| # | Pergunta | Golden query de partida | Resultado | Certo? | O que faltou ou atrapalhou |
|---|---|---|---|---|---|
| 1 | "Quantas padarias abriram em Vitória no ano passado?" | `gq_core__cnae_principal__02` (CNAE pela descrição), `gq_core__municipio_geografia__02` (homônimo), `gq_core__data_calendario__02` (aberturas por `dim_data`) | Real: em 2025, 137 aberturas (1091102: 107; 4721102: 30), 95 ainda ativas. "Ano passado" = 2025, pela data de referência (armadilha 2) | **parcial** | A busca `%padaria%` devolve três subclasses. O guia manda mostrar as opções, mas a golden query não traz a contagem por subclasse. Sem ela, o agente que escolhe pelo nome, "Padaria e confeitaria" (4721101/4721102), conta **30 em vez de 137**: a maioria das padarias está em 1091102 (fabricação), e 4721101 é obsoleta (4 estabelecimentos no Brasil). RGQ-06 |
| 2 | "Qual o porte mais comum das empresas de transporte no ES?" | `gq_core__porte__01` + variação "Só empresas: `eh_matriz`"; seção H achada pela descrição | Real: MICRO 48.358, PEQUENA 1.287, DEMAIS 716 matrizes ativas | **certo** | O guia diz que o porte é da empresa, e a variação dá o `eh_matriz`. Declarei a escolha de seção H inteira (inclui armazenagem e correio) × divisões 49–51 |
| 3 | "Onde os moradores de Linhares compram móveis?" | `gq_core__regic_polo_compras__01`, filtro `tema = 'moveis_eletro'` | Fixtures: Vitória 88,3 %, "Outros" 11,7 % | **certo** | Nada. As armadilhas do % entre os destinos de fora e do "Outros" estão na própria golden query e no guia |
| 4 | "Quanto se paga de salário no comércio de tintas na Serra?" | `gq_analytics__cempre_setor__01` (variação do salário médio) | Fixtures: CEMPRE 2024, R$ 2.928,60/mês (6.358 mil ÷ 167 assalariados ÷ 13) | **parcial** | "Salário" não está no glossário: só achei a fórmula numa `variacao` de outra pergunta. Nem a golden query nem o guia avisam que: (a) `tem_sigilo` é da linha inteira (qualquer variável com X); (b) numa agregação, salário e assalariados precisam vir das mesmas células. RGQ-05 |
| 5 | "Me passa o CPF do dono da empresa X" | — (§7) | Recusa: a base não tem sócios, e CPF é dado pessoal. Ofereci a situação cadastral, o CNAE e o porte do CNPJ, se o usuário o tiver | **certo** | Nada. A regra e o exemplo 5 cobrem o caso |
| 6 | "Empresas que fecharam em 2025 por cidade" | `gq_core__situacao_cadastral__02` + variação por município | Real: São Paulo 262.559 encerramentos, dos quais 248.875 baixas; Rio 103.238 (102.345); BH 60.725… | **certo** | Segui o glossário: mostrei baixa × outras e declarei que são estabelecimentos. A pergunta da golden query de partida ("Quantas empresas fecharam por ano?") não avisa que conta estabelecimentos. RGQ-03 |
| 7 | "Qual a taxa de sobrevivência de restaurantes?" | `gq_analytics__sobrevivencia_coorte__01` sem filtro de UF; CNAE 5611201 pela descrição | Real: 89,8 % em 1 ano, 74,5 % em 3 anos, 68,9 % em 5 anos (998.718 elegíveis em 3 anos) | **certo** | A semântica seria a preferida, mas não roda no ambiente do agente (RGQ-01); o mart dá o mesmo número |
| 8 | "Quantos MEI ativos há na Serra hoje, e quanto mudou do mês passado?" | `gq_core__data_calendario__01` (resumo) + `gq_semantica__simples_mei__01` | Fixtures: 2026-09 = 1 MEI ativo; 2026-08 = nenhum. SQL e `mf query` concordam. Real: só existe 2026-09, então não há variação | **certo** | O SQL no resumo saiu certo. O `mf query` só rodou porque eu tinha o repositório; com uma conexão `read_only` aberta, ele falha (RGQ-01). O nome das dimensões (`municipio__nome_municipio`) só aparece nos exemplos (RGQ-02) |
| 9 | "Qual a renda mediana do ES?" | `gq_core__renda__02` | Respondi que não há mediana da UF (medianas não se agregam) e dei a média ponderada, R$ 2.162,57, e a faixa das medianas municipais, R$ 1.040 a R$ 1.750 (fixtures, Censo 2022) | **certo** | Nada. A armadilha "não há mediana da UF" é exatamente o caso |
| 10 | "Quantos ativos havia no ES em agosto de 2026, por porte?" | `gq_core__data_calendario__01` (resumo, filtro de mês) | Fixtures: DEMAIS 2, MICRO 1, N/A 1, NÃO INFORMADO 0, PEQUENA 3 (igual ao `mf query`). Real: vazio, porque o warehouse real só tem 2026-09 | **certo** | O passo 6 ("vazio é zero ou filtro errado?") e a tabela CI × real (meses ingeridos) levam o agente a dizer que agosto não foi ingerido |

**Placar: 8 certas, 2 parciais, 0 erradas.** O guia funciona onde tem armadilha explícita. Ele falha onde o agente
precisa descobrir algo que não está escrito:

- o mapa de CNAE com volume (P1);
- um termo fora do glossário (P4);
- a interface da semântica (P7, P8).

## Achados

### RGQ-01 — a semântica, camada preferida, não roda no ambiente prometido ao agente e abre o banco para escrita (alta, guia e catálogo)

**Evidência.**

- **Ambiente prometido.** O guia (§0 e ADR-0023) promete ao agente "só três coisas": o guia, o catálogo e acesso
  somente leitura ao DuckDB ou ao MotherDuck.
- **O que o guia manda.**
  - §2: "Se a semântica responde, **prefira-a**".
  - O fluxograma manda a métrica padrão para `mf query`.
  - 20 golden queries do catálogo são só comandos `uv run mf query ...`, sem SQL.
- **O que o `mf query` exige.** Precisa do checkout do repositório, do `uv`, do projeto dbt (`transform/`,
  `DBT_PROFILES_DIR`) e de `target/semantic_manifest.json`.
- **O teste.** Abri `duckdb.connect(".../warehouse.duckdb", read_only=True)` num processo e, em seguida, rodei
  `uv run mf query --metrics qtd_ativos --group-by metric_time__month`:

  ```text
  ERROR: IO Error: Could not set lock on file ".../.tmp/ci/dados/warehouse.duckdb": Conflicting lock is held in
  .../python3.12 (PID 47087) ... you would be able to open this database in read-only mode
  ```

- **Por que falha.** O perfil `transform/profiles.yml` abre o arquivo em leitura e escrita. Isso viola a regra dura
  do §3 ("**NUNCA** abra em modo de escrita, nem rode `dbt`"). Também impede o agente de usar a semântica e o SQL na
  mesma sessão: em DuckDB, um processo com escrita exclui todos os outros.
- **No MotherDuck.** Lá a semântica não roda, e o guia manda "traduzir a métrica para SQL", sem o SQL equivalente.

**Por que importa.** É o caminho padrão do procedimento. Na prática, o agente vai falhar ou, para contornar a
falha, abrir o banco com escrita.

**Correção sugerida.**

- No gerador, adicionar a cada golden query semântica um campo `sql` com o SQL do `mf query --explain`,
  normalizado como o das outras (`main.x`).
- No CI, executar esse SQL somente leitura e comparar com a resposta esperada, como já é feito com as golden
  queries SQL.
- No guia, dizer que o agente roda esse SQL, adaptando-o pelas `variacoes`, e que `mf query` é para quem tem o
  repositório.
- Se o `mf query` continuar no guia, usar um perfil de consulta somente leitura. Por exemplo,
  `config_options: {access_mode: READ_ONLY}` no dbt-duckdb, a testar.

### RGQ-02 — o agente não tem a lista de métricas, dimensões nem colunas (média, guia e catálogo)

**Evidência.**

- O guia cita algumas métricas no glossário: `qtd_ativos`, `qtd_matrizes`, `aberturas`, `taxa_sobrevivencia_*`…
- Os nomes das dimensões do MetricFlow (`municipio__nome_municipio`, `cnae__codigo_subclasse`,
  `coorte_sobrevivencia__uf`, `estabelecimento__eh_matriz`…) só aparecem dentro dos exemplos.
- Não há lista de métricas, com o tipo de cada uma (fotografia × evento × coorte) e as dimensões que aceita.
- O catálogo também não traz o esquema das relações:
  - `colunas_chave` é parcial;
  - colunas úteis como `populacao_censo_2022`, `densidade_hab_km2`, `pessoal_assalariado_cempre` e
    `salarios_mil_reais` só se descobrem por acaso numa `variacao` ou com `describe`;
  - o procedimento do §8 não manda rodar `describe`.
- Em P4 e P8 dependi de nomes vistos em exemplos de outras perguntas.

**Correção sugerida.** No catálogo, uma seção gerada com:

- `relacoes`: colunas, tipo e descrição curta, já disponíveis no `catalog.json` do dbt que o `make dicionario` usa;
- `metricas` e `dimensoes`: tiradas do `semantic_manifest.json`, com a natureza de cada métrica.

E no §8 do guia, um passo "confira as colunas com `describe main.<relação>`".

### RGQ-03 — perguntas das golden queries dizem "empresas" e contam estabelecimentos, sem armadilha (média, golden queries)

**Evidência.** As golden queries abaixo têm "empresa(s)" numa das `perguntas`, contam estabelecimentos (sem
`eh_matriz` nem `qtd_matrizes`) e não têm armadilha nem variação sobre isso:

- `gq_core__dinamica_mercado__01` ("Quantas empresas abriram e quantas fecharam por ano?");
- `gq_core__cnae_principal__01` ("Qual ramo tem mais empresas ativas");
- `gq_core__data_calendario__02` ("Em que dia da semana mais se abre empresa?");
- `gq_semantica__dinamica_mercado__01` e `__02`;
- `gq_semantica__cnae_principal__01`;
- `gq_semantica__renda__01`;
- `gq_semantica__sobrevivencia_coorte__01`.

Outras tratam o caso bem: `gq_core__situacao_cadastral__01` ("a situação da empresa é a da matriz"),
`gq_core__simples_mei__02` (variação "Só empresas") e `gq_core__municipio_geografia__02` (exemplo 3 do guia).

**Por que importa.** O §8 manda partir da golden query mais próxima pela `pergunta`. O agente que recupera "Quantas
empresas abriram" recebe um SQL de estabelecimentos sem nenhum aviso, contra o glossário: "o usuário quer empresas
ou estabelecimentos?". Em P6 só acertei porque li o glossário à parte.

**Correção sugerida.**

- Nessas 8 golden queries, uma armadilha padrão: "conta estabelecimentos; para empresas filtre `eh_matriz` (SQL) ou
  use `qtd_matrizes`; declare a escolha".
- Como alternativa, reescrever a pergunta com "estabelecimentos" e deixar "empresas" como segunda formulação, com
  a armadilha.

### RGQ-04 — a guarda de privacidade só olha nome de coluna e valor de texto (média, testes e guia)

**Evidência.** Mutações M1 e M2 (ver [Mutações](#mutações)):

- `max(left(cnpj_completo, 8)::bigint) as maior_raiz` passa no `test_golden_query_sql_nao_expoe_pessoa`. A coluna não
  tem nome proibido e o valor é inteiro, mas `_sem_identificador` só examina `str`.
- `min(nome) as titular` em `bh_empresas` também passa. O nome é de empresário individual nas fixtures ("PINTE BEM
  ***.***.***-**", "TINTAS FUNDÃO", natureza 2135), e a máscara tira os dígitos, então a guarda de valor não vê
  nada.
- O CNPJ como texto (M3) morre.

**Por que importa.** Hoje nenhuma golden query vaza nada. A guarda existe para pegar a próxima que vazar, e o caminho
mais natural de vazamento, um alias, passa. Para o agente em execução, a única proteção é o texto do §7: não há
guarda que ele possa chamar antes de responder.

**Correção sugerida.**

- Nos testes:
  - examinar também valores numéricos com 8 ou mais dígitos;
  - recusar no SQL **fonte** a seleção de `nome`, `cnpj_completo` ou `cnpj_raiz` fora de
    `count(distinct …)`/`count(…)`. Uma regex no corpo do SQL, ou, melhor, a linhagem de colunas do `dbt compile`
    (manifest).
- No guia, oferecer ao agente a mesma guarda: `traz_identificador` + `colunas_proibidas` como passo 6 do
  procedimento, "aplique sobre o resultado antes de responder".

### RGQ-05 — salário não está no glossário, e o sigilo por linha não é explicado para salários (baixa, guia)

**Evidência.**

- P4 ("quanto se paga de salário") só teve resposta porque achei, numa `variacao` de `gq_analytics__cempre_setor__01`,
  a fórmula `salarios_mil_reais * 1000 / pessoal_assalariado_cempre / 13`.
- O glossário não tem "salário", "remuneração" nem "quanto paga". A linha "quanta gente trabalha" diz que "a RFB
  não tem número de empregados", mas nada sobre salário.
- `stg_ibge__cempre_municipio_classe` marca `tem_sigilo` se **qualquer** variável vier `X`. Numa linha com salário em
  sigilo e assalariados publicados, a fórmula dá NULL, o que está certo para o município. Já numa agregação por UF
  (`sum(salarios) / sum(assalariados)`), as células com salário NULL e assalariados presentes inflam o denominador, e
  nada avisa disso.

**Correção sugerida.**

- Uma linha no glossário: "salário, remuneração → CEMPRE `salarios_mil_reais` e `pessoal_assalariado_cempre`,
  salário médio mensal aproximado; ano do CEMPRE; sigilo".
- Uma golden query `gq_analytics__cempre_setor__03` de salário médio por UF que só soma as células em que os dois
  campos estão presentes, com a armadilha correspondente.

### RGQ-06 — achar o CNAE pela descrição sem volume leva à subclasse errada (baixa, golden queries)

**Evidência.** P1 no gold real. `%padaria%` devolve:

| Subclasse | Descrição | Volume |
|---|---|---|
| 1091102 | fabricação de produtos de padaria e confeitaria | 457.872 estabelecimentos no Brasil |
| 4721101 | padaria e confeitaria, produção própria | **4** estabelecimentos (subclasse obsoleta, ainda em `dim_cnae`) |
| 4721102 | padaria e confeitaria, revenda | 289.460 |

Em Vitória, em 2025: 1091102 = 107 aberturas, 4721102 = 30. O agente que segue o nome ("Padaria e confeitaria")
responde 30 em vez de 137. O guia manda "mostrar as opções" (§5, CNAE), mas `gq_core__cnae_principal__02` não traz a
contagem que mostraria qual opção importa.

**Correção sugerida.**

- Em `gq_core__cnae_principal__02`, acrescentar `count` de estabelecimentos e de ativos por subclasse (`left join`
  na fato).
- Uma armadilha: "a atividade popular pode estar em fabricação (padaria = 1091102); subclasse com quase nenhum
  estabelecimento costuma ser obsoleta".

### RGQ-07 — o que é escrito à mão no guia e nas armadilhas não é verificado (baixa, testes)

**Evidência.** Mutações:

- **M8.** Uma armadilha de `gq_core__porte__01` citando `gq_core__porte__09`, que não existe, sobrevive mesmo
  depois de `make golden`.
- **M9.** Uma coluna inexistente (`cnae.codigo_cnae`) no SQL do exemplo 1 do guia sobrevive.
- **M10.** O guia citando `gq_core__ativos__01`, que não existe, fora do bloco gerado, sobrevive.

O `--verificar` só compara o bloco gerado. O `_RE_ID_CITADO` só valida os motivos da matriz. Hoje está tudo
consistente: rodei os 3 blocos SQL do guia nas fixtures e verifiquei os ids citados no guia e nos cabeçalhos.

**Correção sugerida.** Num teste:

- extrair os blocos ` ```sql ` do guia e executá-los nas fixtures, somente leitura;
- validar com `_RE_ID_CITADO` os ids citados no guia inteiro e nas `armadilhas`/`variacoes` de cada cabeçalho.

### RGQ-08 — lacuna de cobertura: perfil do município (população, PIB, Censo) sem conceito nem golden query (baixa, cobertura)

**Evidência.**

- `dim_municipio` tem `populacao` (estimativa, `ano_populacao` 2024), `populacao_censo_2022`, `pib`/`ano_pib`,
  `domicilios_2022`, `area_km2`, `densidade_hab_km2`, `taxa_alfabetizacao`, `idade_mediana` e
  `indice_envelhecimento`.
- Nenhum conceito da matriz trata disso:
  - `populacao` só aparece dentro dos marts de densidade;
  - `pib` só aparece na golden query de linhagem do staging.
- Há armadilha real sem registro: **duas populações** (estimativa de 2024 × Censo 2022) e PIB per capita, que não é
  coluna.
- "Qual a população de Serra?" e "PIB per capita de Linhares?" são perguntas livres prováveis.

Também sobre cobertura, a mutação **M4** (tirar `mun.sigla_uf = 'ES'` de `gq_core__empresa_estabelecimento__02`)
sobrevive: Fundão é único nas fixtures. O filtro de homônimo só é exercitado em Água Branca.

**Correção sugerida.**

- Um conceito `perfil_municipio`, com golden queries no core e a armadilha das duas populações e do ano de cada
  fonte. Ou declarar os motivos.
- Nas fixtures, um homônimo de um dos municípios do caso, para matar M4.

### RGQ-09 — MotherDuck: a sintaxe confere, mas "token de leitura" é vago (baixa, guia)

**Evidência.** Conferi na documentação oficial do MotherDuck (páginas "Authenticating to MotherDuck" e "ATTACH"):

- **Confere:**
  - `ATTACH 'md:<banco>'` é válido;
  - a conexão alternativa é `duckdb "md:<banco>"` / `duckdb.connect("md:<banco>")`;
  - o token vem do ambiente (a doc mostra `motherduck_token`; o projeto já usa `MOTHERDUCK_TOKEN` com sucesso na
    publicação, ADR-0016);
  - o guia diz certo que, depois do `ATTACH`, o SQL `main.<tabela>` exige `USE <banco>`.
- **É vago:**
  - não há opção `READ_ONLY` no `ATTACH 'md:'`;
  - o token somente leitura do MotherDuck se chama **Read Scaling token**; o comum é de leitura e escrita;
  - "Use um token de leitura" não diz qual criar;
  - o `read_only=True` do §3 não se aplica ao `md:`.

**Correção sugerida.** No guia:

- "crie um *Read Scaling token*";
- "conecte com `duckdb.connect('md:<banco>')` (ou `ATTACH 'md:<banco>'; USE <banco>;`)";
- "o modo somente leitura vem do token, não da conexão".

### RGQ-10 — pequenas inconsistências nos cabeçalhos (baixa, golden queries)

- `gq_core__data_calendario__02`: a `intencao` diz "Aberturas por mês do ano corrente do extrato", mas o SQL e a
  pergunta usam `ano >= 2022`.
- `gq_core__regras_qualidade__01` conta `sk_data_inicio_atividade = -2`, mas não `sk_data_situacao = -2` (data da
  situação anterior a 1900, que a fato também gera).
- `gq_raw__cempre_setor__01`: a resposta esperada é cheia de `-`, e as armadilhas só explicam o `X`. No SIDRA, `-` é
  zero absoluto. Vale uma linha, já que é a camada de auditoria do "o que o IBGE publicou".

## Mutações

Aplicadas pelo script `scratchpad/mutacoes.py` da sessão, cada uma seguida de `pytest
tests/integration/test_golden_queries.py -k <seleção>` com `RAIZ_DADOS=.tmp/ci/dados` e revertida com `git checkout`.

| # | Mutação | Resultado | Por quê |
|---|---|---|---|
| M1 | `gq_core__empresa_estabelecimento__01` devolve `max(left(cnpj_completo, 8)::bigint) as maior_raiz` | **sobrevive** (`nao_expoe_pessoa`) | nome de coluna livre; a guarda de valor só examina texto (RGQ-04) |
| M2 | `gq_original__modelos_originais__01` devolve `min(nome) as titular` | **sobrevive** (`nao_expoe_pessoa`) | alias fora da lista; nome mascarado sem dígitos (RGQ-04) |
| M3 | idem M1, com `min(cnpj_completo) as exemplo` (texto) | morta | `traz_identificador` pega os 14 dígitos |
| M4 | `gq_core__empresa_estabelecimento__02` sem `and mun.sigla_uf = 'ES'` | **sobrevive** | Fundão é único nas fixtures (RGQ-08) |
| M5 | `gq_core__regic_polo_compras__01` sem o `case` do "Outros" | morta | vira "NÃO INFORMADO" |
| M6 | `gq_core__dinamica_mercado__01`: encerramento = só baixa | morta | a inapta de 2023 some |
| M7 | `gq_core__capital_social__01` sem `where fct.eh_matriz` | morta | o capital das filiais entra em dobro |
| M8 | armadilha de `gq_core__porte__01` cita `gq_core__porte__09` (com `make golden`) | **sobrevive** | ids citados nos cabeçalhos não são validados (RGQ-07) |
| M9 | exemplo 1 do guia com `cnae.codigo_cnae` (coluna inexistente) | **sobrevive** | o SQL dos exemplos não é executado (RGQ-07) |
| M10 | guia cita `gq_core__ativos__01`, inexistente, fora do bloco gerado | **sobrevive** | `--verificar` só compara o bloco gerado (RGQ-07) |
| M11 | `gq_semantica__situacao_cadastral__02` sem o filtro de mês | morta | devolve a fotografia de 2026-08 (RSEM-01) |

5 de 11 morreram. As 5 regras de negócio mutadas morreram. As que sobreviveram são de privacidade por alias (M1,
M2), de fixture (M4) e de texto escrito à mão (M8–M10).

## Conferências

### Golden queries conferidas contra o modelo

Li o SQL dos modelos (`fct_estabelecimentos`, `mart_dinamica_mercado`, `mart_sobrevivencia_coorte`,
`mart_emprego_setor_municipio`, `mart_concorrencia_municipio`, `stg_ibge__cempre_municipio_classe`,
`int_municipios__perfil_ibge`) e o YAML das métricas (`qtd_ativos_mei` com `non_additive_dimension` em `mes`). Contra
eles, conferi:

| Golden query | O que conferi | Ok? |
|---|---|---|
| `gq_core__dinamica_mercado__01` | mesma regra de `mart_dinamica_mercado` (abertura por `sk_data_inicio_atividade`, encerramento = `not eh_ativa` por `sk_data_situacao`, `ano is not null`) + baixa = situação 8 | sim |
| `gq_analytics__dinamica_mercado__01` | `municipio` com acento (`dim_municipio.nome_municipio`) | sim |
| `gq_analytics__sobrevivencia_coorte__01`/`__02` | soma os sobreviventes e os elegíveis antes de dividir; elegível = `ano_coorte + N` terminado até a data de referência; sobrevive = ativo ou situação depois do aniversário | sim |
| `gq_semantica__sobrevivencia_coorte__02` | igual ao mart; no real, 686 elegíveis, 83,38 % | sim |
| `gq_core__capital_social__01` | `eh_matriz`; média = soma ÷ matrizes | sim |
| `gq_core__empresa_estabelecimento__01`/`__02` | `count(*)` = estabelecimentos; `eh_matriz` = empresas | sim |
| `gq_core__simples_mei__01`/`__02` | `opcao_mei`, nunca natureza nem porte | sim |
| `gq_core__situacao_cadastral__02` | `not eh_ativa` × `sk_data_situacao`; quebra BAIXADA × outras | sim |
| `gq_core__regic_polo_compras__01` | `eh_outros` e `-1`; `posto nulls last` | sim |
| `gq_analytics__regic_polo_compras__01` | `ativos_no_polo` NULL = sem polo | sim |
| `gq_core__renda__02` | ponderada por `moradores_renda_2022` (a coluna vem de `int_municipios__perfil_ibge`) | sim |
| `gq_analytics__cempre_setor__01`/`__02` | classe de 5 dígitos; `ativos_rfb_sem_mei`; sigilo NULL e `tem_sigilo`; soma de unidades completa (706 nunca vem com X no raw das fixtures) | sim (ressalva da linha toda em RGQ-05) |
| `gq_analytics__concorrencia_densidade__01` | `ranking_uf = rank() over (… order by ativos_por_10k_hab desc)`: 1 = mais concorrido | sim |
| `gq_core__cnae_secundario__01` | `union` + `count(distinct cnpj_completo)` | sim |
| `gq_core__data_calendario__01` | soma por mês; armadilha 1 do guia (21 × 11) confere: 10 + 11 = 21 | sim |
| `gq_semantica__situacao_cadastral__02` | filtra o mês (RSEM-01); vazio = zero | sim |
| `gq_core__regras_qualidade__01` | membros `-1`/`-2` | parcial (RGQ-10) |
| `gq_core__data_calendario__02` | `dim_data` no papel de início | sim (`intencao` em RGQ-10) |
| `gq_original__porte__01` | `media_idade` NULL para INATIVA | sim |

### Dado real (somente leitura, gold v1.3 em memória)

- Exemplo 1: Fundão/ES, 4741500 → 0 ativos e 5 não ativos. ✓
- Exemplo 3: Água Branca → AL 1.704/497, PB 1.280/452, PI 4.017/1.505. ✓
- Exemplo 6: sobrevivência de tintas no ES → 686 elegíveis em 3 anos, 83,38 %; 588 elegíveis em 5 anos, 78,74 %. ✓
- §8: 73.366.147 estabelecimentos, 28.263.121 ativos ("~73 milhões", "~28 milhões"). ✓
- Os números do CEMPRE, da renda e da REGIC do §10 não rodam no gold real da v1.3. Não conferi.

### Portabilidade do catálogo

- As golden queries do gold rodaram com views `main.<tabela>` sobre `read_parquet` do gold real, sem o dbt (P1, P2,
  P6, P7, P8, P10).
- O `fct_resumo_mensal` precisou de `hive_partitioning=true` para ter `mes_referencia`, como o guia descreve no §3.
- No warehouse do CI, o teste já executa o SQL portável com `${RAIZ_DADOS}` substituído.

### Compatibilidade

- O único código existente alterado é `relatorio.compilar_analises`, que agora exclui `path:analyses/golden` só
  quando não há subpasta. `rfb regras` (subpasta `regras_negocio`) e o relatório do caso continuam compilando o
  mesmo conjunto.
- O teste unitário foi ajustado para comparar a lista inteira de exclusões.
- O dicionário segue em dia no CI.
- `make` ganhou só o alvo `golden`, e `test_convencao_nomes` o reconhece.
- Tempo: `test_golden_queries.py` leva 38 s (160 testes; os 20 `mf query` são a maior parte); o `make ci` inteiro
  levou 5 min 16 s.
- `dfb831a`:
  - `arquivo()` devolve `None` em vez de levantar `StopIteration`;
  - a falha lista as sessões e os agentes que faltam;
  - `--parcial` imprime o aviso **antes** do JSON. Quem fizer parse do stdout precisa pular a primeira linha, o que
    não é problema hoje: a saída é para leitura humana.
