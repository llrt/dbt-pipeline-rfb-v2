### [markdown]
# Coleta e Carga

Neste trabalho utilizaremos uma abordagem ELTL(Extract-Load-Transform-Load), onde os dados de interesse serão primeiro extraídos e carregados crus, depois faremos dois modelos derivados deste, um com dados granulares e outro agregado.

Todos os dados crus que iremos utilizar neste trabalho são dados públicos, sem qq restrição de uso e sem dados pessoais envolvidos.

### [markdown]
## 1 - QSA / RFB

Iremos utilizar como ponto de partida para a resolução das questões postas a base pública de dados de empresas (CNPJ, QSA) da RFB, porque é a base que contém os dados oficiais de empresas, de onde podemos fazer uma pesquisa de mercado mais fidedigna possível.

Os dados da base estão disponíveis como arquivos zip em pastas no endereço base abaixo:
https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/

Os dados mais recentes disponíveis quando da realização deste trabalho são os de fev/2025, disponíveis em:

https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/2025-02/

Estaremos baixando os dados de Empresas, Estabelecimentos e as tabelas de domínio de CNAEs, Municípios, Motivos de Situação e Natureza Jurídica.

IMPORTANTE:
- Esta é uma base GRANDE, com mais de 15 milhões de empresas ativas cadastradas e mais de 16 GB de tamanho. Vamos tentar baixar todos os dados e carregar no Spark
- Apesar de não dizer claramente na sua doc, é possível constatar que os arquivos da RFB vem em encoding ISO-8859-1. É importante no processamento dos arquivos no Spark utilizar este encoding correto na leitura e persistência dos dados

### [markdown]
### Coleta / Extração (geral)

O processamento no Databricks Community Edition parece ser limitado a 1 h. Como baixar os arquivos, dezipar e processar no Spark dentro da plataforma estava levando muito tempo, não foi possível fazer tudo dentro da plataforma.

