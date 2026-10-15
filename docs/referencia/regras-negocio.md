# Regras de negócio do cadastro CNPJ

> **Adição** ([ADR-0020](../adr/0020-regras-de-negocio.md)). Este catálogo lista as regras e invariantes que o cadastro
> CNPJ deveria cumprir e diz de onde vem cada uma. Cada regra tem uma analysis em
> `transform/analyses/regras_negocio/` que conta quantos registros a cumprem e quantos a violam. O resultado do dado
> real está em [`regras-negocio.md`](../relatorios/regras-negocio.md).

## Como usar

- `make regras` (ou `uv run rfb regras`) compila as analyses, executa-as no `warehouse.duckdb` de `RAIZ_DADOS`
  **somente leitura** e escreve `docs/relatorios/regras-negocio.md` (`SAIDA=<arquivo>` / `--saida` muda o
  destino). Rode depois de um `dbt build` do mês ([operacao.md](../operacao.md)).
- **Violação não é erro.** O comando sai com 0 mesmo com regras violadas. Só falha quando a execução falha:
  compilação, consulta, linha fora do padrão ou desencontro entre este catálogo e as analyses. Os checks **não**
  entram no `dbt build`: não derrubam nem atrasam a atualização mensal.
- **Só contagens.** Cada analysis devolve `regra`, `avaliados` (o universo da regra), `violacoes` e, se for o
  caso, uma quebra agregada (situação cadastral, porte, natureza jurídica, campo, tabela…). Nunca CNPJ, nome ou
  CPF ([ADR-0008](../adr/0008-minimizacao-dados-pessoais.md)). O `rfb regras` guarda isso em duas camadas: recusa
  coluna fora da lista fechada de quebras e valor que pareça identificador, com ou sem máscara (8 ou mais
  dígitos, o que pega CNPJ básico, CPF e CNPJ, ou CNPJ alfanumérico de 14 posições).
- No `make ci`, o mesmo comando roda sobre as fixtures e grava em `.tmp/ci/relatorio-regras.md` (não versionado).

## Tipos de regra e leitura de uma violação

| Tipo | Quer dizer |
|---|---|
| **legal** | está numa lei, instrução normativa ou resolução (LC 123/2006, IN RFB 2.119/2022) |
| **leiaute/cadastro** | está no leiaute dos dados abertos ou nas tabelas de domínio publicadas pela RFB |
| **estrutural** | grão ou chave: uma linha por X, toda referência tem par |
| **coerência do projeto** | o projeto espera que valha, mas nenhuma fonte o diz; regra do projeto ou observação |

Uma violação pode ser lida de quatro jeitos. O catálogo diz qual é o mais provável em cada regra; o relatório do
dado real diz o que se viu. Nenhuma das leituras é afirmada sem evidência.

- **Erro de dado da RFB:** o registro contradiz a regra e não há explicação conhecida.
- **Comportamento conhecido do cadastro:** a regra vale para atos novos, mas o cadastro guarda histórico (registros
  antigos, situações herdadas, efeitos futuros).
- **Defasagem temporal do extrato:** o extrato é uma fotografia; dois arquivos (Empresas, Simples, Estabelecimentos)
  ou dois atos podem estar em momentos diferentes.
- **Limite do projeto:** a regra foi traduzida para os dados disponíveis e a tradução não pega o caso.

## Traduções das regras pedidas

O pedido citou três regras. Duas viram checks diretos, a terceira precisa de tradução:

