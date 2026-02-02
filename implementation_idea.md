# Backend Analítico Descritivo: Projeto Técnico para Análise Inteligente de Chamados

Esta é uma abordagem sólida para a construção de um backend de IA focado em análise de tickets corporativos. Ao remover a responsabilidade de "decisor" da IA e focá-la em **padronização e agrupamento**, elimina-se os maiores riscos de alucinação e viés, transformando a IA em uma ferramenta de *Data Enrichment* (Enriquecimento de Dados).

Abaixo está o projeto técnico detalhado, integrando a arquitetura de processamento com a estratégia de agregação de dados, adaptado para o modelo de **Processamento Interno em Lote (Batch)**.

---

## 1. Arquitetura da Solução: O Pipeline "Cluster & Label" (Batch)

Não utilizaremos uma arquitetura complexa de múltiplos agentes ou interação em tempo real com o usuário para a geração da análise. A arquitetura definida é um **Pipeline Linear de Processamento em Lote (Batch Processing)**, executado internamente pela equipe técnica (ex: a cada 6 meses ou mensalmente). A IA Generativa entra apenas no final para "dar nome aos bois".

### Fluxo do Pipeline
1.  **Ingestão em Lote (Batch):** SQL Query de janela fixa (ex: últimos 6 meses) executada internamente via script.
2.  **Vetorização (Embeddings):** Transformação de texto em matemática.
3.  **Redução Dimensional & Clustering:** Matemática pura para encontrar os grupos (sem IA generativa aqui).
4.  **Agregação Determinística (Python/SQL):** Cálculo exato de métricas (contagem de serviços, solicitantes, etc.).
5.  **Agente Sintetizador (LLM):** Lê uma amostra do grupo e gera o título/descrição do problema.
6.  **Persistência de Resultados:** Salva um arquivo JSON consolidado (artefato estático) para consumo rápido pelo Dashboard.

---

## 2. O Conceito Central: Quem faz o quê?

Para ter sucesso e obter dados conectados (Ex: Cluster 1 possui 3 chamados do Serviço A e 5 do Serviço B), é necessário separar as responsabilidades corretamente.

Se você pedir para a IA (LLM) contar quantos "Solicitante A" existem em um grupo de 500 chamados, ela vai errar (alucinar números) e vai custar caro. Se esperar que o Vector DB faça isso, ele não fará, pois guarda apenas posições matemáticas.

A melhor abordagem é o padrão **"Code-Interpreter Pattern"** (ou Agregação via Código).

### A Divisão de Papéis:

#### 1. O Papel do Clustering (Matemática)
Ele apenas diz: *"Os IDs de chamado 10, 25, 30... pertencem ao Grupo 42".*

#### 2. O Papel do Backend (Python/Pandas/SQL) - A MÁGICA
É o seu código Python que vai pegar a lista de IDs do Grupo 42, cruzar com o banco de dados original e fazer a conta.
* **Precisão:** O Python nunca erra uma conta de `count()`. A IA erra.
* **Escala:** O Python agrupa 10.000 linhas em milissegundos.
* **Economia:** Você não gasta tokens para ler nomes de solicitantes.

#### 3. O Papel da IA (LLM - Agente Sintetizador)
Você envia para ela apenas o **texto** de 5 a 10 exemplos desse grupo.
* *Prompt:* "Leia estes exemplos e dê um título e descrição técnica."
* *Retorno:* Título "Falha de Login no Protheus", Descrição "Erro de credenciais inválidas recorrente."

---

## 3. Detalhamento Técnico das Etapas

### A. Embeddings (O Motor Semântico)
É aqui que resolvemos o problema de "textos não padronizados".
* **Estratégia:** Concatenar `Sistema` + `Serviço` + `Título` + `Descrição` em um único bloco de texto.
* **Modelo Recomendado:**
    * Opção Cloud: OpenAI `text-embedding-3-small` (Rápido, barato e excelente para português).
    * Opção On-Premise/Open Source: `multilingual-e5-large` (Roda localmente, sem custo por token).
* **Função:** Transforma "Erro ao emitir NFe" e "Falha de comunicação com SEFAZ" em vetores numéricos muito próximos.

### B. Clustering (A Mágica da Recorrência)
Não use LLM para agrupar 5.000 chamados. Use algoritmos matemáticos não supervisionados.
* **Algoritmo Recomendado:** **HDBSCAN** (Hierarchical Density-Based Spatial Clustering of Applications with Noise).
* **Por que HDBSCAN?**
    * Não precisa dizer quantos grupos existem (diferente do K-Means).
    * Entende o conceito de "Ruído" (chamados que não se agrupam), evitando *Overclustering*.
    * Funciona por densidade, ideal para encontrar problemas que "explodiram" de repente.

