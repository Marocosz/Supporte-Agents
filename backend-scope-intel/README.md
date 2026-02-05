# Scope Intelligence - Backend & Pipeline

O **Scope Intelligence** é a inteligência central do sistema de análise de chamados. Este backend é responsável por processar grandes volumes de dados de suporte (chamados), identificar padrões ocultos através de algoritmos de clustering avançados e utilizar Inteligência Artificial Generativa (LLM) para explicar o "porquê" desses problemas estarem ocorrendo.

Diferente de sistemas de BI tradicionais que mostram "o que" aconteceu, este sistema foca no "motivo", agrupando incidentes semanticamente similares e gerando insights qualitativos de forma automatizada.

## ⚙️ Tecnologias Utilizadas

O stack foi selecionado para lidar com processamento intensivo de dados (ETL), Inteligência Artificial (Vetores + LLM) e alta disponibilidade via API.

- **[Python 3.10+](https://www.python.org/)**: Linguagem base para todo o processamento e API.
- **[FastAPI](https://fastapi.tiangolo.com/)**: Framework moderno e de alta performance para construção da API REST.
- **[Qdrant](https://qdrant.tech/)**: Banco de dados vetorial (Vector Database) utilizado para armazenar e buscar embeddings semânticos dos chamados.
- **[OpenAI API](https://openai.com/)**: Utilizada em duas frentes:
  - **Embeddings (text-embedding-3-small)**: Para converter textos de chamados em vetores numéricos.
  - **Chat Completion (GPT-4o)**: Para analisar clusters, gerar títulos, descrições e raciocínios técnicos.
- **[HDBSCAN](https://hdbscan.readthedocs.io/)**: Algoritmo de clustering baseado em densidade hierárquica, capaz de encontrar grupos de formatos variados e isolar ruídos (outliers).
- **[Scikit-Learn](https://scikit-learn.org/)**: Ferramentas auxiliares de ML (cálculo de distâncias, matrizes).
- **[SQLAlchemy](https://www.sqlalchemy.org/)**: ORM para comunicação com o banco de dados relacional (MySQL).
- **[ReportLab](https://www.reportlab.com/)**: Biblioteca para geração programática de relatórios em PDF.

## 📑 Tópicos

- [1 - Estrutura do Projeto](#1-estrutura-do-projeto)
- [2 - Funcionalidades Principais](#2-funcionalidades-principais)
- [3 - Arquitetura e Fluxo do Pipeline](#3-arquitetura-e-fluxo-do-pipeline)
- [4 - Instalação e Configuração](#4-instalação-e-configuração)
- [5 - Como Executar](#5-como-executar)
- [6 - Modelagem de Dados](#6-modelagem-de-dados)

## <a id="1-estrutura-do-projeto"></a>1 - Estrutura do Projeto 🏗️

A organização segue os princípios de separação de responsabilidades, dividindo o código entre a API (online) e os Scripts de Pipeline (batch/offline).

```
├── 📁 app/                     # Núcleo da aplicação
│   ├── 📁 api/                 # Definição de Rotas e Schemas (Pydantic/FastAPI)
│   ├── 📁 core/                # Configurações globais, Conexão DB e Vector Store
│   ├── 📁 models/              # Modelos de dados (se aplicável ao ORM)
│   └── 📁 services/            # Lógica de Negócio (O "Cérebro" do sistema)
│       ├── 🐍 cluster_engine.py # Lógica de Clustering (HDBSCAN + Agrupamento Hierárquico)
│       ├── 🐍 data_fetcher.py   # ETL: Extração de dados do MySQL
│       ├── 🐍 llm_agent.py      # Integração com OpenAI (Prompts e Chamadas)
│       ├── 🐍 vectorizer.py     # Geração e gerenciamento de embeddings
│       └── 🐍 aggregator.py     # Consolidação estatística de grupos
├── 📁 data_output/             # Armazenamento local dos JSONs gerados pelo pipeline
├── 📁 qdrant_data/             # Persistência de dados do container Qdrant
├── 📁 reports/                 # Saída dos relatórios PDF gerados
├── 📁 scripts/                 # Scripts de execução Batch (Offline)
│   ├── 🐍 run_pipeline.py      # Entrypoint principal da análise de dados
│   └── 🐍 generate_report.py   # Gerador de relatórios PDF a partir dos JSONs
├── 📄 .env                     # Variáveis de ambiente e segredos
├── 🐳 docker-compose.yml       # Orquestração do serviço Qdrant
├── 📄 ddl.sql                  # Schema do Banco de Dados Relacional
└── 📄 requirements.txt         # Dependências do Python
```

### 📦 Módulos Principais
- **app/services/cluster_engine.py**: Contém a lógica matemática complexa. Recebe vetores brutos e retorna rótulos (labels) de agrupamento, além de calcular a hierarquia (quais micro-clusters pertencem a quais macro-temas).
- **app/services/llm_agent.py**: Abstrai a "persona" do analista sênior. Contém funções assíncronas para enviar contextos de clusters para o GPT e receber análises estruturadas (JSON mode).
- **scripts/run_pipeline.py**: O orquestrador. Ele não contém lógica de negócio "pura", mas coordena a chamada sequencial de todos os serviços para transformar dados brutos no arquivo JSON final.

## <a id="2-funcionalidades-principais"></a>2 - Funcionalidades Principais 🚀

### 1. Pipeline de Inteligência (Batch)
O coração do sistema. Roda periodicamente (ou sob demanda) para varrer o banco de dados, vetorizar novos chamados e re-calcular os agrupamentos. O resultado é um arquivo `.json` rico, contendo toda a árvore de problemas detectados.

### 2. API REST (FastAPI)
Expõe os dados processados para o Frontend.
- **Endpoints de Leitura**: Permitem que a interface carregue o JSON mais recente e exiba os gráficos e cards.
- **Endpoints de Detalhe**: (Em desenvolvimento) Para drill-down de chamados específicos.

### 3. Geração de Relatórios PDF
Transforma a análise digital (JSON) em um documento executivo (`.pdf`). O relatório inclui:
- Capa com resumo executivo.
- Gráficos de tendência e distribuição.
- Detalhamento dos top clusters (Título, explicação, volumetria e exemplos).

## <a id="3-arquitetura-e-fluxo-do-pipeline"></a>3 - Arquitetura e Fluxo do Pipeline 🧠

O script `scripts/run_pipeline.py` executa um fluxo linear de 7 etapas críticas. Entender esse fluxo é essencial para manter o sistema.

### ETAPA 1: Extração e Vetorização (ETL)
1.  **Conexão**: O sistema conecta no MySQL e busca chamados dos últimos X dias (ex: 180 dias) para o sistema alvo.
2.  **Vetorização**:
    -   Cada chamado (Título + Descrição) é enviado para a API de Embeddings da OpenAI.
    -   Recebemos um vetor de 1536 dimensões representando o significado semântico do problema.
    -   Os vetores são armazenados no **Qdrant** para cache (evitar gastar dinheiro re-processando chamados antigos).

### ETAPA 2: Clustering Hierárquico (Matemática)
Utilizamos uma abordagem híbrida para agrupar os dados:
1.  **Micro-Clustering (HDBSCAN)**: O algoritmo analisa a densidade dos pontos no espaço vetorial. Pontos muito próximos formam um "Micro-Cluster" (ex: "Erro de NullPointerException no Login"). Pontos isolados são marcados como ruído (-1).
2.  **Macro-Agrupamento**: O sistema calcula o centróide de cada micro-cluster e então agrupa esses centróides entre si, criando "Super Grupos" ou Categorias Pai (ex: "Falhas Gerais de Autenticação"). Isso cria a árvore de navegação do sistema.

### ETAPA 3: Análise de Micro-Clusters (IA Assíncrona)
Para cada pequeno grupo formado:
1.  Selecionamos amostras representativas (chamados mais próximos do centro do cluster).
2.  Enviamos para o LLM com um prompt especializado: *"Analise estes 10 chamados e defina um Título Técnico e uma Descrição do problema raiz."*
3.  O LLM retorna metadados estruturados (Título, Tags, Análise Racional).
> *Nota: Isso é feito em paralelo (AsyncIO) para processar centenas de grupos em segundos.*

### ETAPA 4: Consolidação Hierárquica
O pipeline monta a estrutura de árvore (Pai -> Filhos):
- Se um Pai tem vários filhos, ele agrega as métricas de todos eles (soma volumes, combina top ofensores).
- Se um Pai tem apenas 1 filho, a estrutura é "achatada" (Flatten) para simplificar a visualização.

### ETAPA 5: Análise Macro-Executiva (IA)
Para cada Categoria Pai formada:
1.  O sistema envia para o LLM os títulos e descrições dos seus **Filhos**.
2.  O prompt muda: *"Atuando como um Gerente Técnico, resuma o que esses sub-problemas representam em alto nível."*
3.  Isso gera os cards principais da dashboard.

### ETAPA 6: Tratamento de Ruído
Chamados que não formaram grupos densos (dispersos/variados) são coletados em um grupo especial "Outros / Dispersos". Isso garante que 100% da volumetria seja contabilizada, mesmo que não haja padrão claro.

### ETAPA 7: Persistência (JSON)
O resultado final é salvo em `data_output/analise_<sistema>_<data>.json`. Este arquivo é a fonte da verdade para o Frontend e para o gerador de PDF.

## <a id="4-instalação-e-configuração"></a>4 - Instalação e Configuração 🛠

### Pré-requisitos
1.  **Banco de Dados MySQL**: Contendo a tabela de chamados (ver `ddl.sql`).
2.  **Docker**: Para rodar o Qdrant.
3.  **Chave OpenAI**: Necessária para embeddings e LLM.

### Configuração do Ambiente (.env)
Crie um arquivo `.env` na raiz baseado no exemplo abaixo:

```ini
# Configurações do Projeto
PROJECT_NAME="Scope Intelligence"
DEBUG=True

# Banco de Dados (MySQL)
DATABASE_URL="mysql+mysqlconnector://user:pass@localhost:3306/suporte_db"

# Vetor Store (Qdrant)
QDRANT_HOST="localhost"
QDRANT_PORT=6333

# OpenAI (Inteligência)
OPENAI_API_KEY="sk-..."
```

## <a id="5-como-executar"></a>5 - Como Executar ▶️

### 1. Subir Infraestrutura (Qdrant)
Inicie o banco vetorial utilizando Docker:
```powershell
docker-compose up -d
```

### 2. Executar o Pipeline de Análise
Para realizar uma análise completa de um sistema (ex: "PainelRH") considerando 180 dias de histórico:

```powershell
# Ative o ambiente virtual (recomendado)
.\venvscope\Scripts\activate

# Execute o script (a partir da raiz do projeto)
python scripts/run_pipeline.py --sistema "PainelRH" --dias 180
```
*Aguarde o processamento. Logs detalhados serão exibidos no terminal indicando cada etapa.*

### 3. Rodar a API (Opcional)
Se desejar servir os dados via API:
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Acesse a documentação automática em: `http://localhost:8000/docs`

### 4. Gerar Relatório PDF
Para gerar o PDF a partir do último JSON gerado:
```powershell
python scripts/generate_report.py --input "data_output/analise_PainelRH_20231027.json"
```

## <a id="6-modelagem-de-dados"></a>6 - Modelagem de Dados 💾

### Input (MySQL)
O sistema espera uma tabela com colunas mínimas para análise:
- `id_chamado` (Identificador único)
- `titulo` (Texto curto)
- `descricao` (Texto longo - corpo do chamado)
- `data_abertura` (Datetime)
- `solicitante`, `area`, `status` (Metadados para filtros)

### Output (JSON Structure)
O JSON final possui o seguinte esquema simplificado:

```json
{
  "metadata": {
    "sistema": "PainelRH",
    "total_grupos": 12,
    "taxa_ruido": 0.15
  },
  "clusters": [
    {
      "cluster_id": 10001,
      "titulo": "Falha de Autenticação SSO",
      "descricao": "Problemas relacionados a expiração de token...",
      "metricas": { "volume": 150, "top_servicos": {...} },
      "sub_clusters": [
        { "titulo": "Erro 401 no Login", "volume": 80 },
        { "titulo": "Token Inválido na API", "volume": 70 }
      ]
    }
  ]
}
```