- **"Cada estabelecimento tem CNAE primário e CNAEs secundários":** o leiaute traz um CNAE fiscal principal e zero
  ou mais secundários por estabelecimento. Viram [RN-01](#rn-01) a [RN-04](#rn-04): o principal existe e está no
  domínio, os secundários estão no domínio, não repetem o principal e não se repetem.
- **"MEI não pode ter mais de um estabelecimento":** é a LC 123, art. 18-A, § 4º, II. Vira [RN-05](#rn-05), por
  empresa (CNPJ básico) com opção pelo MEI no arquivo Simples. O estabelecimento baixado continua no extrato, mas
  não é mais um estabelecimento da empresa: a violação é ter **mais de um não baixado** de situação conhecida, e a
  situação nula não deixa a empresa parecer limpa (quebra "indeterminado"). Junto vêm as regras
  vizinhas do MEI: optante do Simples ([RN-06](#rn-06)), microempresa ([RN-07](#rn-07)), natureza jurídica
  ([RN-08](#rn-08), observação), não ser sociedade ([RN-29](#rn-29)) e datas ([RN-09](#rn-09), [RN-25](#rn-25),
  [RN-26](#rn-26), [RN-28](#rn-28)).
- **"Empresa em situação ativa não pode ter data de encerramento":** o cadastro **não tem** uma data de
  encerramento. Tem, por estabelecimento, a situação cadastral, a "data do evento da situação cadastral" e o motivo
  da situação [RFB-Leiaute]. Um estabelecimento baixado tem situação 08 e a data da baixa em `dat_situacao`; um
  ativo que tivesse "data de encerramento" seria um ATIVO com motivo de encerramento. A regra vira quatro checks:
  - [RN-10](#rn-10): o ATIVO tem motivo 00 (SEM MOTIVO), e o não ativo tem um motivo. Na tabela de motivos da RFB,
    os motivos diferentes de 00 descrevem baixa (01 "EXTINCAO POR ENCERRAMENTO LIQUIDACAO VOLUNTARIA", 02
    "INCORPORACAO", 03 "FUSAO", 04 "CISAO TOTAL", 05 "ENCERRAMENTO DA FALENCIA", 54 "EXTINCAO - TRATAMENTO
    DIFERENCIADO DADO AS ME E EPP", 75 "OBITO DO MEI - TITULAR FALECIDO"…), nulidade, suspensão ou inaptidão;
    nenhum descreve uma inscrição regular. Os quatro primeiros são as hipóteses de baixa por extinção do art. 24 da
    IN 2.119, e o 05, a do inciso II;
  - [RN-11](#rn-11): o não ativo (nula, suspensa, inapta, baixada) tem a data da situação;
  - [RN-12](#rn-12): a data da situação não é anterior ao início de atividade;
  - [RN-13](#rn-13): nenhuma data de evento passa do limite do extrato (o dia seguinte à data de referência; para
    as opções, 1º de janeiro do ano seguinte).

  "Empresa" foi lida como estabelecimento, porque a situação cadastral é do estabelecimento
  ([CAMADA_SEMANTICA, A3](camada-semantica.md#a3-ciclo-de-vida)). A situação da empresa é a da matriz, e a regra
  da matriz para as filiais é a [RN-14](#rn-14).

## Catálogo

Colunas no formato tabela.coluna, com link para o [dicionário de dados](dicionario-dados.md). As fontes entre
colchetes estão em [Fontes](#fontes).

### Atividade econômica (CNAE)

<a id="rn-01"></a>
### RN-01 — Estabelecimento tem CNAE principal do domínio

- **Enunciado:** todo estabelecimento tem um CNAE fiscal principal preenchido, e o código existe no domínio de
  CNAEs publicado pela RFB.
- **Tipo:** leiaute/cadastro.
- **Fonte:** [RFB-Leiaute], campo "CNAE FISCAL PRINCIPAL – código da atividade econômica principal do
  estabelecimento" (no singular) e domínio "CNAEs".
- **Dados:** [`int_estabelecimentos__enriquecidos`](dicionario-dados.md#int_estabelecimentos__enriquecidos)`.cnae_principal`
  × [`stg_rfb__cnaes`](dicionario-dados.md#stg_rfb__cnaes)`.codigo`. Universo: estabelecimentos do mês, por
  situação.
- **Conceito:** [CNAE principal e secundárias](camada-semantica.md#cnae-principal-e-secundárias); ontologia
  `rfbo:temCnaePrincipal`.
- **Leitura de uma violação:** código fora do domínio do próprio extrato é erro de dado da RFB; código de versão
  antiga da CNAE, comportamento conhecido do cadastro. Não confundir com `cnaes_sem_par_bd` (par na Base dos Dados).
- **Analysis:** `transform/analyses/regras_negocio/rn_01_cnae_principal_valido.sql`.

<a id="rn-02"></a>
### RN-02 — CNAEs secundários são do domínio

- **Enunciado:** cada CNAE secundário do estabelecimento existe no domínio de CNAEs da RFB.
- **Tipo:** leiaute/cadastro.
- **Fonte:** [RFB-Leiaute], campo "CNAE FISCAL SECUNDÁRIA – código da(s) atividade(s) econômica(s) secundária(s)",
  separadas por vírgula (nota 5), e domínio "CNAEs".
- **Dados:** `int_estabelecimentos__enriquecidos.cnaes_secundarios_lista` (lista de `stg_rfb__estabelecimentos.cnaes_secundarios`)
  × `stg_rfb__cnaes.codigo`. Universo: ocorrências de CNAE secundário.
- **Conceito:** [CNAE principal e secundárias](camada-semantica.md#cnae-principal-e-secundárias); ontologia
  `rfbo:temCnaeSecundario`.
- **Leitura de uma violação:** como na RN-01; um código com tamanho errado também indica falha na separação da lista.
- **Analysis:** `transform/analyses/regras_negocio/rn_02_cnaes_secundarios_validos.sql`.

<a id="rn-03"></a>
### RN-03 — CNAE secundário não repete o principal

- **Enunciado:** nenhum CNAE secundário é igual ao CNAE fiscal principal do mesmo estabelecimento.
- **Tipo:** coerência do projeto.
- **Fonte:** regra do projeto. O leiaute separa principal e secundárias, mas não proíbe a repetição.
- **Dados:** `int_estabelecimentos__enriquecidos.cnae_principal` e `.cnaes_secundarios_lista`. Universo: ocorrências
  de CNAE secundário.
- **Conceito:** [CNAE principal e secundárias](camada-semantica.md#cnae-principal-e-secundárias).
- **Leitura de uma violação:** comportamento conhecido do cadastro (a atividade foi promovida a principal e ficou
  também na lista) ou erro de dado. Não muda as métricas, que usam só o principal.
- **Analysis:** `transform/analyses/regras_negocio/rn_03_cnae_secundario_diferente_do_principal.sql`.

<a id="rn-04"></a>
### RN-04 — CNAEs secundários não se repetem

- **Enunciado:** a lista de CNAEs secundários de um estabelecimento não tem código repetido.
- **Tipo:** coerência do projeto.
- **Fonte:** regra do projeto.
- **Dados:** `int_estabelecimentos__enriquecidos.cnaes_secundarios_lista`. Universo: estabelecimentos com ao menos um
  secundário.
- **Conceito:** [CNAE principal e secundárias](camada-semantica.md#cnae-principal-e-secundárias). A ponte
  [`bridge_estabelecimento_cnae_secundario`](dicionario-dados.md#bridge_estabelecimento_cnae_secundario) tem uma linha
  por par: repetições na lista viram uma linha só.
- **Leitura de uma violação:** erro de dado da RFB.
- **Analysis:** `transform/analyses/regras_negocio/rn_04_cnae_secundario_sem_repeticao.sql`.

### Simples Nacional e MEI

<a id="rn-05"></a>
### RN-05 — MEI tem um único estabelecimento não baixado

- **Enunciado:** a empresa com opção pelo MEI tem no máximo um estabelecimento não baixado no extrato. A situação
  nula (vazia ou ilegível no extrato) não conta como baixada nem como não baixada.
- **Tipo:** legal.
- **Fonte:** [LC 123], art. 18-A, § 4º, II: não pode optar pelo SIMEI o MEI "que possua mais de um estabelecimento".
- **Dados:** [`stg_rfb__simples`](dicionario-dados.md#stg_rfb__simples)`.opcao_mei` × estabelecimentos do mesmo
  CNPJ básico em `int_estabelecimentos__enriquecidos`. Universo: empresas (CNPJ básico) com opção pelo MEI, pela
  quantidade de estabelecimentos. Viola a faixa "mais de um não baixado" (de situação conhecida). Não violam: "mais
  de um, no máximo um não baixado" e "indeterminado (situação desconhecida)", a empresa com algum estabelecimento de
  situação nula que teria mais de um não baixado se esses contassem como não baixados (ex.: um ATIVO e um de
  situação nula). O indeterminado não entra nas violações porque a situação não é conhecida, e não entra no "no
  máximo um" para a falta de informação não parecer cadastro limpo.
- **Conceito:** [Simples Nacional e MEI](camada-semantica.md#simples-nacional-e-mei); ontologia `rfbo:OpcaoMEI`.
- **Leitura de uma violação:** mais de um estabelecimento não baixado é erro de dado ou desenquadramento ainda não
  registrado (defasagem). Os estabelecimentos baixados além do único não baixado são comportamento conhecido do
  cadastro (o baixado continua no extrato) e não contrariam a lei: aparecem na quebra, sem violação. A RSEM já
  tinha visto 3.749 filiais de MEI no dado real de 2026-09, quase todas baixadas. O "indeterminado" é lacuna de
  dado, não violação. O build não a barra: a situação vazia fica fora do teste `taxa_conversao_tipada`, e a ilegível
  só avisa até 5 % de perda. É aqui que a lacuna aparece.
- **Analysis:** `transform/analyses/regras_negocio/rn_05_mei_estabelecimento_unico.sql`.

<a id="rn-06"></a>
### RN-06 — MEI é optante do Simples Nacional

- **Enunciado:** quem tem opção pelo MEI tem também opção pelo Simples Nacional.
- **Tipo:** legal.
- **Fonte:** [LC 123], art. 18-A, § 1º: considera-se MEI quem "seja optante pelo Simples Nacional".
- **Dados:** `stg_rfb__simples.opcao_mei` e `.opcao_simples`. Universo: empresas com opção pelo MEI.
- **Conceito:** [Simples Nacional e MEI](camada-semantica.md#simples-nacional-e-mei). O build já tem o teste
  equivalente na fato (`not opcao_mei or opcao_simples`); aqui a regra é contada na fonte.
- **Leitura de uma violação:** erro de dado ou defasagem entre as duas opções do mesmo arquivo.
- **Analysis:** `transform/analyses/regras_negocio/rn_06_mei_optante_simples.sql`.

<a id="rn-07"></a>
### RN-07 — MEI tem porte de microempresa

- **Enunciado:** a empresa com opção pelo MEI tem o porte 01 (MICRO EMPRESA) no arquivo Empresas.
- **Tipo:** legal.
- **Fonte:** [LC 123], art. 18-E, § 3º: "O MEI é modalidade de microempresa." Códigos de porte: [RFB-Leiaute].
- **Dados:** `stg_rfb__simples.opcao_mei` × [`stg_rfb__empresas`](dicionario-dados.md#stg_rfb__empresas)`.porte_codigo`.
  Universo: empresas MEI presentes no arquivo Empresas, por porte declarado.
- **Conceito:** [Porte](camada-semantica.md#porte) ("o porte é declarado, não medido") e
  [Simples Nacional e MEI](camada-semantica.md#simples-nacional-e-mei).
- **Leitura de uma violação:** o porte é declarado no registro e não acompanha a opção pelo MEI; uma violação é
  comportamento conhecido do cadastro (porte desatualizado) mais provável que erro.
- **Analysis:** `transform/analyses/regras_negocio/rn_07_mei_porte_micro.sql`.

<a id="rn-08"></a>
### RN-08 — MEI tem natureza 213-5 (observação)

- **Enunciado:** a empresa com opção pelo MEI tem a natureza jurídica 213-5 Empresário (Individual).
- **Tipo:** coerência do projeto.
- **Fonte:** observação do projeto, **não regra**. A LC 123 define o MEI como empresário individual **ou** o
  empreendedor de certas atividades (art. 18-A, § 1º) e a CONCLA não associa o MEI a uma natureza (RSEM-06). O que
  a lei sustenta é mais estreito e é a [RN-29](#rn-29): o MEI não é sociedade.
- **Dados:** `stg_rfb__simples.opcao_mei` × `stg_rfb__empresas.natureza_juridica_codigo` e
  [`stg_rfb__naturezas`](dicionario-dados.md#stg_rfb__naturezas). Universo: empresas MEI no arquivo Empresas.
- **Conceito:** [Natureza jurídica](camada-semantica.md#natureza-jurídica) ("MEI não é natureza jurídica").
- **Leitura de uma violação:** não é erro por si; mostra quantas empresas MEI têm outra natureza (a RSEM viu 1.238
  estabelecimentos com natureza de sociedade em 2026-09). Código sem descrição no domínio aparece como
  "(fora do domínio)".
- **Analysis:** `transform/analyses/regras_negocio/rn_08_mei_natureza_empresario_individual.sql`.

<a id="rn-29"></a>
### RN-29 — MEI não é sociedade

- **Enunciado:** a empresa com opção pelo MEI não tem natureza jurídica de sociedade.
- **Tipo:** legal.
- **Fonte:** [LC 123], art. 18-A, § 1º (redação da LC 188/2021): considera-se MEI quem "seja empresário individual
  que se enquadre na definição do art. 966 [do Código Civil] [...] ou o empreendedor que exerça" as atividades dos
  §§ 4º-A e 4º-B. Sociedade não é nenhum dos dois. As naturezas de sociedade são as da [CONCLA] cujo nome é
  "Sociedade ...": 203-8, 204-6, 205-4, 206-2, 207-0, 208-9, 209-7, 212-7, 223-2, 224-0, 225-9, 226-7 e 232-1. O
  consórcio e o grupo de sociedades (215-1, 216-0) e o estabelecimento de sociedade estrangeira (217-8) não são,
  eles mesmos, sociedades e ficam de fora.
- **Dados:** `stg_rfb__simples.opcao_mei` × `stg_rfb__empresas.natureza_juridica_codigo` e `stg_rfb__naturezas`.
  Universo: empresas MEI no arquivo Empresas, por natureza.
- **Conceito:** [Natureza jurídica](camada-semantica.md#natureza-jurídica) e
  [Simples Nacional e MEI](camada-semantica.md#simples-nacional-e-mei).
- **Leitura de uma violação:** erro de dado ou desenquadramento do MEI não registrado depois de a empresa virar
  sociedade (defasagem). Diferente da [RN-08](#rn-08), que é observação, aqui a lei é contrariada.
- **Analysis:** `transform/analyses/regras_negocio/rn_29_mei_nao_e_sociedade.sql`.

<a id="rn-09"></a>
### RN-09 — Exclusão do regime não antecede a opção

- **Enunciado:** quando o registro do Simples tem data de opção e data de exclusão do mesmo regime, a exclusão não
  é anterior à opção. Vale para o Simples Nacional e para o MEI. Exclusão no mesmo dia da opção não viola.
- **Tipo:** coerência do projeto.
- **Fonte:** regra do projeto sobre os campos "data de opção" e "data de exclusão" de cada regime [RFB-Leiaute].
- **Dados:** `stg_rfb__simples.dat_opcao_simples`, `.dat_exclusao_simples`, `.dat_opcao_mei`, `.dat_exclusao_mei`.
  Universo: registros com as duas datas, por regime.
- **Conceito:** [Simples Nacional e MEI](camada-semantica.md#simples-nacional-e-mei).
- **Leitura de uma violação:** o arquivo guarda uma opção e uma exclusão por regime. Uma nova opção depois de uma
  exclusão pode deixar a exclusão antiga com a opção nova (comportamento do cadastro); sem reopção, é erro de dado.
- **Analysis:** `transform/analyses/regras_negocio/rn_09_simples_exclusao_apos_opcao.sql`.

<a id="rn-25"></a>
### RN-25 — Opção pelo Simples a partir de 1º/7/2007

- **Enunciado:** a data de opção pelo Simples Nacional não é anterior a 1º de julho de 2007.
- **Tipo:** legal.
- **Fonte:** [LC 123], art. 88: a lei entra em vigor na publicação, "ressalvado o regime de tributação das
  microempresas e empresas de pequeno porte, que entra em vigor em 1º de julho de 2007".
- **Dados:** `stg_rfb__simples.dat_opcao_simples`. Universo: registros com data de opção pelo Simples.
- **Conceito:** [Simples Nacional e MEI](camada-semantica.md#simples-nacional-e-mei).
- **Leitura de uma violação:** erro de dado ou data de opção do regime anterior (o Simples federal, Lei 9.317/1996)
  levada para o campo.
- **Analysis:** `transform/analyses/regras_negocio/rn_25_opcao_simples_apos_inicio_regime.sql`.

<a id="rn-26"></a>
### RN-26 — Opção pelo MEI a partir de 1º/7/2009

- **Enunciado:** a data de opção pelo MEI (SIMEI) não é anterior a 1º de julho de 2009.
- **Tipo:** legal.
- **Fonte:** [LC 128], art. 14, III: os arts. 18-A a 18-C da LC 123, que criam o SIMEI, "produzirão efeitos a
  partir de 1º de julho de 2009".
- **Dados:** `stg_rfb__simples.dat_opcao_mei`. Universo: registros com data de opção pelo MEI.
- **Conceito:** [Simples Nacional e MEI](camada-semantica.md#simples-nacional-e-mei).
- **Leitura de uma violação:** erro de dado (por exemplo, a data de opção pelo Simples copiada para o MEI).
- **Analysis:** `transform/analyses/regras_negocio/rn_26_opcao_mei_apos_inicio_simei.sql`.

<a id="rn-28"></a>
### RN-28 — Opção não antecede o início de atividade (observação)

- **Enunciado:** a data de opção pelo Simples Nacional ou pelo MEI não é anterior ao início de atividade da matriz.
  A opção no mesmo dia do início não viola.
- **Tipo:** coerência do projeto.
- **Fonte:** observação do projeto, **não regra**. Nenhuma fonte diz que a opção não pode anteceder o início de
  atividade, e o leiaute não diz se o arquivo guarda a data do pedido ou a de efeito (a [RN-13](#rn-13) já viu
  opções com data de efeito). Por isso a regra não vira alerta.
- **Dados:** `stg_rfb__simples.dat_opcao_simples`, `.dat_opcao_mei` ×
  `int_estabelecimentos__enriquecidos.dat_inicio_atividade` da matriz. Universo: registros com a data de opção do
  regime, de CNPJ básico com uma única matriz com início de atividade, por regime.
- **Conceito:** [Data de início de atividade](camada-semantica.md#data-de-início-de-atividade) e
  [Simples Nacional e MEI](camada-semantica.md#simples-nacional-e-mei).
- **Leitura de uma violação:** data de início de atividade corrigida depois da opção, opção na abertura com início
  de atividade declarado depois, ou erro de dado. Não é afirmada nenhuma delas.
- **Analysis:** `transform/analyses/regras_negocio/rn_28_opcao_apos_inicio_atividade.sql`.

### Situação cadastral e datas

<a id="rn-10"></a>
### RN-10 — Motivo coerente com a situação

- **Enunciado:** o estabelecimento ATIVO tem o motivo 00 (SEM MOTIVO), e o estabelecimento não ativo tem um motivo
  diferente de 00. Motivo vazio conta como 00.
- **Tipo:** coerência do projeto.
- **Fonte:** regra do projeto, apoiada na tabela de motivos que a RFB publica com os dados abertos (o leiaute só diz
  "código do motivo da situação cadastral" [RFB-Leiaute]) e nas hipóteses de baixa do [IN 2.119], art. 24. Veja a
  [tradução](#traduções-das-regras-pedidas).
- **Dados:** [`stg_rfb__estabelecimentos`](dicionario-dados.md#stg_rfb__estabelecimentos)`.situacao_codigo` e
  `.motivo_situacao_codigo`; [`stg_rfb__motivos`](dicionario-dados.md#stg_rfb__motivos). Universo: todos os
  estabelecimentos, por situação.
- **Conceito:** [Situação cadastral](camada-semantica.md#situação-cadastral); ontologia
  `rfbo:MotivoSituacaoCadastral`.
- **Leitura de uma violação:** ATIVO com motivo é um estabelecimento restabelecido em que o motivo antigo ficou
  (comportamento do cadastro) ou erro de dado. Não ativo com motivo 00 é erro de dado.
- **Analysis:** `transform/analyses/regras_negocio/rn_10_motivo_coerente_com_situacao.sql`.

<a id="rn-11"></a>
### RN-11 — Não ativo tem data da situação

- **Enunciado:** o estabelecimento NULO, SUSPENSO, INAPTO ou BAIXADO tem a data do evento da situação cadastral.
- **Tipo:** coerência do projeto.
- **Fonte:** regra do projeto sobre o campo "data do evento da situação cadastral" [RFB-Leiaute]; a baixa produz
  efeitos desde a data do evento [IN 2.119, art. 24, § 1º]. O leiaute não diz que o campo é obrigatório.
- **Dados:** `int_estabelecimentos__enriquecidos.situacao_codigo` e `.dat_situacao` (`00000000` vira nulo).
  Universo: estabelecimentos não ativos.
- **Conceito:** [Situação cadastral](camada-semantica.md#situação-cadastral) e
  [A3](camada-semantica.md#a3-ciclo-de-vida): sem data, o estabelecimento não entra em `encerramentos` nem `baixas`.
- **Leitura de uma violação:** erro de dado. O ATIVO sem data fica fora da regra (a RSEM viu 115.651 em 2026-09).
- **Analysis:** `transform/analyses/regras_negocio/rn_11_inativo_com_data_situacao.sql`.

<a id="rn-12"></a>
### RN-12 — Situação não antecede o início de atividade

- **Enunciado:** a data da situação cadastral não é anterior à data de início de atividade do estabelecimento. As
  duas datas no mesmo dia não violam.
- **Tipo:** coerência do projeto.
- **Fonte:** regra do projeto sobre os campos de data do [RFB-Leiaute].
- **Dados:** `int_estabelecimentos__enriquecidos.dat_situacao` e `.dat_inicio_atividade`. Universo: estabelecimentos
  com as duas datas, por situação.
- **Conceito:** [Data de início de atividade](camada-semantica.md#data-de-início-de-atividade).
- **Leitura de uma violação:** erro de dado ou data de início corrigida depois do evento. Distorce idade, coortes e
  `mart_dinamica_mercado` (encerramento antes da abertura).
- **Analysis:** `transform/analyses/regras_negocio/rn_12_situacao_apos_inicio_atividade.sql`.

<a id="rn-13"></a>
### RN-13 — Datas de evento não passam do extrato

- **Enunciado:** nenhuma data de evento já ocorrido passa do limite do extrato. Para início de atividade, situação
  cadastral e situação especial, o limite é o dia seguinte à data de referência. Para a opção pelo Simples e pelo
  MEI, é 1º de janeiro do ano seguinte.
- **Tipo:** coerência do projeto.
- **Fonte:** regra do projeto ([ADR-0004](../adr/0004-data-referencia-deterministica.md)), com dois limites medidos ou
  documentados:
  - **dia seguinte (D+1):** no dado real de 2026-09, todas as datas de evento acima da data de referência
    (12/09/2026) são de 13/09/2026, salvo as opções para 2027 (RRN-02). O corte do extrato inclui o dia seguinte ao
    token do nome do arquivo. O D+1 aparece numa faixa à parte, sem violação;
  - **1º de janeiro seguinte:** a opção pelo Simples para 2027 é feita de 1º de setembro a 15 de outubro de 2026 e
    "produzirá efeitos a partir de 1º de janeiro de 2027" [CGSN 190; CGSN 194]. O campo guarda a data de efeito,
    então a opção feita no mês do extrato tem data futura legítima.

  As datas de **exclusão** ficam de fora: podem ter efeito futuro legítimo (R3-11).
- **Dados:** `int_estabelecimentos__enriquecidos.dat_inicio_atividade`, `.dat_situacao`;
  `stg_rfb__estabelecimentos.dat_situacao_especial`; `stg_rfb__simples.dat_opcao_simples`, `.dat_opcao_mei`;
  `_data_referencia`. Universo: valores preenchidos de cada campo, pela faixa ("até a data do extrato", "dia
  seguinte ao extrato", "opção até 1º de janeiro seguinte" e "além do limite"); só a última viola.
- **Conceito:** [Data de início de atividade](camada-semantica.md#data-de-início-de-atividade). O build já avisa
  (`data_nao_futura`, warn) nas colunas de staging; aqui a regra é contada por campo.
- **Leitura de uma violação:** erro de digitação de data ou ato registrado com data posterior. A faixa D+1 é o
  corte do extrato (defasagem), não erro.
- **Analysis:** `transform/analyses/regras_negocio/rn_13_datas_nao_futuras.sql`.

<a id="rn-14"></a>
### RN-14 — Matriz baixada, filiais baixadas ou nulas

- **Enunciado:** se a matriz de uma empresa está BAIXADA, nenhuma filial dela está ativa, suspensa ou inapta: todas
  estão BAIXADAS, ou NULAS.
- **Tipo:** legal.
- **Fonte:** [IN 2.119], art. 24, § 2º: "A baixa da inscrição do estabelecimento matriz no CNPJ implica baixa de
  todas as inscrições dos estabelecimentos filiais da entidade."
- **Dados:** `int_estabelecimentos__enriquecidos.cnpj_raiz`, `.matriz_filial_codigo`, `.situacao_codigo`. Universo:
  filiais de empresas com matriz baixada, pela situação da filial. Viola a filial que não está BAIXADA nem NULA; a
  NULA aparece na quebra, sem violação.
- **Conceito:** [Matriz × filial](camada-semantica.md#matriz--filial); ontologia `rfbo:Matriz`, `rfbo:Filial`.
- **Leitura de uma violação:** defasagem (a baixa da filial ainda não refletida no extrato), filial transformada em
  matriz [IN 2.119, art. 4º, § 3º] ou erro de dado. A filial **NULA** não viola: a nulidade produz efeitos "a partir
  do termo inicial de vigência do ato cadastral declarado nulo" [IN 2.119, art. 34, parágrafo único], então não há
  inscrição regular a baixar.
- **Analysis:** `transform/analyses/regras_negocio/rn_14_matriz_baixada_filiais_baixadas.sql`.

<a id="rn-27"></a>
### RN-27 — Filial não começa depois do fim da matriz

- **Enunciado:** a filial não tem início de atividade posterior à data em que a matriz foi baixada, declarada inapta
  ou declarada nula. Começar **no mesmo dia** do evento da matriz não viola: o cadastro só traz datas, sem hora, e
  não dá para dizer se a filial começou antes ou depois do evento naquele dia. A regra acusa só o que é
  inequivocamente "depois".
- **Tipo:** coerência do projeto.
- **Fonte:** regra do projeto apoiada no [IN 2.119], art. 21, IV: impede a inscrição no CNPJ, "no caso de
  estabelecimento filial, o fato de o estabelecimento matriz da entidade não possuir inscrição no CNPJ ou de sua
  inscrição ser inexistente, baixada, inapta ou nula". A IN fala da **inscrição**; o extrato não traz a data de
  inscrição, e o início de atividade pode ser declarado diferente dela. Por isso não é regra legal. A IN também não
  diz nada sobre um ato no mesmo dia do evento da matriz, por isso a fronteira fica com o enunciado ("depois de").
- **Dados:** `int_estabelecimentos__enriquecidos.cnpj_raiz`, `.matriz_filial_codigo`, `.situacao_codigo`,
  `.dat_situacao` (matriz) e `.dat_inicio_atividade` (filial). Universo: filiais com início de atividade, de CNPJ
  básico com uma única matriz NULA, INAPTA ou BAIXADA com data da situação; pela situação da matriz.
- **Conceito:** [Matriz × filial](camada-semantica.md#matriz--filial) e
  [Situação cadastral](camada-semantica.md#situação-cadastral).
- **Leitura de uma violação:** filial inscrita antes do evento da matriz com início de atividade declarado depois,
  inscrição feita antes de a regra valer, nulidade com data do ato posterior à inscrição, ou erro de dado.
- **Analysis:** `transform/analyses/regras_negocio/rn_27_filial_nao_inicia_apos_fim_da_matriz.sql`.

<a id="rn-15"></a>
### RN-15 — Situação especial e data andam juntas

- **Enunciado:** a situação especial e a data da situação especial estão as duas preenchidas ou as duas vazias.
- **Tipo:** coerência do projeto.
- **Fonte:** regra do projeto sobre os campos "situação especial da empresa" e "data em que a empresa entrou em
  situação especial" [RFB-Leiaute].
- **Dados:** `stg_rfb__estabelecimentos.situacao_especial` e `.dat_situacao_especial`. Universo: todos os
  estabelecimentos, por situação.
- **Conceito:** [Situação especial](camada-semantica.md#situação-especial).
- **Leitura de uma violação:** erro de dado.
- **Analysis:** `transform/analyses/regras_negocio/rn_15_situacao_especial_com_data.sql`.

### Estrutura do cadastro

<a id="rn-16"></a>
### RN-16 — Uma matriz por CNPJ básico

- **Enunciado:** cada CNPJ básico do arquivo Estabelecimentos tem exatamente uma matriz.
- **Tipo:** estrutural.
- **Fonte:** regra do projeto, a leitura de [Matriz × filial](camada-semantica.md#matriz--filial): o identificador
  1/2 [RFB-Leiaute] e a inscrição dos entes "na condição de estabelecimento matriz" [IN 2.119, art. 4º, § 1º]. Não
  há texto que diga "uma matriz por entidade".
- **Dados:** `int_estabelecimentos__enriquecidos.cnpj_raiz` e `.matriz_filial_codigo`. Universo: CNPJs básicos, pelo
  número de matrizes (0, 1, 2 ou mais).
- **Conceito:** [Empresa × estabelecimento](camada-semantica.md#empresa--estabelecimento): `qtd_matrizes` conta
  empresas supondo esta regra.
- **Leitura de uma violação:** 2 ou mais matrizes é erro de dado; 0 matrizes, empresa só com filiais no extrato.
  As duas distorcem `qtd_matrizes`. A RSEM viu 1 CNPJ básico com 2 matrizes em 2026-09.
- **Analysis:** `transform/analyses/regras_negocio/rn_16_uma_matriz_por_cnpj_basico.sql`.

<a id="rn-17"></a>
### RN-17 — Dígitos verificadores do CNPJ

- **Enunciado:** os dois dígitos verificadores do CNPJ conferem pelo módulo 11, no formato numérico e no
  alfanumérico.
- **Tipo:** legal.
- **Fonte:** [IN 2.119], art. 2º, parágrafo único (formato alfanumérico de 14 posições, Anexo XV) e
  [RFB-Alfanumérico] (DV "utilizando o cálculo pelo módulo 11"; os números atuais e seus DV continuam válidos).
- **Dados:** `int_estabelecimentos__enriquecidos.cnpj_completo` (macro `cnpj_dv_invalidos`, a mesma do teste
  `cnpj_dv_valido`, que no build só avisa). Universo: estabelecimentos, por situação.
- **Conceito:** [CNPJ](camada-semantica.md#cnpj).
- **Leitura de uma violação:** erro de dado da RFB ou de conversão.
- **Analysis:** `transform/analyses/regras_negocio/rn_17_cnpj_dv_valido.sql`.

<a id="rn-18"></a>
### RN-18 — Estabelecimento tem empresa

- **Enunciado:** todo estabelecimento tem a empresa (o mesmo CNPJ básico) no arquivo Empresas do mês.
- **Tipo:** estrutural.
- **Fonte:** [RFB-Leiaute]: o CNPJ básico é o "número base de inscrição" nos dois arquivos; a empresa tem um ou mais
  estabelecimentos [IN 2.119, art. 4º].
- **Dados:** `int_estabelecimentos__enriquecidos.tem_empresa` (left join com `stg_rfb__empresas`). Universo:
  estabelecimentos, por situação.
- **Conceito:** [Empresa × estabelecimento](camada-semantica.md#empresa--estabelecimento).
- **Leitura de uma violação:** defasagem entre os arquivos do mês ou erro de dado. O estabelecimento sem empresa
  fica com natureza e porte -1 na estrela e é descartado por `bh_empresas` (inner join do original).
- **Analysis:** `transform/analyses/regras_negocio/rn_18_estabelecimento_com_empresa.sql`.

<a id="rn-19"></a>
### RN-19 — Município do domínio da RFB

- **Enunciado:** o código de município do estabelecimento existe no domínio de municípios publicado pela RFB.
- **Tipo:** leiaute/cadastro.
- **Fonte:** [RFB-Leiaute], campo "MUNICÍPIO – código do município de jurisdição onde se encontra o
  estabelecimento" e domínio "MUNICÍPIOS".
- **Dados:** `int_estabelecimentos__enriquecidos.municipio_rfb_codigo` × [`stg_rfb__municipios`](dicionario-dados.md#stg_rfb__municipios)`.codigo`.
  Universo: estabelecimentos, por situação.
- **Conceito:** [Município: código RFB × código IBGE](camada-semantica.md#município-código-rfb--código-ibge). É o
  domínio da **RFB**: o par na Base dos Dados é outro teste (`cobertura_municipio_rfb_bd`).
- **Leitura de uma violação:** erro de dado da RFB.
- **Analysis:** `transform/analyses/regras_negocio/rn_19_municipio_no_dominio.sql`.

<a id="rn-20"></a>
### RN-20 — Ente federativo só na administração pública

- **Enunciado:** o ente federativo responsável é preenchido nas naturezas jurídicas do grupo 1XXX (administração
  pública) e fica em branco nas demais.
- **Tipo:** leiaute/cadastro.
- **Fonte:** [RFB-Leiaute]: "O ENTE FEDERATIVO RESPONSÁVEL É PREENCHIDO PARA OS CASOS DE ÓRGÃOS E ENTIDADES DO GRUPO DE
  NATUREZA JURÍDICA 1XXX. PARA AS DEMAIS NATUREZAS, ESTE ATRIBUTO FICA EM BRANCO" (e nota 3).
- **Dados:** `stg_rfb__empresas.natureza_juridica_codigo` e `.ente_federativo_responsavel`; `stg_rfb__naturezas`.
  Universo: empresas, pelo grupo e pela natureza; natureza vazia conta como "demais".
- **Conceito:** [Natureza jurídica](camada-semantica.md#natureza-jurídica).
- **Leitura de uma violação:** no grupo 1, ente vazio é erro de dado ou entidade sem um único ente responsável, como
  o consórcio público (1210, 1228), que é interfederativo; fora dele, ente preenchido é erro de dado ou natureza
  alterada sem limpar o campo.
- **Analysis:** `transform/analyses/regras_negocio/rn_20_ente_federativo_natureza_publica.sql`.

<a id="rn-21"></a>
### RN-21 — Capital social não negativo

- **Enunciado:** o capital social da empresa não é negativo.
- **Tipo:** coerência do projeto.
- **Fonte:** regra do projeto sobre o campo "capital social da empresa" [RFB-Leiaute].
- **Dados:** `stg_rfb__empresas.capital_social` e `.porte_codigo`. Universo: empresas com capital preenchido, por
  porte.
- **Conceito:** [Capital social](camada-semantica.md#capital-social): `capital_social_total` soma só as matrizes.
- **Leitura de uma violação:** erro de dado ou de conversão do separador decimal.
- **Analysis:** `transform/analyses/regras_negocio/rn_21_capital_social_nao_negativo.sql`.

### Grãos declarados sem teste (RDIC-09)

O dicionário de dados declara o grão de cada tabela e diz quando ele não é testado
([RDIC-09](../historico/revisoes/RDIC.md)). Estas regras contam as linhas excedentes (linhas − chaves distintas) sem acrescentar
testes ao build.

<a id="rn-22"></a>
### RN-22 — Simples: uma linha por CNPJ básico

- **Enunciado:** o arquivo Simples tem uma linha por CNPJ básico no mês selecionado.
- **Tipo:** estrutural.
- **Fonte:** regra do projeto, o grão declarado de [`rfb.simples`](dicionario-dados.md#rfb-simples) ("empresa
  (`cnpj_raiz`) por mês de referência").
- **Dados:** `stg_rfb__simples.cnpj_raiz` (a fonte já filtrada pelo mês). Universo: linhas do mês.
- **Conceito:** [Simples Nacional e MEI](camada-semantica.md#simples-nacional-e-mei).
- **Leitura de uma violação:** arquivo duplicado na pasta do mês ou erro de dado; a raiz repetida multiplicaria
  estabelecimentos no left join de `int_estabelecimentos__enriquecidos`.
- **Analysis:** `transform/analyses/regras_negocio/rn_22_grao_simples.sql`.

<a id="rn-23"></a>
### RN-23 — Grão dos marts

- **Enunciado:** os marts sem teste de unicidade têm uma linha por combinação do grão declarado:
  [`agg_empresas`](dicionario-dados.md#agg_empresas) (as 10 dimensões do original),
  [`mart_dinamica_mercado`](dicionario-dados.md#mart_dinamica_mercado) (`ano`, `sk_cnae`, `sk_municipio`) e
  [`mart_sobrevivencia_coorte`](dicionario-dados.md#mart_sobrevivencia_coorte) (`ano_coorte`, `sk_cnae`, `sk_porte`,
  `uf`).
- **Tipo:** estrutural.
- **Fonte:** regra do projeto (`meta.grao` dos modelos).
- **Dados:** as três tabelas do gold. Universo: linhas de cada tabela.
- **Conceito:** [A3](camada-semantica.md#a3-ciclo-de-vida) (aberturas, encerramentos, coortes).
- **Leitura de uma violação:** limite do projeto (erro de modelagem: um `group by` sem uma das chaves).
- **Analysis:** `transform/analyses/regras_negocio/rn_23_grao_marts.sql`.

<a id="rn-24"></a>
### RN-24 — Grão das fontes e domínios

- **Enunciado:** as fontes e o seed sem teste de unicidade têm uma linha por chave do grão declarado:
  [`rfb.paises`](dicionario-dados.md#rfb-paises) e [`rfb.qualificacoes`](dicionario-dados.md#rfb-qualificacoes)
  (`codigo` por mês, só no mês do relatório), [`basedosdados.cnae_2`](dicionario-dados.md#basedosdados-cnae_2) (`subclasse`),
  [`basedosdados.regiao_metropolitana_2017`](dicionario-dados.md#basedosdados-regiao_metropolitana_2017) (município ×
  região), [`basedosdados.vizinhanca_municipio`](dicionario-dados.md#basedosdados-vizinhanca_municipio) (`ano`,
  `id_municipio_1`, `id_municipio_2`, como publicada), [`excecoes_conhecidas_municipio`](dicionario-dados.md#excecoes_conhecidas_municipio)
  (`codigo`) e [`observabilidade.dq_historico_testes`](dicionario-dados.md#observabilidade-dq_historico_testes)
  (`invocation_id`, `nome_teste`).
- **Tipo:** estrutural.
- **Fonte:** regra do projeto (`meta.grao` das fontes e do seed).
- **Dados:** as sete tabelas. Universo: linhas de cada tabela. As fontes RFB guardam todos os meses ingeridos:
  países e qualificações entram só no mês do relatório (o `_mes_referencia` de
  `int_estabelecimentos__enriquecidos`, o mesmo das demais regras), para o grão valer sobre a fotografia do mês. Um
  duplicado de um mês antigo não conta, e apagar meses antigos não muda o total. As outras cinco não têm mês: a Base
  dos Dados e o seed são uma versão só, e o histórico de testes acumula execuções por desenho.
- **Conceito:** [A1](camada-semantica.md#a1-as-bases).
- **Leitura de uma violação:** na vizinhança é comportamento conhecido da fonte: o grão declarado avisa que ela
  "pode repetir o par" e a ponte `bridge_municipio_vizinho` deduplica (RDIC-02). Nas demais, erro de dado da fonte
  ou arquivo duplicado.
- **Analysis:** `transform/analyses/regras_negocio/rn_24_grao_fontes_e_dominios.sql`.

### Coerência entre as bases (incremento enriquecimento IBGE)

<a id="rn-30"></a>
### RN-30 — CEMPRE e RFB concordam sobre a presença do setor no município (observação)

- **Enunciado:** onde o CEMPRE do IBGE vê ao menos 3 unidades locais de uma classe CNAE num município, a RFB tem ao
  menos um estabelecimento ativo da classe que não é de empresa optante pelo MEI.
- **Tipo:** coerência do projeto.
- **Fonte:** observação do projeto, **não regra**: nenhuma das duas bases promete bater com a outra. O que a
  sustenta é a metodologia do CEMPRE [IBGE-CEMPRE]: desde o ano-base 2022 ele inclui as empresas e outras
  organizações com "situação cadastral ativa em 31.12 na Receita Federal" que não tenham indicativo de inatividade
  nas pesquisas estruturais do IBGE, mais as que declararam o eSocial ou responderam às pesquisas, e **exclui os
  MEI**. Por isso a comparação é com os ativos **sem MEI**. O CEMPRE conta também unidades sem empregado (71,6 % das
  empresas de 2024 não tinham assalariado em 31.12): não é um cadastro só de quem emprega. O que **não** se sabe:
  como o IBGE classifica a atividade de cada unidade local (o CNAE das pesquisas do IBGE prevalece sobre o dos
  registros administrativos, e a publicação não diz se a unidade herda a classe da empresa), nem quantas unidades o
  filtro de inatividade tira em cada classe.
- **Limiar:** 3 unidades. Com 1 ou 2, a diferença cabe na defasagem: o CEMPRE é de 31/12 do `ano_cempre` (hoje
  2024) e o extrato da RFB é de quase dois anos depois, e uma ou duas baixas ou reclassificações bastam para zerar
  a classe. A metodologia não indica outro limiar; se a leitura do dado real mostrar que o 3 só pega ruído, ele
  sobe.
- **Dados:** a fonte `ibge.cempre_municipio_cnae` (variável 706, unidades locais, no ano mais recente, classes CNAE
  `NN.NN-N` de `ibge.cempre_categorias_cnae`) × [`fct_estabelecimentos`](dicionario-dados.md#fct_estabelecimentos)
  ativos (`eh_ativa`, `opcao_mei`) × [`dim_cnae`](dicionario-dados.md#dim_cnae)`.codigo_classe` ×
  [`dim_municipio`](dicionario-dados.md#dim_municipio). Universo: os pares município × classe com unidade local no
  CEMPRE ou ativo na RFB (o grão de [`mart_emprego_setor_municipio`](dicionario-dados.md#mart_emprego_setor_municipio)),
  sem município e CNAE desconhecidos (-1), por UF e faixa da razão unidades CEMPRE ÷ ativos RFB sem MEI. Só entram
  as classes do CEMPRE que existem na CNAE da RFB (`dim_cnae.codigo_classe`): no dado real, 2 das 673 não existem,
  70.10-7 ("Sedes de empresas e unidades administrativas locais", 92 unidades no Brasil) e 47.90-3 (nenhuma
  unidade), e uma classe sem par nunca teria ativo na RFB: seria violação estrutural, não divergência. No
  `mart_emprego_setor_municipio` esses pares ficam, com a descrição da classe pelo CEMPRE. Lê o
  CEMPRE pela fonte, e não pelo staging, para rodar sobre um warehouse que ainda não tem os modelos do IBGE.
  Sem `ibge/` (modo offline) o CEMPRE é vazio e a regra avalia só os pares da RFB, sem violação.
- **Conceito:** [CEMPRE](camada-semantica.md#cempre-unidades-locais-e-pessoal-ocupado) e
  [CNAE principal e secundárias](camada-semantica.md#cnae-principal-e-secundárias).
- **Leitura de uma violação:** divergência de classificação CNAE entre o IBGE e a RFB (a unidade está noutra classe
  no CNPJ) ou defasagem do cadastro (unidades encerradas entre 31/12 e o mês do extrato), sem afirmar qual. Não é
  erro de nenhuma das bases. Faixas: `sem ativo RFB sem MEI` (onde as violações estão), `sem unidade no CEMPRE`, e
  as razões `< 0,5`, `de 0,5 a 2` e `> 2`.
- **Fixtures e injeção:** nas fixtures, as classes do CEMPRE de Serra, Vitória, Linhares e Aracruz em 47.41-5 e de
  Fundão em 47.11-3 e 47.44-0 têm 3 ou mais unidades sem ativo RFB sem MEI (Serra só tem um MEI: é o caso que separa
  "com MEI" de "sem MEI"); Aracruz tem exatamente 3 (a fronteira). Os casos injetados em
  `tests/integration/test_regras_negocio.py` põem um ativo sem MEI onde havia violação (sai da violação e muda de
  faixa), um MEI (não muda nada) e um ativo numa classe sem CEMPRE (entra no universo sem violar). Serra tem 4
  unidades em 20.51-7 e Aracruz 1 em 35.11-5, classes que não estão na CNAE das fixtures: ficam fora da regra (como
  a 70.10-7 no real), e a de Serra seria violação.
- **Analysis:** `transform/analyses/regras_negocio/rn_30_cempre_coerente_com_rfb.sql`.

## Fontes

Conferidas em **2026-10-13** (texto lido na fonte, não só citado). As linhas LC 128, CONCLA e CGSN 190/194 e os
trechos novos da LC 123 (art. 88) e da IN 2.119 (art. 21, IV) entraram com o lote FRN (RRN-02, RRN-08). As chaves são as da
[A7 da camada semântica](camada-semantica.md#a7-fontes), onde estão as demais.

| Chave | Fonte | O que sustenta aqui |
|---|---|---|
| RFB-Leiaute | Receita Federal, [Novo Layout dos Dados Abertos do CNPJ](https://www.gov.br/receitafederal/dados/cnpj-metadados.pdf) (PDF, 6 p.) | CNAE fiscal principal e secundárias, separadas por vírgula (RN-01 a RN-04); campos de data e motivo da situação, situação especial (RN-10 a RN-15); opção e datas do Simples e do MEI (RN-06, RN-09); porte (RN-07); identificador matriz/filial (RN-16); município de jurisdição e domínio de municípios (RN-19); ente federativo só no grupo 1XXX (RN-20); capital social (RN-21) |
| LC 123 | [Lei Complementar nº 123/2006](https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp123.htm), texto compilado do Planalto | MEI "optante pelo Simples Nacional" (art. 18-A, § 1º, RN-06); MEI "seja empresário individual [...] ou o empreendedor" (art. 18-A, § 1º, redação da LC 188/2021, RN-29); MEI "que possua mais de um estabelecimento" não pode optar pelo SIMEI (art. 18-A, § 4º, II, RN-05); "O MEI é modalidade de microempresa" (art. 18-E, § 3º, incluído pela LC 147/2014, RN-07); o regime "entra em vigor em 1º de julho de 2007" (art. 88, RN-25) |
| LC 128 | [Lei Complementar nº 128/2008](https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp128.htm), Planalto | os arts. 18-A a 18-C da LC 123 (SIMEI) "produzirão efeitos a partir de 1º de julho de 2009" (art. 14, III, RN-26) |
| IN 2.119 | [Instrução Normativa RFB nº 2.119/2022](http://normas.receita.fazenda.gov.br/sijut2consulta/link.action?idAto=127567), texto multivigente | formato alfanumérico (art. 2º, parágrafo único, RN-17); hipóteses de baixa e efeitos desde o evento (art. 24, caput e § 1º, RN-10, RN-11); baixa da matriz implica a das filiais (art. 24, § 2º, RN-14); nulidade com efeito "a partir do termo inicial de vigência do ato cadastral declarado nulo" (art. 34, parágrafo único, RN-14); a matriz baixada, inapta ou nula impede a inscrição de filial (art. 21, IV, RN-27) |
| RFB-Alfanumérico | Receita Federal, [Perguntas e respostas: CNPJ alfanumérico](https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/perguntas-e-respostas/cnpj/cnpj-alfanumerico.pdf) | DV pelo módulo 11; números atuais e seus DV continuam válidos (RN-17) |
| RFB-Motivos | Tabela de motivos da situação cadastral publicada com os dados abertos (`Motivos.zip`, extrato de 2026-09; fonte `rfb.motivos`) | descrição dos motivos 00 a 93 (RN-10). Não é norma: é o domínio do próprio cadastro |
| CGSN 190 | Resolução CGSN nº 190/2026, publicada em 10/08/2026 (listada no [Sijut, resoluções do CGSN](https://normas.receita.fazenda.gov.br/sijut2consulta/consulta.action?lblTiposAtosSelecionados=Res.&orgaosSelecionados=CGSN&tipoData=2&tiposAtosSelecionados=67)), lida na notícia oficial da Receita Federal [CGSN atualiza regras do Simples Nacional](https://www.gov.br/receitafederal/pt-br/assuntos/noticias/2026/agosto/cgsn-atualiza-regras-do-simples-nacional-para-adequacao-a-reforma-tributaria-do-consumo) | a opção feita em setembro de 2026 é "para produzir efeitos a partir de 1º de janeiro do ano seguinte" (RN-13). O texto da resolução não foi aberto: o Sijut só a lista |
| CGSN 194 | Resolução CGSN nº 194/2026, publicada no DOU de 28/09/2026 (listada no Sijut, como a 190), lida na notícia oficial da Receita Federal [Simples Nacional 2027: entenda os novos prazos](https://www.gov.br/receitafederal/pt-br/assuntos/noticias/2026/setembro/simples-nacional-2027-entenda-os-novos-prazos-e-faca-sua-escolha-com-consciencia-e-tranquilidade) | opção para 2027 de 1º/9 a 15/10/2026; "A opção, quando confirmada, produzirá efeitos a partir de 1º de janeiro de 2027" (RN-13) |
| CONCLA | IBGE/CONCLA, [Tabela de Natureza Jurídica 2021](https://concla.ibge.gov.br/estrutura/natjur-estrutura/natureza-juridica-2021.html) | os códigos e nomes das naturezas de sociedade (RN-29) |
| IBGE-CEMPRE | IBGE, [Estatísticas do Cadastro Central de Empresas 2024](https://agenciadenoticias.ibge.gov.br/media/com_mediaibge/arquivos/e1be87301fe780c6ccf8aeab200e71ea.pdf) (apresentação, "Notas técnicas"; conferida em 2026-10-14) | fontes do CEMPRE (CNPJ, RAIS, CAGED, eSocial e as pesquisas anuais do IBGE, que prevalecem); critérios de unidade ativa (eSocial, pesquisas ou CNPJ ativo em 31.12 sem indicativo de inatividade); exclusão dos MEI; quebra de série em 2022; 71,6 % das empresas sem assalariado em 31.12 (RN-30) |

**Não confirmado.** Nenhuma fonte diz que o ATIVO tem motivo 00, que o não ativo tem data da situação, que a
situação não antecede o início de atividade, que os CNAEs secundários não repetem o principal, que há uma única
matriz por CNPJ básico ou que a filial não começa atividade depois do fim da matriz (a IN fala da inscrição): por
isso RN-03, RN-04, RN-09 a RN-13, RN-15, RN-16, RN-21 e RN-27 são "coerência do projeto" ou "estrutural". O corte
D+1 da RN-13 é medido no dado, não documentado pela RFB. A natureza 213-5 do MEI (RN-08) e a opção antes do início
de atividade (RN-28) são observações, não regras, assim como a coerência entre o CEMPRE e a RFB (RN-30).
