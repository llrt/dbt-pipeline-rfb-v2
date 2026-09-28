### [markdown]
# Análise de Dados / Solução do problema posto

Com base no modelo de dados construído, vamos buscar solucionar as questões colocadas. Vamos relembrar o problema a ser resolvido e as perguntas propostas:

### [markdown]
### Problema a ser resolvido

Sou um consultor de negócios que está apoiando com dados a abertura de uma nova empresa no setor de venda de tintas. É viável abrir esse negócio na cidade de Fundão/ES? Há muitas empresas concorrentes na região? Há fornecedores próximos de onde conseguiria comprar insumos?

### [markdown]

### Perguntas a serem respondidas:
- Quantas empresas concorrentes existem de um determinado setor (CNAE) numa determinada localidade (município/UF), onde se deseja abrir a empresa ? São muitas? Se são poucas, pode indicar que não há mercado na região. Se são muitas, pode indicar que o mercado está muito saturado.
- Qual a idade média das empresas que atuam atualmente naquele setor?
- Como estão distribuídas as empresas daquele setor em termos de porte (tamanho da empresa relacionado ao seu faturamento)? Há espaço para empresas menores? As empresas menores são muito recentes ou conseguem sobreviver aos primeiros 3 anos de vida?
- Quantas empresas potencialmente fornecedoras existem nas proximidades daquela localidade (microrregião, mesorregião)?


### [markdown]

Então, supondo o contexto abaixo, vamos buscar responder as perguntas acima.

Contexto:
- A empresa que queremos abrir será do setor de venda em varejo (tipo mais comum) de tintas
- A empresa será aberta na cidade de Fundão/ES, cidade pequena do interior do ES, próximo à Serra/ES, Linhares/ES, Aracruz/ES


### [markdown]

### 1 - Quantas empresas concorrentes há neste setor (CNAE) e localidade (município/UF) escolhidos?

