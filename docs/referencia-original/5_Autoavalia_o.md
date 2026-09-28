### [markdown]
# Autoavaliação sobre o trabalho realizado


### [markdown]

Considero que o trabalho foi muito gratificante, útil e valioso. Foi tecnicamente difícil/desafiador, mas considero que consegui atingir bem os objetivos que me propus, tendo aprendido muito:
  - me "desenferrujei" em Python e SQL e trabalhei e aprofundei os conhecimentos de Spark, ETL
  - conheci em mais detalhes o Databricks, especialmente o Databricks Community Edition, que se mostrou uma ferramenta muito valiosa para análise de dados e prática de engenharia de dados, com custo praticamente zero
  - aprendi a trabalhar com ferramentas de armazenamento na cloud, como o serviço S3-like Tigris

### [markdown]

Escolhi trabalhar com a base pública de CNPJs da Receita Federal (RFB), porque são dados que já conhecia e acho muito interessantes e que habilitam muitas análises importantes para os negócios, como esta que propus fazer de pesquisa/inteligência de mercado. Entretanto, esta escolha trouxe alguns desafios:
  - as bases são realmente muito grandes (cerca de 20 GB no total, mais de 60 milhões de registros).. com isso, baixar as bases diretamente no Databricks Community Edition para carga posterior no Spark se tornou inviável, porque consumia muito tempo e processamento e o cluster do Community Edition era reiniciado depois de 1 h de processamento direto..
  - a solução para este problema foi pré-processar (baixar, dezipar) as bases da RFB (e outras depois) e subir os dados num serviço S3-like (Tigris) - isso se mostrou essencial para reduzir o tempo de processamento no Databricks, ficando neste último apenas a tarefa de baixar os dados do S3-like e processar
  - ainda assim, o pipeline era longo e tedioso de se rodar, não cabendo em um único notebook ipynb. A solução foi dividir o processamento em diversas etapas, cada uma com seu notebook próprio
  - a próxima dificuldade foi conseguir armazenar os dados de forma perene. O Databricks Community Edition, embora uma excelente ferramenta e gratuita, não aloca clusters de forma efêmera para seus usuários - quando o cluster é enfim desligado (por inatividade ou fim da sessão por ex ) tudo que foi salvo apenas no cluster se perde... Tive que aprender a armazenar dados no dbfs (file system distribuído da Databricks) e nas tabelas Spark para uso entre sessões
  - na sequência, descobri que infelizmente as tabelas Spark - mais precisamente os metadados que as descrevem na Hive Metastore; os dados em si permanecem armazenados no dbfs num caminho específico - são perdidos quando o cluster é desligado. Como recarregar os dados na tabela Spark era um processo muito demorado e tedioso, tive de buscar uma solução para tentar recriar as tabelas Spark a partir dos arquivos delta armazenados no dbfs. Com auxílio de algumas pesquisas no Google/Gemini, consegui chegar a um script funcional, que acompanha este trabalho
  - durante o tratamento da carga propriamente dita, encontrei ainda alguns problemas de encoding e uso de caracteres especiais nos arquivos da RFB, mas depois de algumas análises (usando ferramenta Pig e scripts python auxiliares) e tentativas de carga, encontrei os problemas e consegui corrigí-los
  - por fim, encontrei algumas pequenas dificuldades no uso do Spark propriamente dito, mas resolvidos com pesquisas e troca de conhecimentos com os colegas e professores
  
  Uma última dificuldade, boba, mas que me atrapalhou um bocado: como as bases de dados são muito grandes, em alguns casos o notebook ficou muito grande com os resultados e ao exportar o Databricks dava erro porque o arquivo ficava muito grande. A solução foi dividir mais uma vez em vários notebooks.

### [markdown]
# Trabalhos Futuros

O trabalho apresentado é um MVP, não se encerra em si mesmo. Daqui, há diversas possibilidades de melhoria/expansão:

- Pode-se expandir a base humanizada agregando-se outras infos de bases públicas, por ex incluindo-se dados de demografia dos municípios, para uma análise de público alvo das empresas
- Um outro ponto de melhoria, é expandir os textos de CNAEs secundários e permitir buscas melhores usando essas infos multivaloradas (atualmente só trazemos os códigos separados por "," , como a RFB faz)
- Pode-se também investir em um modelo estrela/snowflake para uso self-service facilitado por um usuário final, com dashboards e visualizações
- Por fim, é possível também trabalhar mais na automação do processo de carga, por ex com uso de bibliotecas como dbt ou airflow, chegando-se a uma solução que possa ser agendada e carregar de tempos em tempos os dados mais atualizados da RFB


### [markdown]

# Agradecimentos finais


### [markdown]

  Agradeço a Deus em primeiro lugar, pela Sua Graça e pelo dom da Vida, por tudo. 
  
  Em seguida agradeço:
  - à PUC Rio e aos professores e instrutores, pela oportunidade de fazer esta pós, que tanto está me acrescentando
  - à minha família por todo o apoio e compreensão nestes dias de dedicação
  - e aos colegas de turma, em especial ao James Reis, Pedro Lira e Igor Venancio, com quem mais troquei ideias sobre o trabalho, que me ajudaram no desenvolvimento do MVP
