# Cenários de uso das fontes do IBGE

> **Para quem:** consultor(a), empreendedor(a) ou analista que quer usar renda, REGIC, CEMPRE e valor adicionado ·
> **Quando ler:** para achar a consulta pronta de uma pergunta de mercado e saber como ler o resultado.

> **Adição**, incremento `enriquecimento_ibge` ([ADR-0022](../adr/0022-enriquecimento-fontes-gratuitas-ibge.md)). Cinco
> perguntas de negócio para quem vai abrir um negócio ou estuda um setor, cada uma respondida por uma das bases
> novas do IBGE e por uma consulta pronta em `transform/analyses/`. O exemplo é o estudo de caso do projeto: uma loja
> de tintas (CNAE 4741500) em Fundão/ES. O que cada base é e como ela foi construída está na
> [conceitos](../conceitos.md#1-as-bases).

## Como rodar

As consultas usam as vars do caso (`caso_cnae_alvo`, `caso_municipio`, `caso_uf` em `transform/dbt_project.yml`) e
leem o gold de `RAIZ_DADOS` depois de um `dbt build`. Três delas entram no relatório do caso (`make relatorio`, seção
"Enriquecimento com o IBGE"). Para rodar uma sozinha:

```bash
cd transform
uv run dbt show --select cenario_polo_compras_evasao --limit 20
uv run dbt show --select cenario_polo_compras_evasao --vars '{caso_uf: SP, caso_cnae_alvo: "4744099"}' --limit 20
uv run dbt compile --select cenario_polo_compras_evasao   # o SQL em target/compiled/rfb/analyses/
```

Para um agente que responde perguntas livres, as mesmas bases aparecem como golden queries testadas no
[guia de consulta em linguagem natural](consulta-agente.md) ([ADR-0023](../adr/0023-golden-queries-e-guia-para-agente.md)).

Todas trazem só agregados por município, CNAE ou UF, nunca CNPJ nem nome
([ADR-0008](../adr/0008-minimizacao-dados-pessoais.md)). As linhas de exemplo abaixo vêm do dado real (extrato da RFB de
2026-09, CEMPRE 2024, Censo 2022, REGIC 2018), consultado em 2026-10-14.

| # | Pergunta | Base | Analysis | Métrica ou consulta salva |
|---|---|---|---|---|
| 1 | Onde há renda e pouca concorrência? | Censo 2022 (renda) | `cenario_renda_concorrencia.sql` | — |
| 2 | Onde os moradores compram, e quanto há de concorrência lá? | REGIC 2018 | `cenario_polo_compras_evasao.sql` | `polo_compras_concorrencia_caso` |
| 3 | Qual é o tamanho real do setor? | CEMPRE | `cenario_tamanho_setor_cempre.sql` | `unidades_locais_cempre`, `pessoal_ocupado_cempre`, `ativos_rfb` |
| 4 | Qual é o perfil econômico do município? | PIB dos Municípios (VA) | `cenario_perfil_economico_va.sql` | — |
| 5 | Em que nível da rede urbana o setor se concentra? | REGIC 2018 (hierarquia) | `cenario_hierarquia_urbana.sql` | — |
| — | O caso: Fundão, o seu polo e a UF | todas | `estudo_caso_enriquecimento_ibge.sql` | — |

## O caso: Fundão, o seu polo de compras e a UF

`estudo_caso_enriquecimento_ibge.sql` põe lado a lado o município do caso, o polo de compras dele e a UF.

| escopo | município | hierarquia | renda média | renda mediana | polo | % no polo | ativos 4741500 | unidades CEMPRE 47.41-5 | pessoal CEMPRE |
|---|---|---|---:|---:|---|---:|---:|---:|---:|
| município do caso | Fundão | Metrópole | 1.406,78 | 1.040,00 | Serra | 45,0 | 0 | 0 | 0 |
| polo de compras | Serra | Metrópole | 1.541,03 | 1.100,00 | — | — | 45 | 33 | 196 |
| UF | ES | — | 1.650,72 | — | — | — | 391 | 281 | 1.207 (com sigilo) |

**Como ler.** Fundão não tem loja de tintas ativa nem unidade local da classe no CEMPRE. Quem sai de Fundão para
comprar bens duráveis vai principalmente a Serra, onde há 45 lojas ativas. A renda da UF é a média dos municípios
ponderada pelos moradores; o pessoal ocupado da UF soma só as células sem sigilo e por isso subestima.

## 1. Renda × concorrência: mercado subatendido

**Pergunta.** Em que municípios da UF a renda per capita está acima da mediana dos municípios e há poucos
concorrentes por habitante no CNAE?

**Base e por quê.** A renda do Censo 2022 (`renda_per_capita_media_2022` em `dim_municipio`) diz se há poder de
compra; os ativos por 10 mil habitantes (`mart_concorrencia_municipio`) dizem quanta oferta já existe. Renda alta com
densidade baixa é candidato a mercado subatendido.

**Analysis.** `cenario_renda_concorrencia.sql`: só os municípios com renda acima da mediana da UF, do menos ao mais
concorrido; `abaixo_da_mediana_densidade` marca os que têm densidade até a mediana da UF.

**Exemplo (ES, lojas de tintas).**

| município | renda média | mediana da UF | população | ativos | ativos por 10 mil hab. | abaixo da mediana |
|---|---:|---:|---:|---:|---:|---|
| Fundão | 1.406,78 | 1.256,01 | 18.898 | 0 | 0,00 | sim |
| Domingos Martins | 1.477,15 | 1.256,01 | 38.236 | 1 | 0,26 | sim |

**Como ler.** Fundão está entre os 39 municípios do ES com renda acima da mediana e é um dos oito sem nenhuma loja
ativa. É um sinal para investigar, não uma conclusão: o morador pode comprar no polo (cenário 2), e a população
pequena pode não sustentar a loja.

## 2. Polo de compras e evasão de demanda

**Pergunta.** Onde os moradores de cada município compram bens duráveis, e quanta concorrência há no município e no
polo?

**Base e por quê.** A REGIC 2018 traz, para cada município, os destinos procurados para comprar móveis e
eletroeletrônicos (Q2), a melhor proxy de bem durável e material de construção, com o percentual de cada um. O
destino com o maior percentual é o polo de compras (`dim_municipio.id_municipio_polo_compras`); a ponte
`bridge_municipio_destino_compras` tem todos os destinos.

**Analysis.** `cenario_polo_compras_evasao.sql`, com `mart_concorrencia_area_mercado.ativos_no_polo`. Consulta
salva `polo_compras_concorrencia_caso` (`uv run mf query --saved-query polo_compras_concorrencia_caso`).

**Exemplo (ES, lojas de tintas).**

| município | hierarquia | polo | % no polo | destinos citados | % "Outros" | ativos no município | ativos no polo |
|---|---|---|---:|---:|---:|---:|---:|
| Colatina | Centro Sub-Regional A | Vitória | 98,3 | 2 | 0,0 | 18 | 28 |
| Linhares | Centro Sub-Regional A | Vitória | 88,3 | 2 | 0,0 | 23 | 28 |

**Como ler.** O percentual divide os deslocamentos **entre os destinos de fora**: 98 % de quem sai de Colatina para
comprar móveis vai a Vitória. A REGIC não mede quanto da compra fica no próprio município, então "evasão" aqui é o
destino de quem sai, não a fração que sai. Um polo com muito mais lojas que a origem indica que parte da demanda já
é atendida fora. Os 67 municípios de maior centralidade (Vitória, Vila Velha e Serra, no ES) não têm polo. Todo
município da UF com polo aparece, inclusive sem nenhum estabelecimento do CNAE nele, nos vizinhos ou na região
metropolitana (0 ativos no município): no dado real, as lojas de tintas somam 5.503 municípios com polo no Brasil,
226 deles fora da área de mercado do CNAE (66 no PI, 36 em MG, 21 na PB); no ES, todos os 75 já estavam nela.

## 3. Tamanho real do setor (CEMPRE)

**Pergunta.** Quantas unidades e quantas pessoas trabalham no setor, por município, e qual o salário médio, ao lado
do número de CNPJs ativos?

**Base e por quê.** O CEMPRE conta as unidades locais com sinal de atividade e o pessoal ocupado em 31/12, sem MEI;
a RFB conta todo CNPJ ativo. A diferença entre "CNPJ ativo" e "estabelecimento com gente trabalhando" aparece lado a
lado em `mart_emprego_setor_municipio`.

**Analysis.** `cenario_tamanho_setor_cempre.sql`, para a classe do CNAE do caso (47.41-5) na UF. Métricas
`unidades_locais_cempre`, `pessoal_ocupado_cempre` e `ativos_rfb`.

**Exemplo (ES, classe 47.41-5).**

| município | unidades | pessoal ocupado | assalariados | salário médio mensal aprox. | pessoas por unidade | sigilo | ativos RFB | sem MEI |
|---|---:|---:|---:|---:|---:|---|---:|---:|
| Serra | 33 | 196 | 167 | 2.928,60 | 5,94 | não | 45 | 34 |
| Iconha | 5 | — | — | — | — | sim | 4 | 4 |

**Como ler.** Em Serra, 33 unidades com atividade empregam 196 pessoas, cerca de 6 por loja; a RFB tem 45 CNPJs
ativos, 11 deles MEI. Em Iconha, o IBGE esconde o pessoal (`X`): o projeto não inventa um número, só sinaliza
`tem_sigilo`. O salário médio é aproximado (salários ÷ assalariados em 31/12 ÷ 13); o IBGE usa o pessoal
assalariado médio do ano, que a tabela municipal não traz.

## 4. Perfil econômico (valor adicionado por atividade)

**Pergunta.** O município vive de serviços, de indústria ou do agro, e como isso se cruza com a densidade do setor?

**Base e por quê.** O PIB dos Municípios abre o valor adicionado em agropecuária, indústria, serviços e administração
pública (`pct_va_*` em `dim_municipio`). Um varejo de bens de construção depende de renda e de obras; o perfil diz
de onde vem a renda local.

**Analysis.** `cenario_perfil_economico_va.sql`: municípios da UF pela participação de serviços, com a atividade
predominante e os ativos por 10 mil habitantes do CNAE.

**Exemplo (ES).**

| município | ano do VA | agro % | indústria % | serviços % | adm. pública % | predominante | ativos por 10 mil hab. |
|---|---:|---:|---:|---:|---:|---|---:|
| Vitória | 2021 | 0,10 | 37,78 | 54,19 | 7,92 | serviços | 0,82 |
| Fundão | 2021 | 8,88 | 25,68 | 37,93 | 27,51 | serviços | 0,00 |

**Como ler.** O ano do VA é explícito porque as aberturas por atividade saem depois do PIB total (hoje, VA até 2021 e
PIB até 2023). Em Fundão, a administração pública pesa 27,5 % do VA, sinal de economia menos diversificada. O VA é
de 2021 e os ativos de 2026: compare perfis, não anos.

## 5. Hierarquia urbana: onde o setor se concentra na rede urbana

**Pergunta.** A concorrência do setor se concentra nas metrópoles, nas capitais regionais ou nos centros locais?

**Base e por quê.** A hierarquia da REGIC 2018 (`regic_hierarquia` em `dim_municipio`) agrupa os municípios pelo
papel na rede urbana. A densidade do setor por nível mostra se ele é de cidade grande ou de cidade pequena.

**Analysis.** `cenario_hierarquia_urbana.sql`, no Brasil inteiro, para o CNAE do caso.

**Exemplo (Brasil, lojas de tintas).**

| nível | hierarquia | municípios | com ativo | ativos | ativos por 10 mil hab. |
|---|---|---:|---:|---:|---:|
| 2B | Capital Regional B | 92 | 78 | 2.185 | 1,56 |
| 5 | Centro Local | 4.115 | 1.256 | 2.564 | 0,51 |

**Como ler.** As capitais regionais e os centros sub-regionais têm a maior densidade; nos centros locais, só 30,5 %
dos municípios têm ao menos uma loja. Fundão é classificado como Metrópole porque integra o arranjo populacional de
Vitória: a hierarquia é do arranjo, não do município isolado.

## Limitações comuns

- **Anos diferentes.** Ativos da RFB do mês do extrato; CEMPRE de 31/12 do `ano_cempre` (hoje 2024); renda do Censo
  2022; REGIC de 2018; VA até 2021 (`ano_va`), PIB total até 2023 (`ano_pib`). Compare ordens de grandeza, não anos.
- **Sigilo do CEMPRE.** Pessoal e salários com `X` ficam NULL e `tem_sigilo` true. Nunca são imputados; somas sobre
  municípios ou classes subestimam.
- **CEMPRE sem MEI.** Compare `unidades_locais_cempre` com `ativos_rfb_sem_mei`, não com `ativos_rfb`
  ([RN-30](../referencia/regras-negocio.md#rn-30)).
- **REGIC de 2018, malha de 2018.** Municípios criados depois não têm hierarquia nem polo; o percentual é a divisão
  entre os destinos de fora, não a fração da demanda que sai; os 67 municípios mais centrais não têm polo.
- **Renda nominal de 2022.** Em reais de julho de 2022, sem correção; use a mediana para o domicílio típico.
- **VA negativo.** O IBGE publica VA negativo em alguns municípios (indústria de Cachoeira Dourada/GO em 2021), e aí
  as participações saem de 0–100.
- **Modo offline sem `ibge/`.** Com um espelho `--origem-local` antigo, as colunas do IBGE saem vazias e os cenários
  devolvem só a parte da RFB ([operacao.md](../operacao.md#fontes-do-ibge-incremento-enriquecimento_ibge)).
