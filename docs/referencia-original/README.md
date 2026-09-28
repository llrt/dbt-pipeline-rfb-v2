# Referência: projeto original (MVP Databricks/Spark)

Extração em texto (células markdown + código + trechos curtos de saída) dos notebooks do projeto original
[llrt/pos_dados_puc_rio-mvp_sprint_eng_dados](https://github.com/llrt/pos_dados_puc_rio-mvp_sprint_eng_dados)
(commit `2ea8bd2`, 2025-03-29, licença MIT, © 2025 Leandro Loriato).

Estes arquivos são a **fonte de verdade do escopo original** para o port. Toda regra marcada como
`escopo: original` no projeto dbt deve ser rastreável a uma célula destes arquivos.

| Arquivo | Notebook original | Conteúdo relevante para o port |
|---|---|---|
| `0_Defini_es_Iniciais.md` | 0 - Definições Iniciais | Problema, perguntas de negócio, bases |
| `1_Coleta_e_Carga_de_Dados.md` | 1 - Coleta e Carga | Leitura CSV RFB (latin-1, `;`, escape `"`, multiline), headers, carga BD |
| `2.1.1_*.md`, `2.1.2_*.md` | 2.1.x - Qualidade (domínios RFB/BD) | Checks de unicidade/completude/integridade dos domínios |
| `2.2_*.md` | 2.2 - Qualidade Empresas | Checks de empresas (unicidade, natureza, porte) |
| `2.3_*.md` | 2.3 - Qualidade Estabelecimentos | Checks de estabelecimentos (CNAE, município, situação) |
| `3_Modelo_de_Dados.md` | 3 - Modelo de Dados | SQL e catálogo de `bh_empresas` e `agg_empresas` |
| `4_An_lise_de_Dados.md` | 4 - Análise | Estudo de caso: tintas em Fundão/ES |
| `5_Autoavalia_o.md` | 5 - Autoavaliação | Dificuldades e trabalhos futuros (fonte de várias adições) |
| `99_Reconstruir_tabelas_Spark.md` | Reconstruir tabelas Spark | Workaround do Hive Metastore (obsoleto no port) |
