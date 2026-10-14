# ADR-0022 — Enriquecimento com fontes gratuitas direto da origem (pacote 1)

**Status:** aceita (2026-10-14). Encerra a Fase 2 do [ADR-0015](0015-enriquecimento-base-dos-dados.md).

**Contexto.** Pedido do usuário (2026-10-13): avaliar fontes gratuitas que agreguem ao projeto, no seu espírito,
que é o perfil de mercado para quem pensa em abrir um negócio ou estuda um setor (estudo de caso: loja de tintas,
CNAE 4741500, em Fundão/ES). A Fase 2 do ADR-0015 (pirâmide etária, RAIS, CAGED, exportadoras, CEP) estava adiada
porque a Base dos Dados só a entrega pelo BigQuery, que exige conta no Google Cloud. A avaliação (artefato Traycer
"Avaliação: enriquecimento com fontes gratuitas") mostrou que essas tabelas não são pagas na origem: o que exigia
BigQuery era o **caminho**. O usuário aprovou o pacote 1 em 2026-10-14.

**Princípio do usuário (regra do projeto).** Nenhuma base paga e nenhum serviço que transfira custo a quem usa o
projeto, nem atalho que contorne a cobrança da fonte original. Busca-se a **fonte primária gratuita**, usada como
ela mesma distribui: sem conta em nuvem, sem chave, sem cadastro. Uma fonte nova só entra se cumprir isso.

**Decisão.** Pacote 1, "demanda e tamanho do setor", marcado como incremento `enriquecimento_ibge` (mesmo
mecanismo do ADR-0015: `meta.incremento` e tag `incremento_enriquecimento_ibge` em todo nó dbt, comentário
`-- incremento: enriquecimento_ibge` no SQL e selo "Incremento: enriquecimento IBGE" em `docs/ESCOPO.md`).

| Fonte | De onde | O que responde | Por que esta |
|---|---|---|---|
| CEMPRE (Cadastro Central de Empresas) | API SIDRA, tabela 9528, município × classe CNAE 2.0 | tamanho real do setor: unidades locais, pessoal ocupado, assalariados, salários; checagem cruzada com os ativos da RFB | é o agregado oficial por município × classe; dispensa os microdados da RAIS |
| Rendimento domiciliar per capita | API SIDRA, tabela 10295 (Censo 2022) | poder de compra do município, médio e mediano | dado censitário, todos os municípios |
| REGIC 2018 | planilhas do geoftp do IBGE | hierarquia urbana e para onde os moradores vão comprar (polo de compras) | é a única fonte oficial de deslocamentos para comércio; completa a vizinhança geográfica do ADR-0015 |
| Valor adicionado por atividade | já no raw (`stg_bd__pib`, PIB dos Municípios do IBGE pela Base dos Dados) | perfil econômico: agro, indústria, serviços, administração pública | custo quase zero: só não chegava à dimensão |

No modelo, tudo é **aditivo** (versão minor, v1.4.0): colunas novas em `dim_municipio` (renda, VA com `ano_va`
próprio, hierarquia, índice de atração, polo de compras e total do CEMPRE); a ponte
`bridge_municipio_destino_compras`; o mart `mart_emprego_setor_municipio` (CEMPRE × RFB por município × classe);
o polo de compras em `mart_concorrencia_area_mercado`, sem mudar grão nem colunas; a regra RN-30; dimensões,
métricas e uma consulta salva na camada semântica; conceitos na ontologia; a seção do IBGE no relatório do caso e
os [cenários de uso](../CENARIOS_DE_USO.md). Nenhuma coluna, grão ou comando existente muda.

- **Polo de compras = maior percentual em móveis e eletroeletrônicos (Q2 da REGIC),** a melhor proxy de bem
  durável e material de construção para o caso. O destino "Outros" nunca é polo; empate fica com o menor código.
- **Sigilo nunca é imputado.** Célula `X` do IBGE fica NULL, com `tem_sigilo`.
- **Modo offline compatível.** Um espelho `--origem-local` sem `ibge/` (da v1.3) continua funcionando: a ingestão
  avisa e publica as tabelas IBGE vazias, com o esquema; o dbt constrói tudo com as colunas do IBGE NULL. Era a
  condição do usuário para a versão ser minor.

**Alternativas descartadas.**