### C. Agente Sintetizador (O Único LLM Necessário)
Uma vez identificado o cluster, acionamos a IA Generativa.
* **Papel:** Ler 5 a 10 chamados aleatórios dentro do cluster e gerar um rótulo explicativo.
* **Técnica:** Map-Reduce simplificado (apenas Summarization).

**Estratégia de Prompt (System Message):**
> "Você é um Analista de Padrões de TI Sênior. Sua função é ler um conjunto de descrições de chamados que foram agrupados matematicamente por similaridade e extrair o problema raiz comum.
>
> **Regras Rígidas:**
> 1. NÃO julgue a prioridade ou gravidade.
> 2. NÃO sugira soluções.
> 3. Identifique o sistema e o erro técnico comum.
> 4. Se os chamados forem muito genéricos (ex: 'erro', 'ajuda'), rotule como 'Inconclusivo/Genérico'.
> 5. Crie um título curto e uma descrição técnica unificada.
>
> **Entrada:** Lista de 5 chamados do Sistema Logix.
> **Saída esperada (JSON):**
> {
>   'problema_identificado': 'Falha de conexão ODBC no módulo Contábil',
>   'sintomas_comuns': ['Travamento na tela de lançamentos', 'Erro de timeout'],
>   'contexto_sistema': 'Logix'
> }"

---

## 4. Implementação da Agregação (Python)

Como implementar a fusão dos dados estatísticos com a análise semântica no Backend.

### Lógica de Código (Python/Pandas):

```python
# 1. O Clustering (HDBSCAN) devolveu os labels
df_chamados['cluster_id'] = clusterer.labels_

# 2. Agrupamos os dados matematicamente (SEM IA AQUI)
resumo_clusters = []

for cluster_id in df_chamados['cluster_id'].unique():
    if cluster_id == -1: continue # Ignora ruído

    # Filtra apenas chamados deste grupo
    grupo = df_chamados[df_chamados['cluster_id'] == cluster_id]
    
    # Cálculos Estatísticos (Rápido e Preciso)
    contagem_servicos = grupo['servico'].value_counts().to_dict()
    contagem_solicitantes = grupo['solicitante'].value_counts().to_dict()
    
    # 3. Aqui chamamos a IA apenas para dar o NOME
    # Pegamos 5 textos aleatórios do grupo para a IA ler
    amostra_textos = grupo['descricao_concatenada'].sample(5).tolist()
    analise_ia = agente_sintetizador.analisar(amostra_textos) # Chama OpenAI/LLM
    
    # 4. Montamos o objeto final
    resumo_clusters.append({
        "cluster_id": int(cluster_id),
        "titulo": analise_ia['titulo'],
        "servicos": contagem_servicos,       # O dado conectado
        "solicitantes": contagem_solicitantes # O dado conectado
    })

return resumo_clusters
```

### Exemplo do JSON Final (A Fusão):
Este é o objeto que o seu backend entrega para o dashboard, juntando o cálculo exato (Passo A) com o enriquecimento semântico (Passo B).

```json
{
  "id": 42,
  "titulo": "Falha no Spooler de Impressão", // Veio da IA
  "descricao": "O serviço de spooler está travando devido a drivers desatualizados...", // Veio da IA
  "metricas": { // Veio do Python (Cálculo Exato)
      "total": 15,
      "top_servicos": [
          {"nome": "Impressão", "qtd": 10},
          {"nome": "Rede", "qtd": 5}
      ],
      "top_solicitantes": [
          {"nome": "João Silva", "qtd": 8},
          {"nome": "Maria Souza", "qtd": 7}
      ]
  }
}
```

---

## 5. Estrutura de Dados para Persistência e Filtros (Modelo JSON)

Para entregar dashboards (Solicitante x Problema) sem a complexidade de banco de dados em tempo real, o script gera um **Arquivo JSON Rico (Dataset)** que alimenta o frontend:

1.  **Arquivo `analise_logix.json`**:
    * Contém os clusters identificados (Problemas).
    * Contém a lista de chamados vinculados a cada cluster.
    * Serve como base de dados estática ("Snapshot") do período analisado.

Com isso, o Frontend carrega esse JSON e faz filtros (Data, Solicitante) usando JavaScript localmente, garantindo performance instantânea.

---

## 6. Pontos de Atenção e Boas Práticas