### [markdown]
Para responder a pergunta, primeiro é importante identificar qual o CNAE que estamos tratando. De acordo com o IBGE, o CNAE de venda (em atacado) de tintas é o [**4741500  - Comércio varejista de tintas e materiais para pintura**](https://cnae.ibge.gov.br/?view=subclasse&tipo=cnae&versao=10&subclasse=4741500&chave=tintas)

### [code]
%sql
select * 
from agg_empresas
where
  CNAE_principal = 4741500 -- Comércio varejista de tintas e materiais para pintura
  and municipio = 'FUNDÃO'
  and UF = 'ES'

### [markdown]
Pelo que vemos acima, no momento desta análise havia somente uma empresa ativa neste CNAE nesta localidade, uma empresa com natureza jurídica Empresário Individual (EI). Houve outras 4 empresas antes, mas todas se encontram inativas atualmente.

Destes resultados, podemos depreender que é um comércio de tintas é um empreendimento relativamente nichado, arriscado mas viável, com mercado consumidor nesta região.

### [markdown]
As próximas 2 perguntas vamos responder de forma conjunta:

### [markdown]
### 2 - Qual a idade média das empresas que atuam atualmente naquele setor e localidade?


### [markdown]

### 3 - Como estão distribuídas as empresas daquele setor em termos de porte? Há espaço para empresas menores? As empresas menores são muito recentes ou conseguem sobreviver aos primeiros 2 anos de vida?

### [markdown]
Considerando somente as empresas ativas, vamos recuperar a média de idade das empresas naquele setor e localidade.

### [code]
%sql

select porte, avg(media_idade) as media_idade, sum(qtd_empresas) as qtd_empresas 
from agg_empresas
where
  CNAE_principal = 4741500 
  and municipio = 'FUNDÃO'
  and UF = 'ES'
  and situacao = 'ATIVA'
group by porte

### [markdown]
Como havíamos visto, havia apenas uma empresa ativa naquele setor e localidade. Portanto, a média de idade é idêntica à idade daquela empresa em específico, no caso 3,9 anos (ou 3 anos e 11 meses aprox). 

Podemos ver que se trata de uma empresa com porte MICRO (faturamento até 360 mil reais) , empresas essas em geral mais vulneráveis, ainda não tão estabilizadas e com maior taxa de mortalidade - aprox metade das empresas fecham até 3 anos de idade. Entretanto, esta empresa em particular está indo bem e tem mais de 3 anos de idade. Portanto, podemos concluir que há espaço para novos entrantes, para empresas menores e com boa possibilidade de sobrevivência para além da barreira dos 3 anos.

### [markdown]
### 4 - Quantas empresas potencialmente fornecedoras existem nas proximidades daquela localidade (microrregião, mesorregião)?

### [markdown]
Esta última análise é para verificar se será possível para a futura empresa comprar insumos de forma mais barata, de fornecedores da imediação da localidade em que se encontra. Não haver fornecedores locais para apoiá-la pode ser um grande entrave e encarecer muito o custo de operação daquela empresa, eventualmente inviabilizando o novo negócio.

Para responder essa pergunta, primeiro precisamos entender quais seriam as possíveis empresas fornecedoras desta e buscar na micro e mesorregião.

Como a empresa a ser criada se propõe a vender tintas no varejo, precisamos encontrar as fabricantes de tinta. De acordo com o IBGE, o CNAE correspondente a essa atividade seria o [**2071100 - Fabricação de tintas, vernizes, esmaltes e lacas**](https://cnae.ibge.gov.br/?view=subclasse&tipo=cnae&versao=10.1.0&subclasse=2071100&chave=tintas) . Vamos então buscar as empresas com este CNAE, primeiro no município de Fundão e depois na micro e mesorregião correspondente.

### [code]
%sql
select * 
from agg_empresas
where
  CNAE_principal = 2071100 -- Fabricação de tintas, vernizes, esmaltes e lacas
  and municipio = 'FUNDÃO'
  and UF = 'ES'
  and situacao = 'ATIVA' -- para esta análise não nos interessam as empresas que não estão ativas

### [markdown]
Hummm, mal sinal, não há empresas fornecedoras no município. Mas não percamos as esperanças, vamos olhar a microrregião.

### [code]
%sql
select * 
from agg_empresas
where
  CNAE_principal = 2071100 -- Fabricação de tintas, vernizes, esmaltes e lacas
  and microrregiao_municipio in (select nome_microrregiao from municipio_bd where upper(nome) = 'FUNDÃO' and upper(sigla_uf) = 'ES')
  and situacao = 'ATIVA' -- para esta análise não nos interessam as empresas que não estão ativas

### [markdown]
Ainda nada de empresas fornecedoras nas imediações! Vamos expandir a busca para a mesorregião..

### [code]
%sql
select * 
from agg_empresas
where
  CNAE_principal = 2071100 -- Fabricação de tintas, vernizes, esmaltes e lacas
  and mesorregiao_municipio in (select nome_mesorregiao from municipio_bd where upper(nome) = 'FUNDÃO' and upper(sigla_uf) = 'ES')
  and situacao = 'ATIVA' -- para esta análise não nos interessam as empresas que não estão ativas

### [markdown]
=\ Agora estamos preocupados. Não há empresas fabricantes nas proximidades, nem na localidade, nem na microrregião, nem na mesorregião. Isso poderia indicar que o custo dos insumos poderia ser mais elevado. Mas calma! Não consideramos em nossa análise que empresas de comércio varejista normalmente compram insumos de comércio atacadista. Vejamos:

### [code]
%sql
select * 
from agg_empresas
where
  CNAE_principal in (
    4679601, -- Comércio atacadista de tintas, vernizes e similares
    4679699 --  Comércio atacadista de materiais de construção em geral 
  ) 
  and mesorregiao_municipio in (select nome_mesorregiao from municipio_bd where upper(nome) = 'FUNDÃO' and upper(sigla_uf) = 'ES')
  and situacao = 'ATIVA' -- para esta análise não nos interessam as empresas que não estão ativas

### [markdown]
Também não temos nada de comércio atacadista nas imediações... =\
 

### [markdown]

Porém, um leitor atento verá que consideramos apenas as empresa cuja atividade *principal* é de fabricação ou comércio atacadista de tintas. Na realidade, empresas podem desempenhar essas atividades, mas não ser a sua atividade principal, de forma que uma pesquisa pelo `CNAE_principal` pode não ser adequada. Para uma busca completa, vamos recorrer à base granular:


### [code]
%sql
select * 
from bh_empresas
where
  (
    CNAEs_secundarios like '%2071100%' -- que contenha na lista de CNAEs secundários o CNAE de Fabricação de tintas, vernizes, esmaltes e lacas, em qq ordem
    or CNAEs_secundarios like '%4679601%' -- que contenha na lista de CNAEs secundários o CNAE de Comércio atacadista de tintas, vernizes e similares, em qq ordem
    or CNAEs_secundarios like '%4679699%' -- que contenha na lista de CNAEs secundários o CNAE de Comércio atacadista de materiais de construção em geral, em qq ordem
  ) 
  and mesorregiao_municipio in (select nome_mesorregiao from municipio_bd where upper(nome) = 'FUNDÃO' and upper(sigla_uf) = 'ES')
  and situacao = 'ATIVA' -- para esta análise não nos interessam as empresas que não estão ativas

### [markdown]
Bom, agora realmente esgotamos possibilidades na microrregião e mesorregião imediatas de Fundão/ES. Vamos considerar como último recurso de viabilidade do empreendimento, a compra de qq município do ES: 

### [code]
%sql
select * 
from bh_empresas
where
  (
    CNAEs_secundarios like '%2071100%' -- que contenha na lista de CNAEs secundários o CNAE de Fabricação de tintas, vernizes, esmaltes e lacas, em qq ordem
    or CNAEs_secundarios like '%4679601%' -- que contenha na lista de CNAEs secundários o CNAE de Comércio atacadista de tintas, vernizes e similares, em qq ordem
    or CNAEs_secundarios like '%4679699%' -- que contenha na lista de CNAEs secundários o CNAE de Comércio atacadista de materiais de construção em geral, em qq ordem
  ) 
  and UF = 'ES'
  and situacao = 'ATIVA' -- para esta análise não nos interessam as empresas que não estão ativas

### [markdown]
Ótimo, temos muitas opções no ES, algumas até relativamente próximas, no município de Serra/ES, Vila Velha/ES, Vitória/ES, Cariacica/ES e Linhares/ES.


### [markdown]

### Conclusões Finais

Com a ajuda das bases de dados criadas, com relativo pouco esforço de análise, pudemos comprovar que é viável abrir um empreendimento de venda de tintas na localidade de Fundão/ES . Entretanto, chama a atenção que não há muitas empresas desse tema na região, que não fornecedores nas proximidades imediatas. Isso denota que o empreendimento carrega um maior risco e que deve ser aprofundada a análise com outros elementos e fatores, como custo de insumos, preços, margem de lucro, necessidade de aporte de capital, etc, todos fora do escopo deste trabalho, para fundamentar finalmente a decisão ou não de abrir este empreendimento.