A solução encontrada foi baixar os arquivos offline no meu computador pessoal, dezipar os arquivos localmente e subí-los para um bucket S3 (no caso do Tigris (https://www.tigrisdata.com/), que parece ser mais barato que o S3 da AWS) e de lá ler no Spark do Databricks e salvar em uma Spark Table.

### [code]
# instalar libs necessárias:
# dotenv -> para leitura de variáveis de ambiente, para não deixar secrets explícitos no código
# boto3 -> para interação com storages S3-like 

!pip install dotenv
!pip install boto3

--- out:
Collecting dotenv
  Using cached dotenv-0.9.9-py2.py3-none-any.whl (1.9 kB)
Collecting python-dotenv
  Using cached python_dotenv-1.0.1-py3-none-any.whl (19 kB)
Installing collected packages: python-dotenv, dotenv
Successfully installed dotenv-0.9.9 python-dotenv-1.0.1
[33mWARNING: You are using pip version 21.2.4; however, version 25.0.1 is available.
You should consider upgrading via the '/local_disk0/.ephemeral_nfs/envs/pythonEnv-e2138243-6b66-4d28-a44d-6b03143ea468/bin/python -m pip install --upgrade pip' command.[0m
Requirement already satisfied: boto3 in /databricks/python3/lib

### [code]
# copiando arquivo .env do dbfs para o dir local, para que a lib dotenv consiga ler
dbutils.fs.cp("dbfs:/FileStore/.env", "file:/tmp/env/", True) 

--- out:
Out[2]: True

### [code]
# configurações preliminares

import os
import gc
from pyspark.sql import SparkSession
from dotenv import load_dotenv

load_dotenv(dotenv_path="/tmp/env") # ler arquivo .env do dir local
print("Variáveis de ambiente carregadas")

--- out:
Variáveis de ambiente carregadas


### [code]
# configuração geral do Spark

spark = SparkSession.builder.appName("CargaMVP") \
    .getOrCreate()

# setar variáveis para acessar o Tigris
spark.sparkContext._jsc.hadoopConfiguration().set("fs.s3a.endpoint", os.getenv("AWS_ENDPOINT_URL_S3"))
spark.sparkContext._jsc.hadoopConfiguration().set("fs.s3a.access.key", os.getenv("AWS_ACCESS_KEY_ID"))
spark.sparkContext._jsc.hadoopConfiguration().set("fs.s3a.secret.key", os.getenv("AWS_SECRET_ACCESS_KEY"))
spark.sparkContext._jsc.hadoopConfiguration().set("fs.s3a.path.style.access", "true")
spark.sparkContext._jsc.hadoopConfiguration().set("fs.s3a.connection.ssl.enabled", "true")



### [markdown]
### 1.1 - Dados de Empresas (CNPJ raiz, 8 dígitos)

### [markdown]
#### Carga

### [code]

# path S3 no Tigris onde estão os dados de Empresas
s3_dir = "s3a://pos-pucrio-dados/mvp_sprint_eng_dados/emp/"

# os arquivos da RFB estão vindo sem header - ler primeiro sem headers e acrescentar na mão depois
# OBS: infelizmente, em alguns dos registros há um caracter '\' no nome da empresa escapando indevidamente as aspas duplas ('"') do fim da razao social... mudar caracter de escape para '"'
df_sem_headers = spark.read.option("delimiter", ";").option("escape", "\"").option("multiLine", True).option("encoding", "iso-8859-1").csv(s3_dir, header=False, inferSchema=True) 

# headers segundo doc (https://www.gov.br/receitafederal/dados/cnpj-metadados.pdf)
headers = ["cnpj_raiz", "razao_social", "natureza_jur", "qualificacao_resp", "capital_soc", "porte", "ente_fed_resp"]

#df_sem_headers.show()
df = df_sem_headers.toDF(*headers) # acrescenta os headers no df original

### [code]
# finalmente, carrega os dados em uma tabela Spark
df.write.option("encoding", "iso-8859-1").option("overwriteSchema", "true").mode("overwrite").saveAsTable("empresas")

### [code]
%sql
select * from empresas where cnpj_raiz = 2209756

### [code]
%sql
-- verificando que inseriu corretamente, fazer select simples
select porte, count(distinct cnpj_raiz) from empresas group by porte

### [code]
# apagar dfs sem uso, liberar memória
del df
del df_sem_headers
gc.collect()

--- out:
Out[9]: 477

### [markdown]
### 1.2 - Dados de Estabelecimentos (CNPJ full, 11 dígitos)

### [markdown]
#### Carga

### [code]

# path S3 no Tigris onde estão os dados de Empresas
s3_dir = "s3a://pos-pucrio-dados/mvp_sprint_eng_dados/estab/"

# os arquivos da RFB estão vindo sem header - ler primeiro sem headers e acrescentar na mão depois
# OBS: infelizmente, em alguns dos registros há um caracter '\' no nome da empresa escapando indevidamente as aspas duplas ('"') do fim da razao social... mudar caracter de escape para '"'
df_sem_headers = spark.read.option("delimiter", ";").option("escape", "\"").option("multiLine", True).option("encoding", "iso-8859-1").csv(s3_dir, header=False, inferSchema=True) 

# headers segundo doc (https://www.gov.br/receitafederal/dados/cnpj-metadados.pdf)
headers = ["cnpj_raiz", "cnpj_ordem", "cnpj_dv", "ind_matriz_filial", "nome_fantasia", "situacao", "dat_situacao", "mot_situacao", "cidade_exterior", "pais", "dat_inicio_atividade", "CNAE_principal", "CNAEs_secundarios", "tip_logradouro", "logradouro", "num_logradouro", "compl_logradouro", "bairro", "CEP", "UF", "municipio", "ddd1", "tel1", "ddd2", "tel2", "ddd_fax", "fax", "email", "sit_especial", "dat_sit_especial"]

#df_sem_headers.show()
df = df_sem_headers.toDF(*headers) # acrescenta os headers no df original

### [code]
# finalmente, carrega os dados em uma tabela Spark
df.write.option("encoding", "iso-8859-1").option("overwriteSchema", "true").mode("overwrite").saveAsTable("estabelecimentos")

### [code]
%sql
select * from estabelecimentos where cnpj_raiz = "28645283"

### [code]
%sql
-- verificando que inseriu corretamente, fazer select simples
select CNAE_principal, count(concat(cnpj_raiz, cnpj_ordem, cnpj_dv) ) from estabelecimentos group by CNAE_principal

### [code]
# apagar dfs sem uso, liberar memória
del df
del df_sem_headers
gc.collect()

--- out:
Out[14]: 485

### [markdown]
### 1.3 - Dados de CNAEs

### [markdown]
#### Carga

### [code]

# path S3 no Tigris onde estão os dados de Empresas
s3_dir = "s3a://pos-pucrio-dados/mvp_sprint_eng_dados/cnae/"

# os arquivos da RFB estão vindo sem header
# ler primeiro sem headers e acrescentar na mão depois
df_sem_headers = spark.read.option("delimiter", ";").option("encoding", "iso-8859-1").csv(s3_dir, header=False, inferSchema=True) 

# headers segundo doc (https://www.gov.br/receitafederal/dados/cnpj-metadados.pdf)
headers = ["codigo", "descricao"]

#df_sem_headers.show()
df = df_sem_headers.toDF(*headers) # acrescenta os headers no df original

### [code]
# finalmente, carrega os dados em uma tabela Spark
df.write.option("encoding", "iso-8859-1").option("overwriteSchema", "true").mode("overwrite").saveAsTable("cnae")

### [code]
%sql
-- verificando que inseriu corretamente, fazer select simples
select * from cnae

### [markdown]
### 1.4 - Dados de Municípios

### [markdown]
#### Carga

### [code]

# path S3 no Tigris onde estão os dados de Empresas
s3_dir = "s3a://pos-pucrio-dados/mvp_sprint_eng_dados/mun/"

# os arquivos da RFB estão vindo sem header
# ler primeiro sem headers e acrescentar na mão depois
df_sem_headers = spark.read.option("delimiter", ";").option("encoding", "iso-8859-1").csv(s3_dir, header=False, inferSchema=True) 

# headers segundo doc (https://www.gov.br/receitafederal/dados/cnpj-metadados.pdf)
headers = ["codigo", "descricao"]

#df_sem_headers.show()
df = df_sem_headers.toDF(*headers) # acrescenta os headers no df original

### [code]
# finalmente, carrega os dados em uma tabela Spark
df.write.option("encoding", "iso-8859-1").option("overwriteSchema", "true").mode("overwrite").saveAsTable("municipio")

### [code]
%sql
-- verificando que inseriu corretamente, fazer select simples
select * from municipio

### [markdown]
### 1.5 - Dados de Motivo de Situação


### [markdown]
#### Carga

### [code]

# path S3 no Tigris onde estão os dados de Empresas
s3_dir = "s3a://pos-pucrio-dados/mvp_sprint_eng_dados/mot/"

# os arquivos da RFB estão vindo sem header
# ler primeiro sem headers e acrescentar na mão depois
df_sem_headers = spark.read.option("delimiter", ";").option("encoding", "iso-8859-1").csv(s3_dir, header=False, inferSchema=True) 

# headers segundo doc (https://www.gov.br/receitafederal/dados/cnpj-metadados.pdf)
headers = ["codigo", "descricao"]

#df_sem_headers.show()
df = df_sem_headers.toDF(*headers) # acrescenta os headers no df original

### [code]
# finalmente, carrega os dados em uma tabela Spark
df.write.option("encoding", "iso-8859-1").option("overwriteSchema", "true").mode("overwrite").saveAsTable("motivo_situacao")

### [code]
%sql
-- verificando que inseriu corretamente, fazer select simples
select * from motivo_situacao

### [markdown]
### 1.6 - Dados de Natureza Jurídica


### [markdown]
#### Carga

### [code]

# path S3 no Tigris onde estão os dados de Empresas
s3_dir = "s3a://pos-pucrio-dados/mvp_sprint_eng_dados/nat/"

# os arquivos da RFB estão vindo sem header
# ler primeiro sem headers e acrescentar na mão depois
df_sem_headers = spark.read.option("delimiter", ";").option("encoding", "iso-8859-1").csv(s3_dir, header=False, inferSchema=True) 

# headers segundo doc (https://www.gov.br/receitafederal/dados/cnpj-metadados.pdf)
headers = ["codigo", "descricao"]

#df_sem_headers.show()
df = df_sem_headers.toDF(*headers) # acrescenta os headers no df original

### [code]
# finalmente, carrega os dados em uma tabela Spark
df.write.option("encoding", "iso-8859-1").option("overwriteSchema", "true").mode("overwrite").saveAsTable("natureza_juridica")

### [code]
%sql
-- verificando que inseriu corretamente, fazer select simples
select * from natureza_juridica

### [markdown]
## 2 - Base dos Dados

### [markdown]
### 2.1 - Municípios, Regiões Imediatas, Regiões Intermediárias (Base dos Dados / IBGE)

Para fazer análises regionalizadas, não restritas exclusivamente a um município alvo mas considerando também os municípios no entorno (região imediata e região intermediária, antigas micro e mesorregiões), podemos utilizar a base de DTB (Divisão Territorial) do IBGE. Entretanto, o código de município da RFB não é o mesmo do IBGE, que faria com que tivéssemos que fazer algum match por nome de município. Para contornar esta questão, vamos utilizar uma base já tratada, a base de Municípios na Base dos Dados (https://basedosdados.org/), site que agrega e trata dados de várias fontes brasileiras e traz o id da RFB e o do IBGE numa mesma tabela de municípios. 

Os dados da base de Municípios estão disponíveis como arquivos csv.gz no endereço abaixo:

https://basedosdados.org/dataset/33b49786-fb5f-496f-bb7c-9811c985af8e?table=dffb65ac-9df9-4151-94bf-88c45bfcb056

Os dados mais recentes disponíveis são os de set/2023.

### [markdown]

#### Coleta / Extração

Apesar do pequeno tamanho, seguiremos o mesmo estilo utilizado para a base do QSA, i.e. baixar o zip localmente, processá-lo e subí-lo para um bucket S3 do Tigris, de onde o Spark lerá os dados e salvará numa Spark Table.

### [markdown]
#### Carga


### [code]

# path S3 no Tigris onde estão os dados de Empresas
s3_dir = "s3a://pos-pucrio-dados/mvp_sprint_eng_dados/mun-bd/"

# os arquivos da BD já vem com headers, então só ler
df = spark.read.option("delimiter", ",").csv(s3_dir, header=True, inferSchema=True) 

### [code]
# finalmente, carrega os dados em uma tabela Spark
df.write.mode("overwrite").saveAsTable("municipio_bd")

### [code]
%sql
-- verificando que inseriu corretamente, fazer select simples
select * from municipio_bd

### [markdown]
### 2.2 - CNAEs (Base dos Dados / IBGE)

A classificação de CNAEs em si é organizada de forma hierárquica, mas a base apresentada pela RFB não traz os níveis intermediários de Divisão, Grupo ou Classe, que seriam úteis para uma análise ou busca em nível mais agregado. Para suprir esse gap, vamos utilizar uma base já tratada, a base de CNAEs na Base dos Dados (https://basedosdados.org/), site que agrega e trata dados de várias fontes brasileiras e traz esta base de CNAEs do IBGE com estas dimensões de níveis agregados já computadas para cada CNAE. 

Os dados da base de CNAEs estão disponíveis como arquivos csv.gz no endereço abaixo:

https://basedosdados.org/dataset/33b49786-fb5f-496f-bb7c-9811c985af8e?table=8a02c4e5-1718-41e7-8891-d0fa09265d58


Os dados mais recentes disponíveis são os de ago/2024.


### [markdown]

#### Coleta / Extração

Apesar do pequeno tamanho, seguiremos o mesmo estilo utilizado para a base do QSA, i.e. baixar o zip localmente, processá-lo e subí-lo para um bucket S3 do Tigris, de onde o Spark lerá os dados e salvará numa Spark Table.

### [markdown]
#### Carga


### [code]

# path S3 no Tigris onde estão os dados de Empresas
s3_dir = "s3a://pos-pucrio-dados/mvp_sprint_eng_dados/cnae-bd/"

# os arquivos da BD já vem com headers, então só ler
# apenas um cuidado: alguns registros estão espalhados por mais de 1 linha de cada vez - habilitar opção de multiline
df = spark.read.option("delimiter", ",").option("multiLine", "true").csv(s3_dir, header=True, inferSchema=True) 

### [code]
# finalmente, carrega os dados em uma tabela Spark
df.write.mode("overwrite").saveAsTable("cnae_bd")

### [code]
%sql
-- verificando que inseriu corretamente, fazer select simples
select * from cnae_bd