### Armadilhas Comuns
* **Alucinação em Clusters:** A IA Generativa não agrupa. Quem agrupa é o embedding + HDBSCAN. A IA apenas lê o grupo já formado.
* **Overclustering (Fragmentação):** Ajuste o parâmetro `min_cluster_size` do HDBSCAN. Se estiver muito baixo (ex: 2), qualquer par vira problema. Recomenda-se no mínimo 5 ou 10 tickets.
* **Underclustering:** Remova assinaturas de e-mail e logs gigantes antes de criar o embedding para evitar poluição semântica.
* **Perda de Rastreabilidade:** Nunca perca o ID do chamado original. O processo deve sempre retornar quais IDs compõem o cluster.

### Escala e Performance
* **Cache de Embeddings (Hashing):** Gere um hash (SHA256) do texto antes de enviar para a API (ou use o Qdrant ID). Se já existir no banco, reutilize o vetor. Economiza muito dinheiro em reprocessamentos futuros.
* **Auditoria:** Guarde o JSON de resposta da IA para cada cluster para auditoria humana futura.

## Resumo
Você não precisa de RAG clássico aqui. Você está construindo um **Pipeline de ETL Cognitivo**. O segredo do sucesso é: **Matemática para agrupar, IA para descrever, SQL/Código para contar.** Certifique-se de que a conexão e contagem sejam feitas pela camada determinística (Código) e apenas a interpretação pela camada probabilística (IA).

# Arquitetura de Solução: Backend de Análise de Chamados (Batch Interno)

Este documento descreve a arquitetura técnica para o sistema de análise inteligente de tickets. O sistema opera sob o modelo **"Processamento em Lote Interno"**: ele não processa em tempo real via solicitação do usuário final, mas sim através de execução programada (Script) pela equipe técnica, gerando visualizações estáticas de períodos fechados (ex: "Semestre Passado").

---

## 1. Visão Geral da Arquitetura

A solução é dividida em três camadas principais: **Script de Processamento (ETL & IA)**, **API de Leitura** e **Frontend (Dashboard)**.

### Diagrama Lógico de Fluxo

1.  **Execução Manual/Agendada:** TI roda o script `run_pipeline.py`.
2.  **ETL & AI Core:** Script busca dados, vetoriza, agrupa e rotula.
3.  **Geração de Artefato:** Script salva `analise_sistema_data.json`.
4.  **API Gateway:** Expõe endpoint de leitura (`GET /analise`).
5.  **Dashboard:** Consome o JSON consolidado para visualização instantânea.

---

## 2. Componentes da Arquitetura

### A. Frontend (Dashboard Interativo)
* **Tecnologia:** React, Vue ou Angular + Biblioteca de Gráficos (ECharts/Recharts).
* **Tela de Visualização:**
    * *Inputs:* Filtros locais (JavaScript) aplicados sobre os dados do JSON carregado.
    * *Sem Loading:* Como o dado já está processado, a abertura é imediata.
* **Tela de Resultados:**
    * **Visão Geral:** Cards ordenados por volume ("Erro X - 450 casos").
    * **Detalhe:** Ao clicar no card, exibe a descrição da IA, gráfico de evolução temporal e tabelas de "Top Solicitantes" e "Serviços Afetados".

### B. Backend (Python - Scripts + FastAPI Leitura)
* **Script Runner:** Arquivo Python executado via terminal/cron que orquestra todo o processamento pesado.
* **API (FastAPI):** Endpoint REST super leve apenas para servir os arquivos JSON gerados.
* **Módulo Core (AI Pipeline):**
    1.  **Data Fetcher:** SQL Query no banco legado (Janela de 6 meses).
    2.  **Vectorizer:** Converte texto em vetores (OpenAI Ada-003 ou SentenceTransformers).
    3.  **Cluster Engine:** Algoritmo **HDBSCAN** para agrupar por densidade.
    4.  **Labeler Agent:** Chama o LLM *apenas* para dar nome aos grupos formados (Amostragem de 5 itens).
    5.  **Aggregator:** Código Python (Pandas) que consolida as estatísticas.

### C. Camada de Dados (Híbrida)
* **Banco Legado (Leitura):** SQL Server/Oracle/Postgres onde residem os chamados.
* **Vector Store (Cache):** **Qdrant** (Docker Local).
    * *Função:* Cache de embeddings. Garante que se rodarmos o script novamente, não pagamos pela vetorização dos mesmos chamados.
* **File System (Saída):** Pasta `data_output/` contendo os JSONs de resultado.

---

