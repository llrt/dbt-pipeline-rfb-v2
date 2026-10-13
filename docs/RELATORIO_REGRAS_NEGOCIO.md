# Relatório das regras de negócio — 2026-09

> Mês de referência **2026-09** (extrato de 2026-09-12). Gerado por `rfb regras` a partir das analyses `transform/analyses/regras_negocio/` e do catálogo [`docs/REGRAS_NEGOCIO.md`](REGRAS_NEGOCIO.md); não edite à mão acima da seção "Interpretação". Só contagens: nenhum CNPJ, nome ou CPF ([ADR-0008](adr/0008-minimizacao-dados-pessoais.md)). Inconsistências não falham o comando nem o build ([ADR-0020](adr/0020-regras-de-negocio.md)).

## Resumo

**29** regras avaliadas: **13** sem violação e **16** com violação.

| Regra | Enunciado | Tipo | Avaliados | Violações | % |
|---|---|---|---:|---:|---:|
| [RN-01](REGRAS_NEGOCIO.md#rn-01) | Estabelecimento tem CNAE principal do domínio | leiaute/cadastro | 73.366.147 | 0 | 0 % |
| [RN-02](REGRAS_NEGOCIO.md#rn-02) | CNAEs secundários são do domínio | leiaute/cadastro | 125.425.117 | 0 | 0 % |
| [RN-03](REGRAS_NEGOCIO.md#rn-03) | CNAE secundário não repete o principal | coerência do projeto | 125.425.117 | 3.310 | < 0,01 % |
| [RN-04](REGRAS_NEGOCIO.md#rn-04) | CNAEs secundários não se repetem | coerência do projeto | 34.670.077 | 3.488 | 0,01 % |
| [RN-05](REGRAS_NEGOCIO.md#rn-05) | MEI tem um único estabelecimento não baixado | legal | 17.523.665 | 33 | < 0,01 % |
| [RN-06](REGRAS_NEGOCIO.md#rn-06) | MEI é optante do Simples Nacional | legal | 17.523.665 | 469 | < 0,01 % |
| [RN-07](REGRAS_NEGOCIO.md#rn-07) | MEI tem porte de microempresa | legal | 17.523.665 | 110 | < 0,01 % |
| [RN-08](REGRAS_NEGOCIO.md#rn-08) | MEI tem natureza 213-5 (observação) | coerência do projeto | 17.523.665 | 1.236 | < 0,01 % |
| [RN-09](REGRAS_NEGOCIO.md#rn-09) | Exclusão do regime não antecede a opção | coerência do projeto | 45.280.511 | 6 | < 0,01 % |
| [RN-10](REGRAS_NEGOCIO.md#rn-10) | Motivo coerente com a situação | coerência do projeto | 73.366.147 | 1 | < 0,01 % |
| [RN-11](REGRAS_NEGOCIO.md#rn-11) | Não ativo tem data da situação | coerência do projeto | 45.103.026 | 0 | 0 % |
| [RN-12](REGRAS_NEGOCIO.md#rn-12) | Situação não antecede o início de atividade | coerência do projeto | 73.250.497 | 1.058 | < 0,01 % |
| [RN-13](REGRAS_NEGOCIO.md#rn-13) | Datas de evento não passam do extrato | coerência do projeto | 234.136.725 | 0 | 0 % |
| [RN-14](REGRAS_NEGOCIO.md#rn-14) | Matriz baixada, filiais baixadas ou nulas | legal | 765.465 | 159 | 0,02 % |
| [RN-15](REGRAS_NEGOCIO.md#rn-15) | Situação especial e data andam juntas | coerência do projeto | 73.366.147 | 0 | 0 % |
| [RN-16](REGRAS_NEGOCIO.md#rn-16) | Uma matriz por CNPJ básico | estrutural | 70.085.591 | 1 | < 0,01 % |
| [RN-17](REGRAS_NEGOCIO.md#rn-17) | Dígitos verificadores do CNPJ | legal | 73.366.147 | 0 | 0 % |
| [RN-18](REGRAS_NEGOCIO.md#rn-18) | Estabelecimento tem empresa | estrutural | 73.366.147 | 0 | 0 % |
| [RN-19](REGRAS_NEGOCIO.md#rn-19) | Município do domínio da RFB | leiaute/cadastro | 73.366.147 | 0 | 0 % |
| [RN-20](REGRAS_NEGOCIO.md#rn-20) | Ente federativo só na administração pública | leiaute/cadastro | 70.085.591 | 318 | < 0,01 % |
| [RN-21](REGRAS_NEGOCIO.md#rn-21) | Capital social não negativo | coerência do projeto | 70.085.591 | 0 | 0 % |
| [RN-22](REGRAS_NEGOCIO.md#rn-22) | Simples: uma linha por CNPJ básico | estrutural | 50.396.768 | 0 | 0 % |
| [RN-23](REGRAS_NEGOCIO.md#rn-23) | Grão dos marts | estrutural | 23.620.646 | 0 | 0 % |
| [RN-24](REGRAS_NEGOCIO.md#rn-24) | Grão das fontes e domínios | estrutural | 526.526 | 19 | < 0,01 % |
| [RN-25](REGRAS_NEGOCIO.md#rn-25) | Opção pelo Simples a partir de 1º/7/2007 | legal | 50.396.766 | 0 | 0 % |
| [RN-26](REGRAS_NEGOCIO.md#rn-26) | Opção pelo MEI a partir de 1º/7/2009 | legal | 37.082.800 | 0 | 0 % |
| [RN-27](REGRAS_NEGOCIO.md#rn-27) | Filial não começa depois do fim da matriz | coerência do projeto | 1.134.226 | 2.427 | 0,21 % |
| [RN-28](REGRAS_NEGOCIO.md#rn-28) | Opção não antecede o início de atividade (observação) | coerência do projeto | 87.479.562 | 1.751 | < 0,01 % |
| [RN-29](REGRAS_NEGOCIO.md#rn-29) | MEI não é sociedade | legal | 17.523.665 | 1.236 | < 0,01 % |

## Regras com violação

### RN-03 — CNAE secundário não repete o principal

**3.310** violações em **125.425.117** avaliados (< 0,01 %). Como ler: [catálogo, RN-03](REGRAS_NEGOCIO.md#rn-03).

| situacao | Avaliados | Violações | % |
|---|---:|---:|---:|
| BAIXADA | 38.834.586 | 1.777 | < 0,01 % |
| INAPTA | 16.239.655 | 882 | < 0,01 % |
| ATIVA | 69.857.319 | 596 | < 0,01 % |
| SUSPENSA | 399.503 | 31 | < 0,01 % |
| NULA | 94.054 | 24 | 0,03 % |

### RN-04 — CNAEs secundários não se repetem

**3.488** violações em **34.670.077** avaliados (0,01 %). Como ler: [catálogo, RN-04](REGRAS_NEGOCIO.md#rn-04).

| situacao | Avaliados | Violações | % |
|---|---:|---:|---:|
| BAIXADA | 12.685.590 | 1.683 | 0,01 % |
| INAPTA | 4.947.636 | 981 | 0,02 % |
| ATIVA | 16.890.615 | 787 | < 0,01 % |
| SUSPENSA | 107.278 | 24 | 0,02 % |
| NULA | 38.958 | 13 | 0,03 % |

### RN-05 — MEI tem um único estabelecimento não baixado

**33** violações em **17.523.665** avaliados (< 0,01 %). Como ler: [catálogo, RN-05](REGRAS_NEGOCIO.md#rn-05).

| estabelecimentos | Avaliados | Violações | % |
|---|---:|---:|---:|
| mais de um não baixado | 33 | 33 | 100,00 % |
| mais de um, no máximo um não baixado | 3.214 | 0 | 0 % |
| um | 17.520.418 | 0 | 0 % |

### RN-06 — MEI é optante do Simples Nacional

**469** violações em **17.523.665** avaliados (< 0,01 %). Como ler: [catálogo, RN-06](REGRAS_NEGOCIO.md#rn-06).

### RN-07 — MEI tem porte de microempresa

**110** violações em **17.523.665** avaliados (< 0,01 %). Como ler: [catálogo, RN-07](REGRAS_NEGOCIO.md#rn-07).

| porte | Avaliados | Violações | % |
|---|---:|---:|---:|
| PEQUENA | 93 | 93 | 100,00 % |
| DEMAIS | 17 | 17 | 100,00 % |
| MICRO | 17.523.555 | 0 | 0 % |

### RN-08 — MEI tem natureza 213-5 (observação)

**1.236** violações em **17.523.665** avaliados (< 0,01 %). Como ler: [catálogo, RN-08](REGRAS_NEGOCIO.md#rn-08).

| natureza_juridica | Avaliados | Violações | % |
|---|---:|---:|---:|
| 2062 Sociedade Empresária Limitada | 1.235 | 1.235 | 100,00 % |
| 2070 Sociedade Empresária em Nome Coletivo | 1 | 1 | 100,00 % |
| 2135 Empresário (Individual) | 17.522.429 | 0 | 0 % |

### RN-09 — Exclusão do regime não antecede a opção

**6** violações em **45.280.511** avaliados (< 0,01 %). Como ler: [catálogo, RN-09](REGRAS_NEGOCIO.md#rn-09).

| regime | Avaliados | Violações | % |
|---|---:|---:|---:|
| MEI | 19.912.560 | 3 | < 0,01 % |
| Simples Nacional | 25.367.951 | 3 | < 0,01 % |

### RN-10 — Motivo coerente com a situação

**1** violação em **73.366.147** avaliados (< 0,01 %). Como ler: [catálogo, RN-10](REGRAS_NEGOCIO.md#rn-10).

| situacao | Avaliados | Violações | % |
|---|---:|---:|---:|
| ATIVA | 28.263.121 | 1 | < 0,01 % |
| BAIXADA | 34.587.462 | 0 | 0 % |
| INAPTA | 10.084.178 | 0 | 0 % |
| NULA | 110.199 | 0 | 0 % |
| SUSPENSA | 321.187 | 0 | 0 % |

### RN-12 — Situação não antecede o início de atividade

**1.058** violações em **73.250.497** avaliados (< 0,01 %). Como ler: [catálogo, RN-12](REGRAS_NEGOCIO.md#rn-12).

| situacao | Avaliados | Violações | % |
|---|---:|---:|---:|
| BAIXADA | 34.587.462 | 517 | < 0,01 % |
| NULA | 110.199 | 196 | 0,18 % |
| INAPTA | 10.084.178 | 160 | < 0,01 % |
| ATIVA | 28.147.471 | 140 | < 0,01 % |
| SUSPENSA | 321.187 | 45 | 0,01 % |

### RN-14 — Matriz baixada, filiais baixadas ou nulas

**159** violações em **765.465** avaliados (0,02 %). Como ler: [catálogo, RN-14](REGRAS_NEGOCIO.md#rn-14).

| situacao | Avaliados | Violações | % |
|---|---:|---:|---:|
| SUSPENSA | 78 | 78 | 100,00 % |
| ATIVA | 53 | 53 | 100,00 % |
| INAPTA | 28 | 28 | 100,00 % |
| BAIXADA | 765.061 | 0 | 0 % |
| NULA | 245 | 0 | 0 % |

### RN-16 — Uma matriz por CNPJ básico

**1** violação em **70.085.591** avaliados (< 0,01 %). Como ler: [catálogo, RN-16](REGRAS_NEGOCIO.md#rn-16).

| matrizes | Avaliados | Violações | % |
|---|---:|---:|---:|
| 2 ou mais | 1 | 1 | 100,00 % |
| 1 | 70.085.590 | 0 | 0 % |

### RN-20 — Ente federativo só na administração pública

**318** violações em **70.085.591** avaliados (< 0,01 %). Como ler: [catálogo, RN-20](REGRAS_NEGOCIO.md#rn-20).

| grupo_natureza | natureza_juridica | Avaliados | Violações | % |
|---|---|---:|---:|---:|
| grupo 1 (administração pública) | 1210 Consórcio Público de Direito Público (Associação Pública) | 1.687 | 262 | 15,53 % |
| grupo 1 (administração pública) | 1031 Órgão Público do Poder Executivo Municipal | 12.004 | 28 | 0,23 % |
| grupo 1 (administração pública) | 1279 Fundação Pública de Direito Privado Municipal | 172 | 9 | 5,23 % |
| grupo 1 (administração pública) | 1066 Órgão Público do Poder Legislativo Municipal | 5.677 | 3 | 0,05 % |
| grupo 1 (administração pública) | 1082 Órgão Público do Poder Judiciário Estadual | 354 | 3 | 0,85 % |
| grupo 1 (administração pública) | 1120 Autarquia Municipal | 3.332 | 3 | 0,09 % |
| grupo 1 (administração pública) | 1155 Fundação Pública de Direito Público Municipal | 2.010 | 2 | 0,10 % |
| grupo 1 (administração pública) | 1228 Consórcio Público de Direito Privado | 41 | 2 | 4,88 % |
| grupo 1 (administração pública) | 1023 Órgão Público do Poder Executivo Estadual ou do Distrito Federal | 2.635 | 1 | 0,04 % |
| grupo 1 (administração pública) | 1112 Autarquia Estadual ou do Distrito Federal | 637 | 1 | 0,16 % |
| grupo 1 (administração pública) | 1147 Fundação Pública de Direito Público Estadual ou do Distrito Federal | 326 | 1 | 0,31 % |
| grupo 1 (administração pública) | 1180 Órgão Público Autônomo Municipal | 347 | 1 | 0,29 % |
| grupo 1 (administração pública) | 1333 Fundo Público da Administração Direta Municipal | 35.761 | 1 | < 0,01 % |
| grupo 1 (administração pública) | 1350 ENTIDADE PÚBLICA SOB REGIME ESPECIAL | 1 | 1 | 100,00 % |
| demais grupos | 0000 Natureza Jurídica não informada | 5 | 0 | 0 % |
| demais grupos | 2011 Empresa Pública | 1.480 | 0 | 0 % |
| demais grupos | 2038 Sociedade de Economia Mista | 780 | 0 | 0 % |
| demais grupos | 2046 Sociedade Anônima Aberta | 3.171 | 0 | 0 % |
| demais grupos | 2054 Sociedade Anônima Fechada | 102.898 | 0 | 0 % |
| demais grupos | 2062 Sociedade Empresária Limitada | 16.753.935 | 0 | 0 % |

_Mostrando 20 de 90 linhas._

### RN-24 — Grão das fontes e domínios

**19** violações em **526.526** avaliados (< 0,01 %). Como ler: [catálogo, RN-24](REGRAS_NEGOCIO.md#rn-24).

| tabela | Avaliados | Violações | % |
|---|---:|---:|---:|
| basedosdados.vizinhanca_municipio | 522.822 | 19 | < 0,01 % |
| basedosdados.cnae_2 | 1.356 | 0 | 0 % |
| basedosdados.regiao_metropolitana_2017 | 1.385 | 0 | 0 % |
| excecoes_conhecidas_municipio | 2 | 0 | 0 % |
| observabilidade.dq_historico_testes | 638 | 0 | 0 % |
| rfb.paises | 255 | 0 | 0 % |
| rfb.qualificacoes | 68 | 0 | 0 % |

### RN-27 — Filial não começa depois do fim da matriz

**2.427** violações em **1.134.226** avaliados (0,21 %). Como ler: [catálogo, RN-27](REGRAS_NEGOCIO.md#rn-27).

| situacao_matriz | Avaliados | Violações | % |
|---|---:|---:|---:|
| BAIXADA | 765.465 | 1.785 | 0,23 % |
| NULA | 426 | 363 | 85,21 % |
| INAPTA | 368.335 | 279 | 0,08 % |

### RN-28 — Opção não antecede o início de atividade (observação)

**1.751** violações em **87.479.562** avaliados (< 0,01 %). Como ler: [catálogo, RN-28](REGRAS_NEGOCIO.md#rn-28).

| regime | Avaliados | Violações | % |
|---|---:|---:|---:|
| Simples Nacional | 50.396.764 | 1.648 | < 0,01 % |
| MEI | 37.082.798 | 103 | < 0,01 % |

### RN-29 — MEI não é sociedade

**1.236** violações em **17.523.665** avaliados (< 0,01 %). Como ler: [catálogo, RN-29](REGRAS_NEGOCIO.md#rn-29).

| natureza_juridica | Avaliados | Violações | % |
|---|---:|---:|---:|
| 2062 Sociedade Empresária Limitada | 1.235 | 1.235 | 100,00 % |
| 2070 Sociedade Empresária em Nome Coletivo | 1 | 1 | 100,00 % |
| 2135 Empresário (Individual) | 17.522.429 | 0 | 0 % |

## Faixas informativas

Regras sem violação com a quebra `faixa`: casos que a regra aceita e que vale acompanhar.

### RN-13 — Datas de evento não passam do extrato

**0** violações em **234.136.725** avaliados (0 %). Como ler: [catálogo, RN-13](REGRAS_NEGOCIO.md#rn-13).

| campo | faixa | Avaliados | Violações | % |
|---|---|---:|---:|---:|
| início de atividade | até a data do extrato | 73.365.920 | 0 | 0 % |
| início de atividade | dia seguinte ao extrato | 227 | 0 | 0 % |
| opção pelo MEI | até a data do extrato | 37.082.587 | 0 | 0 % |
| opção pelo MEI | dia seguinte ao extrato | 213 | 0 | 0 % |
| opção pelo Simples | até a data do extrato | 50.396.544 | 0 | 0 % |
| opção pelo Simples | dia seguinte ao extrato | 212 | 0 | 0 % |
| opção pelo Simples | opção até 1º de janeiro seguinte | 10 | 0 | 0 % |
| situação cadastral | até a data do extrato | 73.250.111 | 0 | 0 % |
| situação cadastral | dia seguinte ao extrato | 386 | 0 | 0 % |
| situação especial | até a data do extrato | 40.515 | 0 | 0 % |

## Interpretação de 2026-09

<!-- Interpretação manual de 2026-09: o texto abaixo desta linha é preservado por `rfb regras` no mesmo mês. -->

Leitura do extrato de 2026-09 (73.366.147 estabelecimentos, 70.085.591 CNPJs básicos, 17.523.665 empresas com opção
pelo MEI). Os números vêm da execução de `rfb regras` sobre uma cópia do warehouse real, em 2026-10-13 (lote FRN,
reexecutado no lote FRN2 com a RN-05 e a RN-24 revistas, sem mudança nas tabelas acima); os de RN-06 e RN-09 e as
contagens de situação nula e de meses das fontes RFB, que não estão nas tabelas acima, vêm de consultas somente
leitura na mesma cópia. As causas são
as leituras prováveis do [catálogo](REGRAS_NEGOCIO.md) e não foram verificadas registro a registro. Nenhuma
violação passa de 0,5 % do universo da regra.

**Regras que valem no dado real.** Treze regras não têm violação: CNAE principal e secundários no domínio (RN-01,
RN-02), não ativo com data da situação (RN-11), datas dentro do limite do extrato (RN-13), situação especial com
data (RN-15), dígitos verificadores (RN-17), estabelecimento com empresa (RN-18), município no domínio da RFB
(RN-19), capital social não negativo (RN-21), os grãos do Simples e dos marts (RN-22, RN-23) e as datas de início
dos regimes: nenhuma opção pelo Simples antes de 1º/7/2007 (RN-25) nem pelo MEI antes de 1º/7/2009 (RN-26).

**MEI (RN-05 a RN-08, RN-29).**

- **RN-05, um único estabelecimento não baixado:** 33 empresas MEI têm mais de um estabelecimento não baixado, as
  violações da LC 123, art. 18-A, § 4º, II. Outras 3.214 têm estabelecimentos além do único não baixado, todos
  baixados: o baixado continua no extrato e não contraria a lei, por isso aparece na quebra sem violação. É o
  mesmo fenômeno das 3.749 filiais de MEI vistas pela RSEM, contado aqui por empresa. Nenhuma empresa MEI está em
  "indeterminado (situação desconhecida)": nenhum dos 73.366.147 estabelecimentos tem situação nula, então a
  separação não mudou nenhuma contagem neste mês.
- **RN-06, MEI optante do Simples:** 469 empresas têm a opção pelo MEI sem a opção pelo Simples. Em 467 delas, a
  exclusão do Simples já está vigente (data até 12/09/2026); nas outras 2, não há data de exclusão. A leitura mais
  provável é o desenquadramento do MEI ainda não registrado depois da exclusão do Simples, não erro de digitação.
- **RN-07, MEI microempresa:** 110 empresas MEI declaram porte de empresa de pequeno porte (93) ou "demais" (17). O
  porte é declarado no registro e não acompanha a opção pelo MEI: leitura provável, porte desatualizado.
- **RN-29, MEI não é sociedade, e RN-08 (observação):** as mesmas 1.236 empresas MEI têm natureza de sociedade
  (1.235 Sociedade Empresária Limitada, 1 em Nome Coletivo). Pela RN-29, contrariam o art. 18-A, § 1º, que só admite
  o empresário individual ou o empreendedor; nenhuma empresa MEI tem outra natureza além dessas e da 213-5. Leitura
  provável: empresa que virou sociedade sem o desenquadramento do MEI registrado.

**Datas e situação (RN-09, RN-10, RN-12, RN-13).**

- **RN-09:** 6 registros (3 no Simples, 3 no MEI) com exclusão anterior à opção, em 45,3 milhões com as duas datas.
  Nos 6, o indicador do regime está em N: são registros hoje excluídos do regime, não optantes atuais. A causa da
  inversão fica em aberto.
- **RN-10:** 1 estabelecimento ATIVO com motivo diferente de 00, em 28,3 milhões de ativos; nenhum inativo com
  motivo 00. A tradução de "ativa não tem encerramento" vale com uma exceção isolada.
- **RN-12:** 1.058 estabelecimentos com data da situação anterior ao início de atividade. A taxa é maior nos NULOS
  (196 de 110.199, 0,18 %), coerente com a nulidade, que retroage ao ato declarado nulo; nas demais situações fica
  abaixo de 0,02 % e a leitura provável é erro de data.
- **RN-13, sem violação:** nenhuma data passa do limite. Acima da data de referência (12/09/2026) há só o dia
  seguinte, 13/09/2026, em 1.038 datas (386 de situação, 227 de início de atividade, 213 de opção pelo MEI e 212
  de opção pelo Simples), e 10 opções pelo Simples com efeito em 1º/1/2027, a janela de opção para 2027 aberta em
  setembro (CGSN 190 e 194/2026). O D+1 é o corte do extrato, não erro de data.

**Matriz e filiais (RN-14, RN-16, RN-27).**

- **RN-14, matriz baixada ⇒ filiais baixadas ou nulas:** 159 filiais de matriz baixada não estão baixadas nem nulas
  (78 suspensas, 53 ativas, 28 inaptas), 0,02 % das 765.465. Contrariam o art. 24, § 2º, da IN 2.119: defasagem ou
  erro de dado. As 245 filiais NULAS aparecem na quebra sem violação.
- **RN-16, uma matriz por CNPJ básico:** 1 CNPJ básico com duas matrizes, o mesmo caso da RSEM.
- **RN-27, filial que começa depois do fim da matriz:** 2.427 filiais (0,21 % de 1.134.226) têm início de atividade
  posterior ao evento da matriz: 1.785 de matriz baixada, 279 de inapta e 363 de nula. Nas matrizes baixadas e
  inaptas, a taxa é baixa (0,23 % e 0,08 %); nas nulas, é de 85,21 % (363 de 426). A taxa das nulas é coerente com a
  nulidade de um ato posterior à abertura das filiais, que leva a data da situação para trás do início delas; não
  foi verificado. Como o extrato não traz a data de inscrição, a regra é coerência do projeto, não regra legal.

**Opção e início de atividade (RN-28, observação).** 1.648 opções pelo Simples e 103 pelo MEI antecedem o início de
atividade da matriz, menos de 0,01 % dos registros. Não é violação de regra: a leitura fica em aberto (início de
atividade corrigido depois da opção ou opção feita na abertura com início declarado depois).

**Leiaute e grãos (RN-20, RN-24).**

- **RN-20, ente federativo:** 318 das 74.240 empresas da administração pública (grupo 1, 0,43 %) não têm o ente
  federativo, que o leiaute manda preencher; nenhuma empresa fora do grupo 1 o tem. 262 delas (82 %) são consórcios
  públicos de direito público (natureza 1210), 15,53 % dos 1.687 consórcios dessa natureza. O consórcio público é
  interfederativo e não tem um único ente responsável óbvio. Seguem 28 órgãos do Executivo municipal (1031, 0,23 %)
  e 9 fundações públicas de direito privado municipais (1279, 5,23 %).
- **RN-24, grãos das fontes:** as 19 linhas excedentes estão todas na vizinhança da Base dos Dados, que o grão
  declarado já admite repetir (RDIC-02); a ponte `bridge_municipio_vizinho` deduplica. Países e qualificações agora
  são lidos só no mês do relatório; como o raw real só tem 2026-09, as 255 e as 68 linhas são as mesmas de antes.

**CNAE (RN-03, RN-04).** 3.310 ocorrências de CNAE secundário repetem o principal e 3.488 estabelecimentos
repetem um secundário. Mais da metade está em estabelecimentos baixados ou inaptos, e a taxa nos ativos é a menor
(596 em 69,9 milhões de ocorrências; 787 em 16,9 milhões de estabelecimentos): leitura provável, registro antigo.
Não afetam as métricas, que usam só o CNAE principal, nem a ponte de secundários, que deduplica os pares.
