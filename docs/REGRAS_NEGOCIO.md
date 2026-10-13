# Regras de negócio do cadastro CNPJ

> **Adição** ([ADR-0020](adr/0020-regras-de-negocio.md)). Este catálogo lista as regras e invariantes que o cadastro
> CNPJ deveria cumprir e diz de onde vem cada uma. Cada regra tem uma analysis em
> `transform/analyses/regras_negocio/` que conta quantos registros a cumprem e quantos a violam. O resultado do dado
> real está em [`RELATORIO_REGRAS_NEGOCIO.md`](RELATORIO_REGRAS_NEGOCIO.md).

## Como usar

- `make regras` (ou `uv run rfb regras`) compila as analyses, executa-as no `warehouse.duckdb` de `RAIZ_DADOS`
  **somente leitura** e escreve `docs/RELATORIO_REGRAS_NEGOCIO.md` (`SAIDA=<arquivo>` / `--saida` muda o
  destino). Rode depois de um `dbt build` do mês ([OPERACAO.md](OPERACAO.md)).
- **Violação não é erro.** O comando sai com 0 mesmo com regras violadas. Só falha quando a execução falha:
  compilação, consulta, linha fora do padrão ou desencontro entre este catálogo e as analyses. Os checks **não**
  entram no `dbt build`: não derrubam nem atrasam a atualização mensal.
