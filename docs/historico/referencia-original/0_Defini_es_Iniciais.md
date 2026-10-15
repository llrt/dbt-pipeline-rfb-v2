### [markdown]
### Problema a ser resolvido

Sou um consultor de negócios que está apoiando com dados a abertura de uma nova empresa no setor de venda de tintas. É viável abrir esse negócio na cidade de Fundão/ES? Há muitas empresas concorrentes na região? Há fornecedores próximos de onde conseguiria comprar insumos?


### [markdown]

### Ideia para o MVP
Construir uma base de dados que possa ser utilizado para pesquisas de mercado para criação de novas empresas ou lançamentos de produtos, utilizando-se como ponto de partida a base pública de empresas da RFB (QSA).

### [markdown]


### Ex de perguntas a serem respondidas (idealmente):
- Quantas empresas concorrentes existem de um determinado setor (CNAE) numa determinada localidade (município/UF), onde se deseja abrir a empresa ? São muitas? Se são poucas, pode indicar que não há mercado na região. Se são muitas, pode indicar que o mercado está muito saturado.
- Qual a idade média das empresas que atuam atualmente naquele setor?
- Como estão distribuídas as empresas daquele setor em termos de porte (tamanho da empresa relacionado ao seu faturamento)? Há espaço para empresas menores? As empresas menores são muito recentes ou conseguem sobreviver aos primeiros 3 anos de vida?
- Quantas empresas potencialmente fornecedoras existem nas proximidades daquela localidade (microrregião, mesorregião)?


### [markdown]

### Bases
Como ponto de partida, utilizaremos as seguintes bases:
- QSA (RFB) - base pública de empresas (CNPJ) - disponível em: 
>  https://dados.gov.br/dados/conjuntos-dados/cadastro-nacional-da-pessoa-juridica---cnpj
>  https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/2025-02/
- CNAE (IBGE) - dados de domínio de CNAE (Código Nacional de Atividade Econômica) - disponível em:
- Censo demográfico (IBGE) - disponível em: 
- Municípios (IBGE) - disponível em: 
- Microrregiões e mesorregiões (IBGE) - disponível em: 


### [markdown]

### Pipeline de Dados
* Os dados de QSA e CNAE serão ingeridos inicialmente no banco Spark disponível no Databricks (Community Edition)
* Na sequência, serão criados modelos de dados granular e agregado com os dados de empresa em formato flat table, para fazer as análises


### [markdown]

### Observações
* Os dados serão baixados das fontes de forma estática e carregados no Spark. Não é escopo deste MVP automatizar a captura dos dados em um pipeline com execução automatizada / periódica

### [markdown]