## 3. O Fluxo de Dados "Passo a Passo" (Execução do Script)

Exemplo de execução: TI roda `python run_pipeline.py --sistema Logix --dias 180`.

### Passo 1: Extração e Limpeza (Python/Pandas)
* **Ação:** Script executa SQL filtrado por data e sistema.
* **Processamento:** Remove assinaturas de e-mail, tags HTML e concatena `Título + Descrição`.
* **Saída:** DataFrame com ID e Texto Limpo.

### Passo 2: Vetorização (Embeddings)
* **Ação:** Sistema verifica cache no Qdrant.
    * *Cache Hit:* Recupera vetor do banco local (Gratuito).
    * *Cache Miss:* Chama API de Embedding e salva (Pago).
* **Saída:** Matriz multidimensional de vetores numéricos.

### Passo 3: Clustering (HDBSCAN)
* **Ação:** O algoritmo analisa a densidade geométrica dos vetores.
* **Lógica:** "Estes 500 pontos estão densos? Sim -> **Cluster 1**". "Estes pontos estão espalhados? Sim -> **Ruído**".
* **Saída:** IDs de chamados associados a IDs de Clusters.

### Passo 4: Rotulagem (Agente IA)
* **Ação:** Sistema seleciona 5 a 10 exemplos aleatórios do "Cluster 1".
* **Prompt:** "Analise estes chamados e defina um Título Técnico curto e uma Descrição do problema raiz."
* **Saída:** Metadados semânticos do problema.

### Passo 5: Consolidação (Code Interpreter Pattern)
* **Ação:** O Python cruza os IDs do Cluster 1 com o banco original.
* **Cálculo:** `GROUP BY solicitante`, `GROUP BY servico`, `COUNT(*)`.
* **Saída:** JSON final estruturado salvo em disco.

---

## 4. Modelo de Dados de Saída (JSON)

Este é o objeto entregue ao Frontend para renderização dos gráficos.

```json
{
  "analise_id": "job_uuid_12345",
  "status": "completed",
  "parametros": {
    "periodo": "01/06/2023 - 31/12/2023",
    "sistema": "Logix"
  },
  "resumo_global": {
    "total_chamados": 5000,
    "total_agrupados": 4200,
    "total_ruido": 800
  },
  "problemas_identificados": [
    {
      "id_cluster": 101,
      "titulo_ia": "Lentidão na Consulta de Estoque Logix",
      "descricao_ia": "Usuários relatam timeout intermitente ao filtrar produtos por armazém.",
      "metricas": {
        "ocorrencias": 150,
        "percentual_do_total": "3.5%",
        "tendencia": "Crescente" 
      },
      "detalhes": {
        "servicos_afetados": [
          {"nome": "Módulo Estoque", "qtd": 140},
          {"nome": "API Integração", "qtd": 10}
        ],
        "top_solicitantes": [
          {"nome": "Filial SP", "qtd": 50},
          {"nome": "Filial MG", "qtd": 30}
        ],
        "timeline": [
          {"mes": "2023-06", "qtd": 10},
          {"mes": "2023-07", "qtd": 15},
          {"mes": "2023-08", "qtd": 50}
        ]
      }
    }
  ]
}
```

---

## 5. Estratégia de Qualidade e Validação

Para garantir que os clusters e a análise sejam confiáveis:

1.  **Vetorização Robusta:** O uso de Embeddings transforma sinônimos ("Senha incorreta" e "Credencial inválida") em vetores próximos matematicamente.
2.  **HDBSCAN vs Ruído:** O algoritmo não força agrupamentos. Se um chamado é único, ele é classificado como ruído (-1), evitando alucinação de padrões.
3.  **Validação Matemática:** O backend pode calcular o *Silhouette Score* dos clusters. Clusters com score baixo (muito dispersos) podem ser descartados ou marcados para revisão.
4.  **Auditoria:** O JSON gerado deve ser salvo. Isso permite que um humano verifique se o título "Falha de Rede" realmente corresponde aos textos dos chamados daquele grupo.

## 6. Boas Práticas de Implementação

* **Não use IA para contar:** Sempre use o código (Python/SQL) para gerar métricas de volume, datas e solicitantes. A IA serve apenas para *interpretar* o texto e gerar o rótulo do problema.
* **Cache é Dinheiro:** A implementação do Vector Store (Qdrant) é crucial para viabilidade econômica, permitindo rodar o script periodicamente sem recustear todo o histórico.
* **Execução Programada:** O processamento ocorre em background via script, sem bloquear o usuário final, gerando arquivos estáticos para consumo imediato.