| Fonte | Motivo |
|---|---|
| Comex Stat (MDIC), exportação e importação por município × SH4 | CSV grande, correspondência SH4 ↔ CNAE imprecisa, pouco ligado às perguntas do projeto |
| Lista de exportadoras e importadoras por CNPJ (MDIC) | **não é mais publicada** (sigilo); só ficaram as estatísticas por município |
| ESTBAN (Banco Central), crédito e depósitos por município | proxy de atividade financeira, pouco ligado às perguntas |
| RAIS microdados (MTE, FTP do PDET) | vários GB por ano e sem identificação; dado o CEMPRE, que entrega o agregado por município × classe, o ganho é baixo |
| IDHM (Atlas Brasil: PNUD, Ipea, FJP) | base no Censo 2010, desatualizado; a renda do Censo 2022 o substitui |
| Ipeadata | em geral reempacota o IBGE e outras fontes; a regra é ir à fonte primária |

**Futuro: pacote 2, "dinâmica do emprego".** O Novo CAGED (MTE, FTP do PDET) tem cadência mensal e subclasse CNAE,
como a RFB, e daria admissões e desligamentos ao lado das aberturas e encerramentos. Exige FTP, 7z e backfill. Fica
para depois de avaliar o pacote 1, por decisão do usuário.

**Fase 2 do ADR-0015 encerrada.** O caminho pelo BigQuery está formalmente abandonado: contraria o princípio acima.
Do que ela listava, CEMPRE e renda entram aqui; CAGED é o pacote 2; RAIS microdados e exportadoras foram descartados
acima; pirâmide etária e diretório de CEP ficam sem plano.

**Limitações.**

- **Valor adicionado só até 2021.** O IBGE publica o PIB total antes das aberturas por atividade: hoje o PIB vai até
  2023 e o VA até 2021. Por isso `ano_va` é independente de `ano_pib`. O IBGE publica VA negativo em alguns
  municípios, e aí as participações saem de 0–100.
- **CEMPRE com defasagem e sigilo.** O ano mais recente é 2024 (31/12), quase dois anos antes do extrato da RFB.
  Exclui os MEI; desde 2022, inclui organizações com CNPJ ativo sem indício de inatividade, e a série anterior não é
  comparável. Pessoal e salários de células pequenas vêm com `X` (na classe 47.41-5, em 1.099 municípios); somas
  subestimam.
- **REGIC de 2018, com a malha de 2018.** Município criado depois não tem hierarquia nem polo; os 67 municípios de
  maior centralidade não tiveram questionário. O percentual divide os deslocamentos entre os destinos de fora; não
  mede quanto da compra fica no município.
- **Renda nominal de 2022**, sem correção.

**Licenças e termos de uso** (conferidos em 2026-10-14).

- O IBGE é fundação pública do Poder Executivo federal. O Decreto nº 8.777/2016, que institui a Política de Dados
  Abertos do Poder Executivo federal, diz no art. 4º: "Os dados disponibilizados pelo Poder Executivo federal, bem
  como qualquer informação de transparência ativa, são de livre utilização pelo Governo federal e pela
  sociedade", e define dados abertos (art. 2º, III) como os que permitem "livre utilização, consumo ou cruzamento,
  limitando-se a creditar a autoria ou a fonte". [Planalto](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2016/decreto/d8777.htm).
- As publicações do IBGE trazem "© IBGE" (por exemplo, a REGIC 2018) e não citam uma licença aberta nomeada; não
  achamos, no portal do IBGE, um termo específico de uso dos dados (o "Termo de Uso e Política de Privacidade" do
  portal trata de dados pessoais). O projeto credita a fonte em cada tabela (`docs/DICIONARIO_DADOS.md`, fontes dbt
  com a tabela SIDRA ou a planilha de origem), na camada semântica (A7) e no relatório do caso.
- O valor adicionado vem da Base dos Dados, nos termos do ADR-0015.

**Consequências.** `rfb ingerir` acessa dois hosts novos (`apisidra.ibge.gov.br`, `geoftp.ibge.gov.br`); o CEMPRE
nacional leva de 1 a 2 horas na primeira vez e depois só é baixado quando sai um ano novo, que a ingestão consulta
no máximo uma vez a cada 30 dias ([OPERACAO.md](../OPERACAO.md#fontes-do-ibge-incremento-enriquecimento_ibge)).
O mensal passa a depender da SIDRA e do geoftp, mas não a exigir (RIBG-02): falha do IBGE é aviso, com o raw
anterior (ou vazio) mantido e a falha no manifesto IBGE; `--sem-ibge` desliga o IBGE na execução; e todo
`RAIZ_DADOS` sem `raw/ibge/` (o da v1.3) ganha o raw vazio antes do dbt e de `rfb regras` (RIBG-01). Para não
embutir o primeiro download no agendamento mensal, `rfb atualizar --renovar-ibge` sem mês novo baixa só o IBGE e
reconstrói o gold corrente. Dependência nova: `openpyxl`. O
caso de Fundão ganha uma explicação para os 0 ativos locais: quem sai de Fundão para comprar bens duráveis vai
principalmente a Serra (45 %), onde há 45 lojas de tintas ativas.
