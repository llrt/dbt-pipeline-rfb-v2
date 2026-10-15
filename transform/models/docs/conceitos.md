{#
  Definições canônicas curtas dos conceitos de negócio (v1.5.0). Fonte única do texto curto:
  - os YAMLs dos modelos usam `{{ doc('<conceito>') }}` na descrição (dbt docs e dicionário de dados);
  - `scripts/gerar_conceitos.py` copia cada bloco para a seção "Definições" de docs/conceitos.md;
  - `scripts/gerar_catalogo_golden.py` embute os blocos no catálogo das golden queries (`conceitos[].definicoes`),
    ligados aos conceitos de docs/referencia/golden_queries/matriz.yml.
  Depois de editar: `make conceitos` e `make golden`. Cada bloco: 1 a 3 parágrafos, sem lista nem tabela (o
  dicionário junta a descrição numa linha só). A primeira linha do bloco é o título, num comentário Jinja.
  A narrativa longa, com as fontes legais, fica em docs/conceitos.md.
#}

{% docs empresa %}{# Empresa #}
**Empresa** é a entidade inscrita no CNPJ (sociedade, empresário individual, órgão público, associação…),
identificada pelo **CNPJ básico** (os 8 primeiros caracteres) e com uma linha no arquivo Empresas da RFB. Natureza
jurídica, porte, capital social e opção pelo Simples/MEI são atributos da empresa.

O projeto não tem uma tabela de empresas no gold: os atributos da empresa são copiados para cada estabelecimento
dela. Para contar empresas, conte as **matrizes** (uma por CNPJ básico).
{% enddocs %}

{% docs estabelecimento %}{# Estabelecimento #}
**Estabelecimento** é o local onde a empresa exerce suas atividades (IN RFB 2.119/2022, art. 5º): a matriz ou uma
filial, cada um com um **CNPJ completo** de 14 posições e uma linha no arquivo Estabelecimentos. Uma empresa tem um
ou mais estabelecimentos. Situação cadastral, CNAE, endereço, município e data de início de atividade são
atributos do estabelecimento.

O estabelecimento é o grão das fatos do projeto: as contagens padrão (estabelecimentos, ativos, MEI ativos) contam
estabelecimentos, não empresas.
{% enddocs %}

{% docs matriz_filial %}{# Matriz e filial #}
**Matriz e filial**: o identificador matriz/filial do leiaute vale 1 (matriz) ou 2 (filial). O projeto lê a
inscrição da entidade como a da matriz, com as filiais em inscrição própria; a baixa da matriz implica a baixa de
todas as filiais (IN RFB 2.119/2022, art. 24, § 2º).

O que diz se é matriz é esse identificador, não a ordem "0001" do CNPJ (o CNPJ alfanumérico existe desde julho de
2026). Contar matrizes é contar empresas: no dado real, todo CNPJ básico tem matriz, e quase sempre uma só.
{% enddocs %}

{% docs situacao_cadastral %}{# Situação cadastral #}
**Situação cadastral** é o estado da inscrição de cada estabelecimento no CNPJ (IN RFB 2.119/2022, art. 9º): 2
ATIVA, 3 SUSPENSA, 4 INAPTA, 8 BAIXADA ou 1 NULA, com a data e o motivo do último evento. Os dados abertos trazem só
a situação atual, não o histórico de eventos.

A situação "da empresa" é lida como a da matriz: uma empresa ATIVA pode ter filiais baixadas.
{% enddocs %}

{% docs ativa_em_operacao %}{# Ativa × em operação #}
**Ativa não quer dizer em operação.** As situações cadastrais "não se confundem com a condição de atividade ou
inatividade para fins tributários" (IN RFB 2.119/2022, art. 9º, parágrafo único). Um estabelecimento parado segue
ATIVO até ser suspenso, declarado inapto ou baixado.

"Ativo" no projeto é a situação ATIVA no extrato do mês. Nos marts e nos modelos originais, "inativo" é toda
situação diferente de ATIVA (inclui suspensa e inapta).
{% enddocs %}

{% docs baixa_inaptidao %}{# Baixa × inaptidão #}
**Baixa** é o encerramento definitivo da inscrição, a pedido (extinção da entidade) ou de ofício. **Inaptidão** é
declarada pela RFB, por exemplo por omissão de declarações por 90 dias ou mais, e é reversível com a
regularização. A inaptidão por omissão sai em lotes, por ato declaratório com uma lista de inscrições, e põe a
mesma data da situação em milhões de estabelecimentos.

Por isso "encerramento" (todo não ativo) não é "fechamento definitivo": para este, use as baixas.
{% enddocs %}

{% docs porte %}{# Porte #}
**Porte** é o código do porte da empresa no leiaute: 00 não informado, 01 microempresa (ME, receita bruta anual
até R$ 360 mil), 03 empresa de pequeno porte (EPP, até R$ 4,8 milhões) e 05 demais (LC 123/2006, art. 3º).

O porte é **declarado** no registro, não medido: os dados abertos não trazem a receita. MEI não é porte, é uma
opção de tributação. "Não informado" aparece de dois jeitos: o código 00 da RFB (rótulo N/A) e o membro -1 (NÃO
INFORMADO) do modelo estrela.
{% enddocs %}

{% docs natureza_juridica %}{# Natureza jurídica #}
**Natureza jurídica** é a forma jurídica da empresa, com código de 4 dígitos da tabela CONCLA/IBGE, em cinco
grupos: administração pública, entidades empresariais (como LTDA, S/A e empresário individual), entidades sem fins
lucrativos, pessoas físicas e organizações internacionais.

**MEI não é natureza jurídica**: quase todo MEI tem a natureza 2135 (Empresário Individual), mas para achar MEI use
a opção pelo MEI, não a natureza.
{% enddocs %}

{% docs cnae_principal %}{# CNAE principal #}
**CNAE** é a Classificação Nacional de Atividades Econômicas (CONCLA/IBGE, CNAE-Subclasses 2.3), em cinco níveis:
seção, divisão, grupo, classe (5 dígitos) e subclasse (7 dígitos). Cada estabelecimento tem **um CNAE fiscal
principal**.

As contagens, os marts e as métricas do projeto recortam pelo CNAE principal, na subclasse de 7 dígitos (lojas de
tintas = 4741500). O CEMPRE do IBGE usa a classe de 5 dígitos (47415).
{% enddocs %}

{% docs cnae_secundario %}{# CNAEs secundários #}
**CNAEs secundários** são as outras atividades do estabelecimento, zero ou mais, separadas por vírgula no arquivo
da RFB. O projeto as guarda numa ponte muitos-para-muitos, fora das métricas: um estabelecimento que tem a
atividade só como secundária não entra num recorte pelo CNAE principal. Depois de juntar a ponte, conte
estabelecimentos distintos.
{% enddocs %}

{% docs simples_nacional %}{# Simples Nacional #}
**Simples Nacional** é o regime unificado de arrecadação de tributos das microempresas e empresas de pequeno
porte (LC 123/2006, art. 12). A opção é anual e o arquivo Simples da RFB traz, por CNPJ básico, a opção e as datas
de opção e de exclusão.

No projeto, a flag é a situação **no extrato** do mês; empresa sem registro no arquivo Simples vira falso.
{% enddocs %}

{% docs mei %}{# MEI #}
**MEI (microempreendedor individual)** é o optante pelo Simples Nacional que recolhe em valores fixos mensais, o
SIMEI (LC 123/2006, art. 18-A): receita bruta anual de até R$ 81 mil em 2026, um único estabelecimento e no máximo
um empregado. Todo MEI é optante pelo Simples; o contrário não vale.

MEI não é porte nem natureza jurídica: identifique-o pela opção pelo MEI. O dado real tem filiais de empresas MEI,
por isso a contagem de MEI ativos (por estabelecimento) pode passar um pouco do número de empresas MEI.
{% enddocs %}

{% docs capital_social %}{# Capital social #}
**Capital social** é o capital declarado da **empresa**, no arquivo Empresas. Como o projeto copia os atributos da
empresa para cada estabelecimento, o capital se repete nas filiais: some ou tire a média **só nas matrizes**.
Capital social não é faturamento.
{% enddocs %}

{% docs municipio %}{# Município (código RFB × IBGE) #}
**Município**: o arquivo Estabelecimentos traz o código do município da **tabela da RFB** (4 dígitos), que não é o
código IBGE (7 dígitos). O projeto converte um no outro pelo diretório de municípios da Base dos Dados e usa o
código IBGE como chave. Sem par, o estabelecimento fica no membro -1 (NÃO INFORMADO).

Para achar um município pelo nome, use sempre a UF: há homônimos (Água Branca existe em AL, PB e PI).
{% enddocs %}

{% docs data_referencia %}{# Data de referência #}
**Data de referência** é a data do extrato mensal da RFB (por exemplo, 12/09/2026 no extrato de 2026-09). Idade,
prazos e "ano corrente" são relativos a ela, nunca à data de hoje. O último mês e o último ano do extrato são
parciais: o extrato vai só até a data de referência.
{% enddocs %}

{% docs fotografia_mensal %}{# Fotografia mensal #}
**Fotografia mensal**: cada mês da RFB é um extrato completo do cadastro, não um registro de eventos. O mesmo
estabelecimento ativo aparece em todos os meses em que segue ativo, então **não se somam meses**. Num período maior
que o mês, vale o último mês do período (nas métricas, o último mês em que o recorte filtrado tem linhas).

Comparando dois extratos se vê a variação líquida do estoque, não quem entrou e quem saiu. Só o resumo mensal
guarda a série de meses; as outras tabelas do gold são do mês corrente.
{% enddocs %}

{% docs abertura_encerramento %}{# Abertura e encerramento #}
**Abertura** e **encerramento** são eventos derivados pelo projeto, não publicados pela RFB. Abertura: o
estabelecimento contado na data de início de atividade. Encerramento: todo estabelecimento **não ativo** (nulo,
suspenso, inapto ou baixado) contado na data da situação. Baixa: só os BAIXADOS, na data da situação. Saldo =
aberturas − encerramentos. Data ausente ou anterior a 1900 não gera evento.

Como só existe a situação atual, um inativo reativado deixa de contar como encerramento. Lotes de inaptidão e o ano
parcial do extrato distorcem os encerramentos e o saldo de um ano.
{% enddocs %}

{% docs sobrevivencia %}{# Sobrevivência por coorte #}
**Sobrevivência a N anos** (1, 3 ou 5) é a fração dos elegíveis de uma coorte de abertura (o ano de início de
atividade) que seguiam ativos N anos depois da abertura: **ativos hoje ou encerrados a partir do aniversário de N
anos**. Não é "ainda ativo": um estabelecimento aberto em 2015 e baixado em 2024 sobrevive aos 3 e aos 5 anos.

A coorte só é elegível quando inteira já completou N anos (31/12 do ano de abertura + N até a data de
referência). A taxa soma elegíveis e sobreviventes dos estratos antes de dividir.
{% enddocs %}

{% docs concorrencia_densidade %}{# Concorrência e densidade #}
**Concorrência** no projeto é o número de estabelecimentos **ativos** de um CNAE principal num município.
**Densidade** é essa contagem relativa ao tamanho do mercado: ativos por 10 mil habitantes (população estimada) ou
por mil domicílios (Censo 2022). "Muita concorrência" exige um critério explícito: ranking na UF, vizinhos ou área
de mercado.
{% enddocs %}

{% docs area_mercado %}{# Área de mercado #}
**Área de mercado** é o município somado aos seus vizinhos de fronteira. O projeto conta os ativos do CNAE no
município, nos vizinhos e na região metropolitana, com a densidade da área por mil domicílios e por km², e marca os
**vazios de mercado**: municípios sem estabelecimento local do CNAE, mas com ativos nos vizinhos ou na região
metropolitana. Fronteira não é raio em km nem fluxo de compra: para o fluxo, veja o polo de compras da REGIC.
{% enddocs %}

{% docs cempre %}{# CEMPRE #}
**CEMPRE** é o Cadastro Central de Empresas do IBGE: empresas e organizações formais ativas e suas **unidades
locais** (endereços de atuação), com pessoal ocupado, assalariados e salários, por município × classe CNAE, em
31/12 do ano do CEMPRE (hoje 2024). Não inclui MEI e conta o que tem sinal de atividade.

A comparação justa com a RFB é de unidades locais com ativos sem MEI. Células que identificariam o informante vêm
com sigilo: o pessoal e os salários ficam nulos, e somá-los dá um piso, não o total.
{% enddocs %}

{% docs renda_censo %}{# Renda per capita (Censo 2022) #}
**Renda per capita** é o rendimento domiciliar per capita médio e mediano do município no Censo Demográfico 2022
(IBGE, tabela SIDRA 10295), em reais nominais de 2022, sem correção. A média é puxada pelas rendas altas; a mediana
descreve o domicílio típico. É renda do morador, não salário de quem trabalha no setor.
{% enddocs %}

{% docs regic_polo_compras %}{# REGIC e polo de compras #}
**REGIC** (Regiões de Influência das Cidades, IBGE, 2018) classifica as cidades numa hierarquia urbana (Metrópole,
Capital Regional, Centro Sub-Regional, Centro de Zona, Centro Local) e mede para onde os moradores de cada município
vão comprar bens e usar serviços.

O **polo de compras** do projeto é o destino com o maior percentual no tema móveis e eletroeletrônicos. O
percentual divide os deslocamentos **entre os destinos de fora**: "45 % em Serra" é 45 % de quem compra fora, não de
toda a compra. Os 67 municípios mais centrais não têm polo.
{% enddocs %}

{% docs valor_adicionado %}{# Valor adicionado #}
**Valor adicionado (VA)** é a abertura do PIB dos Municípios (IBGE, pela Base dos Dados) em agropecuária,
indústria, serviços e administração pública. As aberturas saem depois do PIB total: hoje o PIB vai até 2023 e o VA
até 2021. As participações somam 100, salvo quando o IBGE publica VA negativo.
{% enddocs %}