- **Só contagens.** Cada analysis devolve `regra`, `avaliados` (o universo da regra), `violacoes` e, se for o
  caso, uma quebra agregada (situação cadastral, porte, natureza jurídica, campo, tabela…). Nunca CNPJ, nome ou
  CPF ([ADR-0008](adr/0008-minimizacao-dados-pessoais.md)); o `rfb regras` recusa colunas fora da lista de
  quebras e valores com 11 ou 14 dígitos seguidos.
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
  empresa (CNPJ básico) com opção pelo MEI no arquivo Simples. Junto vêm as regras vizinhas do MEI: optante do
  Simples ([RN-06](#rn-06)), microempresa ([RN-07](#rn-07)), natureza jurídica ([RN-08](#rn-08), observação) e datas
  ([RN-09](#rn-09)).
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
  - [RN-13](#rn-13): nenhuma data de evento é posterior à data do extrato.

  "Empresa" foi lida como estabelecimento, porque a situação cadastral é do estabelecimento
  ([CAMADA_SEMANTICA, A3](CAMADA_SEMANTICA.md#a3-ciclo-de-vida)). A situação da empresa é a da matriz, e a regra
  da matriz para as filiais é a [RN-14](#rn-14).

## Catálogo

Colunas no formato tabela.coluna, com link para o [dicionário de dados](DICIONARIO_DADOS.md). As fontes entre
colchetes estão em [Fontes](#fontes).

### Atividade econômica (CNAE)

<a id="rn-01"></a>
### RN-01 — Estabelecimento tem CNAE principal do domínio

- **Enunciado:** todo estabelecimento tem um CNAE fiscal principal preenchido, e o código existe no domínio de
  CNAEs publicado pela RFB.
- **Tipo:** leiaute/cadastro.
- **Fonte:** [RFB-Leiaute], campo "CNAE FISCAL PRINCIPAL – código da atividade econômica principal do
  estabelecimento" (no singular) e domínio "CNAEs".
- **Dados:** [`int_estabelecimentos__enriquecidos`](DICIONARIO_DADOS.md#int_estabelecimentos__enriquecidos)`.cnae_principal`
  × [`stg_rfb__cnaes`](DICIONARIO_DADOS.md#stg_rfb__cnaes)`.codigo`. Universo: estabelecimentos do mês, por
  situação.
- **Conceito:** [CNAE principal e secundárias](CAMADA_SEMANTICA.md#cnae-principal-e-secundárias); ontologia
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
- **Conceito:** [CNAE principal e secundárias](CAMADA_SEMANTICA.md#cnae-principal-e-secundárias); ontologia
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
- **Conceito:** [CNAE principal e secundárias](CAMADA_SEMANTICA.md#cnae-principal-e-secundárias).
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
- **Conceito:** [CNAE principal e secundárias](CAMADA_SEMANTICA.md#cnae-principal-e-secundárias). A ponte
  [`bridge_estabelecimento_cnae_secundario`](DICIONARIO_DADOS.md#bridge_estabelecimento_cnae_secundario) tem uma linha
  por par: repetições na lista viram uma linha só.
- **Leitura de uma violação:** erro de dado da RFB.
- **Analysis:** `transform/analyses/regras_negocio/rn_04_cnae_secundario_sem_repeticao.sql`.

### Simples Nacional e MEI

<a id="rn-05"></a>
### RN-05 — MEI tem um único estabelecimento

- **Enunciado:** a empresa com opção pelo MEI tem um único estabelecimento no extrato.
- **Tipo:** legal.
- **Fonte:** [LC 123], art. 18-A, § 4º, II: não pode optar pelo SIMEI o MEI "que possua mais de um estabelecimento".
- **Dados:** [`stg_rfb__simples`](DICIONARIO_DADOS.md#stg_rfb__simples)`.opcao_mei` × estabelecimentos do mesmo
  CNPJ básico em `int_estabelecimentos__enriquecidos`. Universo: empresas (CNPJ básico) com opção pelo MEI, pela
  quantidade de estabelecimentos; a quebra separa as violações em que só um estabelecimento não está baixado.
- **Conceito:** [Simples Nacional e MEI](CAMADA_SEMANTICA.md#simples-nacional-e-mei); ontologia `rfbo:OpcaoMEI`.
- **Leitura de uma violação:** se os estabelecimentos além de um estão baixados, é comportamento conhecido do
  cadastro (o estabelecimento baixado continua no extrato) e não contraria a lei. Se há mais de um não baixado, é
  erro de dado ou desenquadramento ainda não registrado (defasagem). A RSEM já tinha visto 3.749 filiais de MEI no
  dado real de 2026-09.
- **Analysis:** `transform/analyses/regras_negocio/rn_05_mei_estabelecimento_unico.sql`.

<a id="rn-06"></a>
### RN-06 — MEI é optante do Simples Nacional

- **Enunciado:** quem tem opção pelo MEI tem também opção pelo Simples Nacional.
- **Tipo:** legal.
- **Fonte:** [LC 123], art. 18-A, § 1º: considera-se MEI quem "seja optante pelo Simples Nacional".
- **Dados:** `stg_rfb__simples.opcao_mei` e `.opcao_simples`. Universo: empresas com opção pelo MEI.
- **Conceito:** [Simples Nacional e MEI](CAMADA_SEMANTICA.md#simples-nacional-e-mei). O build já tem o teste
  equivalente na fato (`not opcao_mei or opcao_simples`); aqui a regra é contada na fonte.
- **Leitura de uma violação:** erro de dado ou defasagem entre as duas opções do mesmo arquivo.
- **Analysis:** `transform/analyses/regras_negocio/rn_06_mei_optante_simples.sql`.

<a id="rn-07"></a>
### RN-07 — MEI tem porte de microempresa

- **Enunciado:** a empresa com opção pelo MEI tem o porte 01 (MICRO EMPRESA) no arquivo Empresas.
- **Tipo:** legal.
- **Fonte:** [LC 123], art. 18-E, § 3º: "O MEI é modalidade de microempresa." Códigos de porte: [RFB-Leiaute].
- **Dados:** `stg_rfb__simples.opcao_mei` × [`stg_rfb__empresas`](DICIONARIO_DADOS.md#stg_rfb__empresas)`.porte_codigo`.
  Universo: empresas MEI presentes no arquivo Empresas, por porte declarado.
- **Conceito:** [Porte](CAMADA_SEMANTICA.md#porte) ("o porte é declarado, não medido") e
  [Simples Nacional e MEI](CAMADA_SEMANTICA.md#simples-nacional-e-mei).
- **Leitura de uma violação:** o porte é declarado no registro e não acompanha a opção pelo MEI; uma violação é
  comportamento conhecido do cadastro (porte desatualizado) mais provável que erro.
- **Analysis:** `transform/analyses/regras_negocio/rn_07_mei_porte_micro.sql`.

<a id="rn-08"></a>
### RN-08 — MEI tem natureza 213-5 (observação)

- **Enunciado:** a empresa com opção pelo MEI tem a natureza jurídica 213-5 Empresário (Individual).
- **Tipo:** coerência do projeto.
- **Fonte:** observação do projeto, **não regra**. A LC 123 define o MEI como empresário individual **ou** o
  empreendedor de certas atividades (art. 18-A, § 1º) e a CONCLA não associa o MEI a uma natureza (RSEM-06).
- **Dados:** `stg_rfb__simples.opcao_mei` × `stg_rfb__empresas.natureza_juridica_codigo` e
  [`stg_rfb__naturezas`](DICIONARIO_DADOS.md#stg_rfb__naturezas). Universo: empresas MEI no arquivo Empresas.
- **Conceito:** [Natureza jurídica](CAMADA_SEMANTICA.md#natureza-jurídica) ("MEI não é natureza jurídica").
- **Leitura de uma violação:** não é erro por si; mostra quantas empresas MEI têm outra natureza (a RSEM viu 1.238
  estabelecimentos com natureza de sociedade em 2026-09).
- **Analysis:** `transform/analyses/regras_negocio/rn_08_mei_natureza_empresario_individual.sql`.

<a id="rn-09"></a>
### RN-09 — Exclusão do regime não antecede a opção

- **Enunciado:** quando o registro do Simples tem data de opção e data de exclusão do mesmo regime, a exclusão não
  é anterior à opção. Vale para o Simples Nacional e para o MEI.
- **Tipo:** coerência do projeto.
- **Fonte:** regra do projeto sobre os campos "data de opção" e "data de exclusão" de cada regime [RFB-Leiaute].
- **Dados:** `stg_rfb__simples.dat_opcao_simples`, `.dat_exclusao_simples`, `.dat_opcao_mei`, `.dat_exclusao_mei`.
  Universo: registros com as duas datas, por regime.
- **Conceito:** [Simples Nacional e MEI](CAMADA_SEMANTICA.md#simples-nacional-e-mei).
- **Leitura de uma violação:** o arquivo guarda uma opção e uma exclusão por regime. Uma nova opção depois de uma
  exclusão pode deixar a exclusão antiga com a opção nova (comportamento do cadastro); sem reopção, é erro de dado.
- **Analysis:** `transform/analyses/regras_negocio/rn_09_simples_exclusao_apos_opcao.sql`.

### Situação cadastral e datas

<a id="rn-10"></a>
### RN-10 — Motivo coerente com a situação

- **Enunciado:** o estabelecimento ATIVO tem o motivo 00 (SEM MOTIVO), e o estabelecimento não ativo tem um motivo
  diferente de 00. Motivo vazio conta como 00.
- **Tipo:** coerência do projeto.
- **Fonte:** regra do projeto, apoiada na tabela de motivos que a RFB publica com os dados abertos (o leiaute só diz
  "código do motivo da situação cadastral" [RFB-Leiaute]) e nas hipóteses de baixa do [IN 2.119], art. 24. Veja a
  [tradução](#traduções-das-regras-pedidas).
- **Dados:** [`stg_rfb__estabelecimentos`](DICIONARIO_DADOS.md#stg_rfb__estabelecimentos)`.situacao_codigo` e
  `.motivo_situacao_codigo`; [`stg_rfb__motivos`](DICIONARIO_DADOS.md#stg_rfb__motivos). Universo: todos os
  estabelecimentos, por situação.
- **Conceito:** [Situação cadastral](CAMADA_SEMANTICA.md#situação-cadastral); ontologia
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
- **Conceito:** [Situação cadastral](CAMADA_SEMANTICA.md#situação-cadastral) e
  [A3](CAMADA_SEMANTICA.md#a3-ciclo-de-vida): sem data, o estabelecimento não entra em `encerramentos` nem `baixas`.
- **Leitura de uma violação:** erro de dado. O ATIVO sem data fica fora da regra (a RSEM viu 115.651 em 2026-09).
- **Analysis:** `transform/analyses/regras_negocio/rn_11_inativo_com_data_situacao.sql`.

<a id="rn-12"></a>
### RN-12 — Situação não antecede o início de atividade

- **Enunciado:** a data da situação cadastral não é anterior à data de início de atividade do estabelecimento.
- **Tipo:** coerência do projeto.
- **Fonte:** regra do projeto sobre os campos de data do [RFB-Leiaute].
- **Dados:** `int_estabelecimentos__enriquecidos.dat_situacao` e `.dat_inicio_atividade`. Universo: estabelecimentos
  com as duas datas, por situação.
- **Conceito:** [Data de início de atividade](CAMADA_SEMANTICA.md#data-de-início-de-atividade).
- **Leitura de uma violação:** erro de dado ou data de início corrigida depois do evento. Distorce idade, coortes e
  `mart_dinamica_mercado` (encerramento antes da abertura).
- **Analysis:** `transform/analyses/regras_negocio/rn_12_situacao_apos_inicio_atividade.sql`.

<a id="rn-13"></a>
### RN-13 — Datas de evento não são futuras

- **Enunciado:** nenhuma data de evento já ocorrido é posterior à data do extrato: início de atividade, situação
  cadastral, situação especial, opção pelo Simples e opção pelo MEI.
- **Tipo:** coerência do projeto.
- **Fonte:** regra do projeto ([ADR-0004](adr/0004-data-referencia-deterministica.md)). As datas de **exclusão** ficam
  de fora: podem ter efeito futuro legítimo (R3-11). A opção pelo Simples pode anteceder os efeitos [CGSN 190], mas
  não o extrato.
- **Dados:** `int_estabelecimentos__enriquecidos.dat_inicio_atividade`, `.dat_situacao`;
  `stg_rfb__estabelecimentos.dat_situacao_especial`; `stg_rfb__simples.dat_opcao_simples`, `.dat_opcao_mei`;
  `_data_referencia`. Universo: valores preenchidos de cada campo.
- **Conceito:** [Data de início de atividade](CAMADA_SEMANTICA.md#data-de-início-de-atividade). O build já avisa
  (`data_nao_futura`, warn) nas colunas de staging; aqui a regra é contada por campo.
- **Leitura de uma violação:** erro de digitação de data ou evento agendado (defasagem: o extrato registra um ato
  com data posterior).
- **Analysis:** `transform/analyses/regras_negocio/rn_13_datas_nao_futuras.sql`.

<a id="rn-14"></a>
### RN-14 — Matriz baixada, filiais baixadas

- **Enunciado:** se a matriz de uma empresa está BAIXADA, todas as filiais dela estão BAIXADAS.
- **Tipo:** legal.
- **Fonte:** [IN 2.119], art. 24, § 2º: "A baixa da inscrição do estabelecimento matriz no CNPJ implica baixa de
  todas as inscrições dos estabelecimentos filiais da entidade."
- **Dados:** `int_estabelecimentos__enriquecidos.cnpj_raiz`, `.matriz_filial_codigo`, `.situacao_codigo`. Universo:
  filiais de empresas com matriz baixada, pela situação da filial.
- **Conceito:** [Matriz × filial](CAMADA_SEMANTICA.md#matriz--filial); ontologia `rfbo:Matriz`, `rfbo:Filial`.
- **Leitura de uma violação:** defasagem (a baixa da filial ainda não refletida no extrato), filial transformada em
  matriz [IN 2.119, art. 4º, § 3º] ou erro de dado. A filial **NULA** é um limite da tradução: a nulidade do ato
  cadastral vale desde o início da inscrição [IN 2.119, art. 34, parágrafo único], então não há inscrição a baixar;
  a quebra por situação a separa das demais.
- **Analysis:** `transform/analyses/regras_negocio/rn_14_matriz_baixada_filiais_baixadas.sql`.

<a id="rn-15"></a>
### RN-15 — Situação especial e data andam juntas

- **Enunciado:** a situação especial e a data da situação especial estão as duas preenchidas ou as duas vazias.
- **Tipo:** coerência do projeto.
- **Fonte:** regra do projeto sobre os campos "situação especial da empresa" e "data em que a empresa entrou em
  situação especial" [RFB-Leiaute].
- **Dados:** `stg_rfb__estabelecimentos.situacao_especial` e `.dat_situacao_especial`. Universo: todos os
  estabelecimentos, por situação.
- **Conceito:** [Situação especial](CAMADA_SEMANTICA.md#situação-especial).
- **Leitura de uma violação:** erro de dado.
- **Analysis:** `transform/analyses/regras_negocio/rn_15_situacao_especial_com_data.sql`.

### Estrutura do cadastro

<a id="rn-16"></a>
### RN-16 — Uma matriz por CNPJ básico

- **Enunciado:** cada CNPJ básico do arquivo Estabelecimentos tem exatamente uma matriz.
- **Tipo:** estrutural.
- **Fonte:** regra do projeto, a leitura de [Matriz × filial](CAMADA_SEMANTICA.md#matriz--filial): o identificador
  1/2 [RFB-Leiaute] e a inscrição dos entes "na condição de estabelecimento matriz" [IN 2.119, art. 4º, § 1º]. Não
  há texto que diga "uma matriz por entidade".
- **Dados:** `int_estabelecimentos__enriquecidos.cnpj_raiz` e `.matriz_filial_codigo`. Universo: CNPJs básicos, pelo
  número de matrizes (0, 1, 2 ou mais).
- **Conceito:** [Empresa × estabelecimento](CAMADA_SEMANTICA.md#empresa--estabelecimento): `qtd_matrizes` conta
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
- **Conceito:** [CNPJ](CAMADA_SEMANTICA.md#cnpj).
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
- **Conceito:** [Empresa × estabelecimento](CAMADA_SEMANTICA.md#empresa--estabelecimento).
- **Leitura de uma violação:** defasagem entre os arquivos do mês ou erro de dado. O estabelecimento sem empresa
  fica com natureza e porte -1 na estrela e é descartado por `bh_empresas` (inner join do original).
- **Analysis:** `transform/analyses/regras_negocio/rn_18_estabelecimento_com_empresa.sql`.

<a id="rn-19"></a>
### RN-19 — Município do domínio da RFB

- **Enunciado:** o código de município do estabelecimento existe no domínio de municípios publicado pela RFB.
- **Tipo:** leiaute/cadastro.
- **Fonte:** [RFB-Leiaute], campo "MUNICÍPIO – código do município de jurisdição onde se encontra o
  estabelecimento" e domínio "MUNICÍPIOS".
- **Dados:** `int_estabelecimentos__enriquecidos.municipio_rfb_codigo` × [`stg_rfb__municipios`](DICIONARIO_DADOS.md#stg_rfb__municipios)`.codigo`.
  Universo: estabelecimentos, por situação.
- **Conceito:** [Município: código RFB × código IBGE](CAMADA_SEMANTICA.md#município-código-rfb--código-ibge). É o
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
- **Dados:** `stg_rfb__empresas.natureza_juridica_codigo` e `.ente_federativo_responsavel`. Universo: empresas, pelo
  grupo da natureza; natureza vazia conta como "demais".
- **Conceito:** [Natureza jurídica](CAMADA_SEMANTICA.md#natureza-jurídica).
- **Leitura de uma violação:** no grupo 1, ente vazio é erro de dado (ou órgão sem ente no cadastro); fora dele,
  ente preenchido é erro de dado ou natureza alterada sem limpar o campo.
- **Analysis:** `transform/analyses/regras_negocio/rn_20_ente_federativo_natureza_publica.sql`.

<a id="rn-21"></a>
### RN-21 — Capital social não negativo

- **Enunciado:** o capital social da empresa não é negativo.
- **Tipo:** coerência do projeto.
- **Fonte:** regra do projeto sobre o campo "capital social da empresa" [RFB-Leiaute].
- **Dados:** `stg_rfb__empresas.capital_social` e `.porte_codigo`. Universo: empresas com capital preenchido, por
  porte.
- **Conceito:** [Capital social](CAMADA_SEMANTICA.md#capital-social): `capital_social_total` soma só as matrizes.
- **Leitura de uma violação:** erro de dado ou de conversão do separador decimal.
- **Analysis:** `transform/analyses/regras_negocio/rn_21_capital_social_nao_negativo.sql`.

### Grãos declarados sem teste (RDIC-09)

O dicionário de dados declara o grão de cada tabela e diz quando ele não é testado
([RDIC-09](revisoes/RDIC.md)). Estas regras contam as linhas excedentes (linhas − chaves distintas) sem acrescentar
testes ao build.

<a id="rn-22"></a>
### RN-22 — Simples: uma linha por CNPJ básico

- **Enunciado:** o arquivo Simples tem uma linha por CNPJ básico no mês selecionado.
- **Tipo:** estrutural.
- **Fonte:** regra do projeto, o grão declarado de [`rfb.simples`](DICIONARIO_DADOS.md#rfb-simples) ("empresa
  (`cnpj_raiz`) por mês de referência").
- **Dados:** `stg_rfb__simples.cnpj_raiz` (a fonte já filtrada pelo mês). Universo: linhas do mês.
- **Conceito:** [Simples Nacional e MEI](CAMADA_SEMANTICA.md#simples-nacional-e-mei).
- **Leitura de uma violação:** arquivo duplicado na pasta do mês ou erro de dado; a raiz repetida multiplicaria
  estabelecimentos no left join de `int_estabelecimentos__enriquecidos`.
- **Analysis:** `transform/analyses/regras_negocio/rn_22_grao_simples.sql`.

<a id="rn-23"></a>
### RN-23 — Grão dos marts

- **Enunciado:** os marts sem teste de unicidade têm uma linha por combinação do grão declarado:
  [`agg_empresas`](DICIONARIO_DADOS.md#agg_empresas) (as 10 dimensões do original),
  [`mart_dinamica_mercado`](DICIONARIO_DADOS.md#mart_dinamica_mercado) (`ano`, `sk_cnae`, `sk_municipio`) e
  [`mart_sobrevivencia_coorte`](DICIONARIO_DADOS.md#mart_sobrevivencia_coorte) (`ano_coorte`, `sk_cnae`, `sk_porte`,
  `uf`).
- **Tipo:** estrutural.
- **Fonte:** regra do projeto (`meta.grao` dos modelos).
- **Dados:** as três tabelas do gold. Universo: linhas de cada tabela.
- **Conceito:** [A3](CAMADA_SEMANTICA.md#a3-ciclo-de-vida) (aberturas, encerramentos, coortes).
- **Leitura de uma violação:** limite do projeto (erro de modelagem: um `group by` sem uma das chaves).
- **Analysis:** `transform/analyses/regras_negocio/rn_23_grao_marts.sql`.

<a id="rn-24"></a>
### RN-24 — Grão das fontes e domínios

- **Enunciado:** as fontes e o seed sem teste de unicidade têm uma linha por chave do grão declarado:
  [`rfb.paises`](DICIONARIO_DADOS.md#rfb-paises) e [`rfb.qualificacoes`](DICIONARIO_DADOS.md#rfb-qualificacoes)
  (`codigo` por mês), [`basedosdados.cnae_2`](DICIONARIO_DADOS.md#basedosdados-cnae_2) (`subclasse`),
  [`basedosdados.regiao_metropolitana_2017`](DICIONARIO_DADOS.md#basedosdados-regiao_metropolitana_2017) (município ×
  região), [`basedosdados.vizinhanca_municipio`](DICIONARIO_DADOS.md#basedosdados-vizinhanca_municipio) (`ano`,
  `id_municipio_1`, `id_municipio_2`, como publicada), [`excecoes_conhecidas_municipio`](DICIONARIO_DADOS.md#excecoes_conhecidas_municipio)
  (`codigo`) e [`observabilidade.dq_historico_testes`](DICIONARIO_DADOS.md#observabilidade-dq_historico_testes)
  (`invocation_id`, `nome_teste`).
- **Tipo:** estrutural.
- **Fonte:** regra do projeto (`meta.grao` das fontes e do seed).
- **Dados:** as sete tabelas. Universo: linhas de cada tabela.
- **Conceito:** [A1](CAMADA_SEMANTICA.md#a1-as-bases).
- **Leitura de uma violação:** na vizinhança é comportamento conhecido da fonte: o grão declarado avisa que ela
  "pode repetir o par" e a ponte `bridge_municipio_vizinho` deduplica (RDIC-02). Nas demais, erro de dado da fonte
  ou arquivo duplicado.
- **Analysis:** `transform/analyses/regras_negocio/rn_24_grao_fontes_e_dominios.sql`.

## Fontes

Conferidas em **2026-10-13** (texto lido na fonte, não só citado). As chaves são as da
[A7 da camada semântica](CAMADA_SEMANTICA.md#a7-fontes), onde estão as demais.

| Chave | Fonte | O que sustenta aqui |
|---|---|---|
| RFB-Leiaute | Receita Federal, [Novo Layout dos Dados Abertos do CNPJ](https://www.gov.br/receitafederal/dados/cnpj-metadados.pdf) (PDF, 6 p.) | CNAE fiscal principal e secundárias, separadas por vírgula (RN-01 a RN-04); campos de data e motivo da situação, situação especial (RN-10 a RN-15); opção e datas do Simples e do MEI (RN-06, RN-09); porte (RN-07); identificador matriz/filial (RN-16); município de jurisdição e domínio de municípios (RN-19); ente federativo só no grupo 1XXX (RN-20); capital social (RN-21) |
| LC 123 | [Lei Complementar nº 123/2006](https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp123.htm), texto compilado do Planalto | MEI "optante pelo Simples Nacional" (art. 18-A, § 1º, RN-06); MEI "que possua mais de um estabelecimento" não pode optar pelo SIMEI (art. 18-A, § 4º, II, RN-05); "O MEI é modalidade de microempresa" (art. 18-E, § 3º, incluído pela LC 147/2014, RN-07) |
| IN 2.119 | [Instrução Normativa RFB nº 2.119/2022](http://normas.receita.fazenda.gov.br/sijut2consulta/link.action?idAto=127567), texto multivigente | formato alfanumérico (art. 2º, parágrafo único, RN-17); hipóteses de baixa e efeitos desde o evento (art. 24, caput e § 1º, RN-10, RN-11); baixa da matriz implica a das filiais (art. 24, § 2º, RN-14); nulidade com efeito desde o início do ato (art. 34, RN-14) |
| RFB-Alfanumérico | Receita Federal, [Perguntas e respostas: CNPJ alfanumérico](https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/perguntas-e-respostas/cnpj/cnpj-alfanumerico.pdf) | DV pelo módulo 11; números atuais e seus DV continuam válidos (RN-17) |
| RFB-Motivos | Tabela de motivos da situação cadastral publicada com os dados abertos (`Motivos.zip`, extrato de 2026-09; fonte `rfb.motivos`) | descrição dos motivos 00 a 93 (RN-10). Não é norma: é o domínio do próprio cadastro |
| CGSN 190 | Resolução CGSN nº 190/2026 (ver [A7](CAMADA_SEMANTICA.md#a7-fontes)) | opção pelo Simples antes do início dos efeitos (RN-13); não reconferida neste lote |

**Não confirmado.** Nenhuma fonte diz que o ATIVO tem motivo 00, que o não ativo tem data da situação, que a
situação não antecede o início de atividade, que os CNAEs secundários não repetem o principal ou que há uma única
matriz por CNPJ básico: por isso RN-03, RN-04, RN-09 a RN-13, RN-15, RN-16 e RN-21 são "coerência do projeto" ou
"estrutural". A natureza 213-5 do MEI (RN-08) é observação, não regra.
