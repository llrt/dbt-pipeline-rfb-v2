### [markdown]
## Reconstruir tabelas Spark

Infelizmente no Databricks Community Edition, apesar de os dados em si das tabelas serem persistidos no dbfs entre uma seção e outra, a Hive Metastore é perdida quando o Cluster associado é parado. Uma solução é tentar reconstruir as definições das tabelas na Hive Metastore a partir dos dados do dbfs. Este script tenta fazer isso.

### [code]
from pyspark.sql import SparkSession
import os

spark = SparkSession.builder.appName("RecreateMetastore").getOrCreate()

warehouse_path = "/user/hive/warehouse/" # dir dbfs onde ficam os dados das bases

for item in dbutils.fs.ls(warehouse_path): # para cada dir (i.e. para cada base) no dbfs na pasta onde ficam os dados
    if item.isDir():
        table_path = item.path # path
        table_name = os.path.basename(os.path.normpath(table_path)) # nome do dir, i.e. nome da base

        # Tentativa de inferir schema (assumindo bases armazenadas em formato delta-table)
        try:
            df = spark.read.format("delta").load(table_path)
            schema = df.schema

            # gerando CREATE TABLE
            create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS {table_name}
                ({", ".join([f"{field.name} {field.dataType.simpleString()}" for field in schema])})
                USING delta
                LOCATION '{table_path}'
            """

            spark.sql(create_table_sql)
            print(f"Tabela '{table_name}' recriada!")

        except Exception as e:
            print(f"Falha ao recriar tabela em '{table_path}': {e}")


--- out:
Tabela 'agg_empresas' recriada!
Tabela 'bh_empresas' recriada!
Tabela 'cnae' recriada!
Tabela 'cnae_bd' recriada!
Tabela 'empresas' recriada!
Tabela 'estabelecimentos' recriada!
Tabela 'motivo_situacao' recriada!
Tabela 'municipio' recriada!
Tabela 'municipio_bd' recriada!
Tabela 'natureza_juridica' recriada!


### [code]
%sql
select count(cnpj_raiz) from empresas
