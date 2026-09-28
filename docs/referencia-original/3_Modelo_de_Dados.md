### [markdown]
# Modelagem


### [markdown]
### Intro

Faremos agora a modelagem da base de dados que será de fato utilizada nas análises das questões postas na introdução (0 - Definições Iniciais) . 

Partiremos das bases cruas, criaremos uma flat table granular com dados de empresas e depois criaremos em cima desta flat table uma outra flat table mas com dados agregados, para uma apuração mais ágil das estatísticas. Em termos de uma arquitetura medallion (https://www.databricks.com/glossary/medallion-architecture), as bases cruas seriam a camada bronze ("landing zone", raw data), a flat table granular seria a camada silver (cleansed and conformed data) e a flat table com dados agregados seria a camada gold (curated business-level tables) .

### [markdown]
### Premissas e decisões iniciais

- Iremos criar uma flat table granular para simplificar o modelo de dados, tratando os dados e juntando as infos de domínio que estão espalhadas em várias tabelas para facilitar o entendimento dos dados
- A flat table granular será criada no nível de estabelecimento (CNPJ completo), mas como as pessoas chamam isso coloquialmente de "empresa", iremos nomear a tabela como bh_empresa (bh = base humanizada)
- Como não precisaremos de todas as colunas existentes nas bases cruas, iremos simplificar e trazer para o modelo somente as colunas que interessam. Para orientar o conjunto inicial necessário, vamos reproduzir novamente mais abaixo as perguntas gerais que queremos responder. Futuramente, caso sejam necessárias outras análises, será simples adicionar outras colunas
- Onde necessário, iremos cruzar com as outras bases de domínio do site Base dos Dados, para trazer infos mais ricas
- Finalmente, será criado uma flat table com dados agregados a partir da flat table com dados granulares, para business intelligence de forma mais ágil. Caso seja necessária uma análise mais detalhada, sempre poderemos recorrer à flat table granular

### [markdown]
### Perguntas a serem respondidas (idealmente):
- Quantas empresas concorrentes existem de um determinado setor (CNAE) numa determinada localidade (município/UF), onde se deseja abrir a empresa ? São muitas? Se são poucas, pode indicar que não há mercado na região. Se são muitas, pode indicar que o mercado está muito saturado.
- Qual a idade média das empresas que atuam atualmente naquele setor?
- Como estão distribuídas as empresas daquele setor em termos de porte (tamanho da empresa relacionado ao seu faturamento)? Há espaço para empresas menores? As empresas menores são muito recentes ou conseguem sobreviver aos primeiros 3 anos de vida?
- Quantas empresas potencialmente fornecedoras existem nas proximidades daquela localidade (microrregião, mesorregião)?

### [markdown]
### Descrição da base (campos, metadados, linhagem, etc)

Abaixo segue a descrição dos modelos flat table granular e flat table agregado

**BH Empresas** (Flat Table)

Tabela `bh_empresas`:

| Nome do Campo | Descrição Semântica | Linhagem | Tipo | Domínio de Dados |
|---------------|---------------------|----------|------|------------------|
| `cnpj_raiz` | 8 primeiros dígitos de CNPJ da empresa | - Fonte: `empresas.cnpj_raiz` <br/> - Transformação: prefixar (lpad) com caracteres '0' | string | Campo deve ser preenchido com caracteres numéricos, prefixado com 0s se necessário | 
| `cnpj_completo` | CNPJ completo da empresa, com 14 dígitos | - Fonte: `estabelecimentos.cnpj_raiz`, `estabelecimentos.cnpj_ordem`, `estabelecimentos.cnpj_dv` <br/> - Transformação: prefixar a esquerda (lpad) com caracteres '0' os dígitos | string | Campo deve ser preenchido com caracteres numéricos das componentes do CNPJ, prefixados a esquerda com 0s se necessário | 
| `nome` | Nome da Empresa | - Fonte: `estabelecimentos.nome_fantasia`, `empresas.razao_social` <br/> - Transformação: `razao_social` apenas caso `nome_fantasia` seja null, seguido de upper case para padronizar | string | Campo deve ser preenchido com caracteres alfanuméricos do nome da empresa | 
| `natureza_juridica` | Natureza Jurídica da empresa, i.e. uma espécie de "tipo" (em termos jurídicos e fiscais) da empresa | - Fonte: `natureza_juridica.descricao` do registro com `natureza_juridica.codigo = empresas.natureza_jur` <br/> - Transformação: upper case (para padronizar) | string | Campo deve ser preenchido com caracteres alfanuméricos do nome da empresa |
| `porte` | Porte da empresa, i.e. uma espécie de "tamanho" (em termos de faturamento) da empresa | - Fonte: `empresa.porte` <br/> - Transformação: mapeamento do código de porte, segundo a regra 0 - "N/A", 1 - "MICRO", 3 - "PEQUENA", 5 - "DEMAIS" | string | Campo deve ser preenchido apenas com os valores "N/A", "MICRO", "PEQUENA", "DEMAIS" |
| `CNAE_principal` | subclasse do CNAE (código nacional de atividade econômica) principal da empresa, i.e. um código padronizado com a atividade desempenhada por aquela empresa | - Fonte: `estabelecimentos.CNAE_principal` <br/> - Transformação: nenhuma | string | Campo deve ser preenchido com 7 caracteres numéricos, correspondente a um CNAE completo segundo a classificação do IBGE (https://cnae.ibge.gov.br/) |
| `desc_CNAE_principal` | Descrição textual da subclasse do CNAE (código nacional de atividade econômica) principal da empresa, i.e. a descrição padronizada da atividade desempenhada por aquela empresa | - Fonte: `cnae_bd.descricao_subclasse` do registro em que `cnae_bd.subclasse = est.CNAE_principal` <br/> - Transformação: upper case (para padronizar) | string | Campo deve ser preenchido com texto que descreve a atividade econômica, segundo a padronização do IBGE (https://cnae.ibge.gov.br/) |
| `grupo_CNAE_principal` | Descrição textual do grupo padronizado (agregador correspondente aos 3 primeiros dígitos de um CNAE completo) ao qual o CNAE (código nacional de atividade econômica) principal da empresa, i.e. a descrição padronizada da atividade desempenhada por aquela empresa | - Fonte: `cnae_bd.descricao_subclasse` do registro em que `cnae_bd.subclasse = est.CNAE_principal` <br/> - Transformação: upper case (para padronizar) | string | Campo deve ser preenchido com texto que descreve o grupo correspondente àquela atividade econômica principal da empresa, segundo a padronização do IBGE (https://cnae.ibge.gov.br/) |
| `CNAEs_secundarios` | subclasses, separadas por vírgula, dos CNAEs (código nacional de atividade econômica) secundários da empresa | - Fonte: `estabelecimentos.CNAEs_secundarios` <br/> - Transformação: nenhuma | string | Campo deve ser preenchido com CNAEs separados por vírgula, cada qual com 7 caracteres numéricos, correspondente a um CNAE completo segundo a classificação do IBGE (https://cnae.ibge.gov.br/) |
| `municipio` | Nome do município onde se encontra aquela empresa | - Fonte: `municipio_bd.nome` do registro em que `municipio_bd.id_municipio_rf = estabelecimentos.municipio` <br/> - Transformação: upper case (para padronizar) | string | Campo deve ser preenchido com nome de município válido, segundo o IBGE |
| `microrregiao_municipio` | Nome da microrregião do município onde se encontra aquela empresa, sendo microrregião um agregado de municípios geograficamente vizinhos/próximos | - Fonte: `municipio_bd.nome_microrregiao` do registro em que `municipio_bd.id_municipio_rf = estabelecimentos.municipio` <br/> - Transformação: upper case (para padronizar) | string | Campo deve ser preenchido com nome de microrregião válida, segundo o IBGE |
| `mesorregiao_municipio` | Nome da mesorregião do município onde se encontra aquela empresa, sendo mesorregião um agregado de microrregiões geograficamente vizinhas/próximas | - Fonte: `municipio_bd.nome_mesorregiao` do registro em que `municipio_bd.id_municipio_rf = estabelecimentos.municipio` <br/> - Transformação: upper case (para padronizar) | string | Campo deve ser preenchido com nome de mesorregião válida, segundo o IBGE |
| `UF` | Sigla da UF do município onde se encontra aquela empresa | - Fonte: `municipio_bd.sigla_UF` do registro em que `municipio_bd.id_municipio_rf = estabelecimentos.municipio` <br/> - Transformação: upper case (para padronizar) | string | Campo deve ser preenchido com sigla de UF válida, segundo o IBGE |
| `situacao` | Situação da empresa, se ativa ou inativa | - Fonte: `estabelecimentos.situacao` - Transformação: mapeamento do código de situação, segundo a regra 2 - "ATIVA", else (qq outro código) - "INATIVA" | string | Campo deve ser preenchido com preenchido apenas com os valores "ATIVA", "INATIVA" |
| `idade_atual` | Idade atual da empresa, apenas se a empresa estiver ativa | - Fonte: `estabelecimentos.dat_inicio_atividade` - Transformação: se situacao = ATIVA, diferença entre a data atual (hoje) e a data de início de atividade, em anos; se estiver INATIVA, null  | integer | Campo deve ser numérico, contendo idade em anos de empresa, se ativa; se inativa, valor será null. Não é esperado empresas com mais de 200 anos de idade (seria uma empresa que existe desde o início do período Imperial do Brasil) |


### [code]
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("ModeloMVP").getOrCreate()

### [code]
# considerando as premissas de modelagem acima, executa via Spark o SQL que retorna a base já tratada e que desejamos persistir
df = spark.sql("""
select 
  lpad(est.cnpj_raiz, 8, 0) as cnpj_raiz, concat(lpad(est.cnpj_raiz, 8, 0), lpad(est.cnpj_ordem, 4, 0), lpad(est.cnpj_dv, 2, 0)) as cnpj_completo, 
  upper(nvl(est.nome_fantasia, emp.razao_social)) as nome,
  upper(nat_jur.descricao) as natureza_juridica, 
  case emp.porte
    when 0 then 'N/A'
    when 1 then 'MICRO'
    when 3 then 'PEQUENA'
    when 5 then 'DEMAIS'
    else null
  end as porte, 
  est.CNAE_principal, 
  upper(cnae_princ.descricao_subclasse) as desc_CNAE_principal,
  upper(cnae_princ.descricao_grupo) as grupo_CNAE_principal,
  est.CNAEs_secundarios, 
  upper(mun.nome) as municipio,
  upper(mun.nome_microrregiao) as microrregiao_municipio,
  upper(mun.nome_mesorregiao) as mesorregiao_municipio,
  upper(mun.sigla_UF) as UF,
  case est.situacao
    when 2 then 'ATIVA'
    else 'INATIVA'
  end as situacao,
  case est.situacao
    when 2 then round(datediff(now(), to_date(est.dat_inicio_atividade, 'yyyyMMdd'))/365.25, 1)
    else null
  end as idade_atual
from empresas emp
  inner join estabelecimentos est on emp.cnpj_raiz = est.cnpj_raiz
  inner join natureza_juridica nat_jur on nat_jur.codigo = emp.natureza_jur
  inner join cnae_bd cnae_princ on cnae_princ.subclasse = est.CNAE_principal
  inner join municipio_bd mun on mun.id_municipio_rf = est.municipio
""")

# finalmente, carrega os dados da base tratada em uma tabela Spark
df.write.option("encoding", "iso-8859-1").option("overwriteSchema", "true").mode("overwrite").saveAsTable("bh_empresas")

### [code]
%sql
select * from bh_empresas

### [markdown]
**Agg Empresas** (Flat Table)

Tabela `agg_empresas`:

| Nome do Campo | Descrição Semântica | Linhagem | Tipo | Domínio de Dados |
|---------------|---------------------|----------|------|------------------|
| `municipio` | Nome do município onde se encontra aquela empresa | - Fonte: `bh_empresas.municipio` - Transformação: nenhuma | string | Campo deve ser preenchido com nome de município válido, segundo o IBGE |
| `microrregiao_municipio` | Nome da microrregião do município onde se encontra aquela empresa, sendo microrregião um agregado de municípios geograficamente vizinhos/próximos | - Fonte: `bh_empresas.microrregiao_municipio` - Transformação: nenhuma | string | Campo deve ser preenchido com nome de microrregião válida, segundo o IBGE |
| `mesorregiao_municipio` | Nome da mesorregião do município onde se encontra aquela empresa, sendo mesorregião um agregado de microrregiões geograficamente vizinhas/próximas | - Fonte: `bh_empresas.mesorregiao_municipio` - Transformação: nenhuma | string | Campo deve ser preenchido com nome de mesorregião válida, segundo o IBGE |
| `UF` | Sigla da UF do município onde se encontra aquela empresa | - Fonte: `bh_empresas.UF` - Transformação: nenhuma | string | Campo deve ser preenchido com sigla de UF válida, segundo o IBGE |
| `CNAE_principal` | subclasse do CNAE (código nacional de atividade econômica) principal da empresa, i.e. um código padronizado com a atividade desempenhada por aquela empresa | - Fonte: `bh_empresas.CNAE_principal` - Transformação: nenhuma | string | Campo deve ser preenchido com 7 caracteres numéricos, correspondente a um CNAE completo segundo a classificação do IBGE (https://cnae.ibge.gov.br/) |
| `desc_CNAE_principal` | Descrição textual da subclasse do CNAE (código nacional de atividade econômica) principal da empresa, i.e. a descrição padronizada da atividade desempenhada por aquela empresa | - Fonte: `bh_empresas.desc_CNAE_principal` - Transformação: nenhuma | string | Campo deve ser preenchido com texto que descreve a atividade econômica, segundo a padronização do IBGE (https://cnae.ibge.gov.br/) |
| `grupo_CNAE_principal` | Descrição textual do grupo padronizado (agregador correspondente aos 3 primeiros dígitos de um CNAE completo) ao qual o CNAE (código nacional de atividade econômica) principal da empresa, i.e. a descrição padronizada da atividade desempenhada por aquela empresa | - Fonte: `bh_empresas.grupo_CNAE_principal` - Transformação: nenhuma | string | Campo deve ser preenchido com texto que descreve o grupo correspondente àquela atividade econômica principal da empresa, segundo a padronização do IBGE (https://cnae.ibge.gov.br/) |
| `natureza_juridica` | Natureza Jurídica da empresa, i.e. uma espécie de "tipo" (em termos jurídicos e fiscais) da empresa | - Fonte: `bh_empresas.natureza_juridica` - Transformação: nenhuma | string | Campo deve ser preenchido com caracteres alfanuméricos do nome da empresa |
| `porte` | Porte da empresa, i.e. uma espécie de "tamanho" (em termos de faturamento) da empresa | - Fonte: `bh_empresas.porte` - Transformação: nenhuma | string | Campo deve ser preenchido com caracteres alfanuméricos do nome da empresa | string | Campo deve ser preenchido apenas com os valores "N/A", "MICRO", "PEQUENA", "DEMAIS" |
| `situacao` | Situação da empresa, se ativa ou inativa | - Fonte: `bh_empresas.situacao` - Transformação: nenhuma | string | Campo deve ser preenchido com preenchido apenas com os valores "ATIVA", "INATIVA" |
| `qtd_empresas` | Count do nr de empresas naquele estrato (combinação das demais dimensões) | - Fonte: `bh_empresas.cnpj_completo` - Transformação: contagem (count)  | integer | Campo numérico, count de registros da bh_empresas |
| `media_idade` | Média da idade de empresas naquele estrato (combinação das demais dimensões), em anos | - Fonte: `bh_empresas.idade_atual` - Transformação: média simples (avg)  | integer | Campo numérico, média de idade em anos; não são esperados valores maiores que 200 anos |

### [code]
# considerando as premissas de modelagem acima, executa via Spark o SQL que retorna a base já tratada e que desejamos persistir
df = spark.sql("""
select 
  municipio,
  microrregiao_municipio,
  mesorregiao_municipio,
  UF,
  CNAE_principal, 
  desc_CNAE_principal,
  grupo_CNAE_principal,
  natureza_juridica,
  porte,
  situacao,
  count(cnpj_completo) as qtd_empresas,
  avg(idade_atual) as media_idade
from bh_empresas
group by 
  municipio, microrregiao_municipio, mesorregiao_municipio, UF, 
  CNAE_principal, desc_CNAE_principal, grupo_CNAE_principal,
  natureza_juridica, porte, situacao 
""")

# finalmente, carrega os dados da base tratada em uma tabela Spark
df.write.option("encoding", "iso-8859-1").option("overwriteSchema", "true").mode("overwrite").saveAsTable("agg_empresas")

### [code]
%sql
select * from agg_empresas
