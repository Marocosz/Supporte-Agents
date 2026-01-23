# Plano Mestre de Reestruturação Backend Text-to-SQL (Enterprise Grade v2.1)

## 1. Visão Geral e Filosofia Arquitetural
Este documento define o roteiro para transformar o backend atual em uma **Plataforma de Inteligência Logística Enterprise**.

### A Mudança de Paradigma
* **De:** Um script linear onde a IA tenta fazer tudo (decidir, gerar, corrigir).
* **Para:** Uma **Arquitetura Hub-and-Spoke Orquestrada**.

### Por que "Orquestrada" e não "Autônoma"?
Em ambientes corporativos, **previsibilidade > criatividade**. Agentes que conversam entre si (Swarms) criam loops infinitos, custos imprevisíveis e são difíceis de auditar.
Nossa abordagem centraliza o controle de fluxo em **código Python determinístico (Orchestrator)** e usa a IA apenas para tarefas cognitivas isoladas (Router, Geração SQL, Correção, RAG).

---

## 2. O Time de Agentes (Specialist Squad)

Não dependeremos apenas de Tracking e Analytics. Para garantir robustez (tratamento de erros) e inteligência de negócio (conceitos), expandiremos o time.

### 2.1. The Router (O Classificador)
* **Função:** Decidir a intenção do usuário.
* **Modelo:** Leve e Rápido (GPT-4o-mini ou GPT-5-nano).
* **Categorias:** `TRACKING`, `ANALYTICS`, `KNOWLEDGE` (Librarian), `CHAT`.
* **Motivação:** Não gastar tokens de um modelo caro (GPT-4o/5) apenas para saber para onde ir.

### 2.2. The Tracking Agent (O Operacional)
* **Função:** Busca pontual de entidades (Nota, Pedido, Carga).
* **Especialidade:** SQL com `DISTINCT ON`, `LIMIT 1`, `ORDER BY last_updated`.
* **Motivação:** Resolver o problema de "qual dado é o mais recente" e duplicidade de séries.

### 2.3. The Analytics Agent (O Gerencial)
* **Função:** Agregações, métricas e tendências.
* **Especialidade:** `GROUP BY`, `SUM`, `AVG`, `COUNT`.
* **Motivação:** Responder perguntas estratégicas sem alucinar dados detalhados linha a linha.

### 2.4. The Fixer Agent (O Mecânico - **NOVO**)
* **Função:** Recebe um SQL quebrado + Mensagem de Erro do Banco e gera o SQL corrigido.
* **Input:** `[Schema, SQL Incorreto, Erro do PostgreSQL]`.
* **Motivação:** Text-to-SQL falha (~15-20% das vezes). O Fixer aumenta a taxa de sucesso final para ~95% corrigindo erros de sintaxe ou colunas inexistentes automaticamente, sem o usuário perceber.

### 2.5. The Librarian Agent (O Bibliotecário - SIMPLIFICADO)
* **Função:** Responder dúvidas conceituais sobre o negócio.
* **Técnica:** **Context Injection (Prompt com Regras)**.
* **Input:** O prompt deste agente contém um dicionário fixo de definições (ex: "Status Bloqueado = Falta pagamento").
* **Motivação:** O banco de dados sabe *quantas* notas estão "Bloqueadas", mas não sabe *o que significa* "Bloqueado". Como o volume de regras é controlado, injetar no prompt é muito mais rápido, simples e barato do que implementar uma infraestrutura de RAG (Vector DB) completa.

---

## 3. O Cérebro: Orchestrator Service (Máquina de Estados)

O Orchestrator deixa de ser um repassador linear e torna-se uma **Máquina de Estados Finita (FSM)** escrita em Python. Ele gerencia o ciclo de vida da requisição, tomando decisões lógicas e chamando os agentes apenas quando necessário.

### Fluxo de Execução Detalhado e Inteligente

O processo ocorre em **7 Estágios de Decisão**, onde cada etapa pode desviar o fluxo ou encerrar a resposta.



#### 1. Input Layer & Short-Circuit (Latência Zero)
* **Ação:** O Orchestrator recebe a mensagem crua.
* **Lógica:** Verifica se a mensagem é uma saudação simples ("Oi", "Start", "Bom dia") ou vazia.
* **Decisão:** Se positivo, retorna imediatamente uma resposta estática cacheada. **Não aciona nenhuma IA.**

#### 2. State 1: Context Resolution (Antes da IA)
* **Problema:** Usuário pergunta "Qual o valor dela?". A IA não sabe quem é "ela".
* **Ação:** O Orchestrator consulta o `Context Manager` (Memória de Sessão).
* **Lógica:** Se houver um pronome relativo, ele recupera a última entidade válida (ex: "Nota 40908") e reescreve a query internamente para: "Qual o valor da Nota 40908?".
* **Resultado:** A query enviada para os próximos passos já está completa e desambiguada.

#### 3. State 2: Routing (O Despachante)
* **Ação:** O Orchestrator envia a query higienizada para o **Router Agent**.
* **Decisão:** O Router classifica a intenção em um de dois grandes caminhos:
    * **Caminho A (Knowledge Flow):** Dúvidas conceituais ("O que é status bloqueado?", "Qual o prazo?"). -> **Vai para o State 3A (Librarian).**
    * **Caminho B (SQL Flow):** Busca de dados ("Status da nota", "Total vendido"). -> **Vai para o State 3B (Specialists).**

#### 4. State 3A: Knowledge Flow (Librarian)
* **Ativação:** Apenas se o Router detectou dúvida de negócio.
* **Ação:** O **Librarian Agent** lê as regras injetadas no prompt e explica o conceito ao usuário.
* **Fim do Ciclo:** O fluxo encerra aqui e vai para a Formatação.

#### 5. State 3B: Generation SQL Flow (Specialists)
* **Ativação:** Apenas se o Router detectou necessidade de dados do banco.
* **Decisão:** Com base na subclassificação do Router:
    * Se for busca pontual -> Aciona **Tracking Agent**.
    * Se for agregação -> Aciona **Analytics Agent**.
* **Ação:** O agente escolhido gera o SQL candidato (ex: `SELECT * FROM...`). **O agente NÃO executa o SQL.**

#### 6. State 4: Security Guard (Hard Logic)
* **Ação:** O código Python (SQL Guard) intercepta o SQL gerado.
* **Validação:**
    1.  Verifica comandos proibidos (`DELETE`, `DROP`).
    2.  Parseia a query em uma árvore sintática (AST).
    3.  **Injeta Obrigatoriamente:** A cláusula `WHERE cod_fornecedor = :tenant_id` em todas as tabelas relevantes.
* **Resultado:** Um SQL blindado e seguro para o cliente específico.

#### 7. State 5: Execution & Self-Healing (Loop Crítico)
* **Ação:** O Orchestrator tenta executar o SQL no banco (`db.run()`).
* **Cenário de Sucesso:** O banco retorna dados. Vai para o State 6.
* **Cenário de Erro (Exception):** O banco retorna um erro (ex: `Syntax Error`, `Column not found`).
    * **Ativação do FIXER:** O Orchestrator captura o erro e chama o **Fixer Agent**.
    * **Input do Fixer:** `[Schema, SQL Errado, Mensagem de Erro]`.
    * **Output:** SQL Corrigido.
    * **Retry:** O Orchestrator volta para o State 4 (Segurança) com o novo SQL e tenta novamente. (Limite de 2 tentativas).

#### 8. State 6: Presentation
* **Ação:** O Orchestrator recebe os dados brutos (seja texto do Librarian ou tuplas do Banco).
* **Lógica:** Encaminha para o módulo de Formatação (Presenter) que transforma os dados brutos em JSON estruturado para o Frontend (Cards visuais ou Configuração de Gráficos).

---

## 4. Segurança Multi-Tenant (Camada de Infraestrutura)

A segurança **nunca** é delegada ao Prompt do LLM ("Por favor, não mostre dados de outros"). Ela é imposta pelo código.

### Componente: `SQL Guard`
* **Ferramenta:** `sqlglot` ou `pglast` (Parsers de SQL robustos).
* **Lógica:**
    1.  Recebe query gerada.
    2.  Parseia para uma árvore sintática (AST).
    3.  Percorre todos os nós `SELECT`.
    4.  Insere/Combina a cláusula `WHERE cod_fornecedor = :current_user_supplier` via manipulação da árvore.
* **Motivação:** Garante matematicamente que é impossível vazar dados entre clientes, mesmo que a IA alucine e tente remover o filtro.

---

## 5. Estratégia de Prompt Engineering (Contrato JSON)

Todos os agentes devem seguir o protocolo **Strict JSON Output**.

* **Regra:** NENHUM texto fora do JSON.
* **Estrutura Base:**
    ```json
    {
      "thought_process": "Breve racional (ajuda a IA a raciocinar antes de responder)",
      "sql": "SELECT ...",
      "missing_info": null,
      "confidence": 0.95
    }
    ```
* **Motivação:** Facilita o parse no Python e evita que a IA peça desculpas ("Desculpe, aqui está a query..."), o que quebra o sistema.

---

## 6. Estrutura de Diretórios Proposta

```text
/backend
├── /app
│   ├── /api                  # Endpoints FastAPI (Exposto para o mundo)
│   │   ├── routes.py
│   │   └── dependencies.py   # Auth, Session Middleware
│   ├── /core                 # Configurações Globais
│   │   ├── config.py         # Env vars, Model Selection
│   │   ├── database.py       # Connection Pool
│   │   └── security.py       # Validação de Token
│   ├── /services             # Lógica "Heavy" (Python Puro)
│   │   ├── orchestrator.py   # A Máquina de Estados (FSM)
│   │   ├── context.py        # Gerenciador de Memória (Redis/Dict)
│   │   └── sql_guard.py      # Parser e Injetor de Segurança
│   ├── /agents               # Os Especialistas (LangChain/LLM)
│   │   ├── base.py           # Interface comum
│   │   ├── router.py         # Classificador
│   │   ├── tracking.py       # Busca Pontual
│   │   ├── analytics.py      # Agregações
│   │   ├── fixer.py          # Corretor de SQL (Self-healing)
│   │   └── librarian.py      # Regras de Negócio (Prompt)
│   └── /prompts              # Templates de Texto (Separados do código)
│       ├── tracking_prompts.py
│       ├── analytics_prompts.py
│       └── ...
├── /tests                    # Testes Unitários
├── .env
└── main.py
```

---

## 7. Roadmap de Implementação (Passo a Passo)

### Fase 1: Fundação & Segurança (Semana 1)
1.  Setup do projeto limpo.
2.  Implementação do `SQL Guard`. Criar testes unitários provando que ele injeta o `WHERE` corretamente em queries complexas.
3.  Implementação do `Context Manager` (estrutura de dados para salvar intenção e entidades da sessão).

### Fase 2: O Cérebro & Roteamento (Semana 2)
1.  Implementar `orchestrator.py` com a lógica de Short-circuit ("Oi").
2.  Implementar `Router Agent` e conectar ao Orchestrator.
3.  Validar fluxo: API -> Orchestrator -> Router -> Log (sem gerar SQL ainda).

### Fase 3: Agentes de Dados & Fixer (Semana 3)
1.  Refatorar `Tracking Agent` com prompts focados em `DISTINCT`.
2.  Criar o `Fixer Agent`.
3.  Implementar o loop de retry no Orchestrator (`try...catch...fix...retry`).
4.  Conectar tudo ao Banco de Dados.

### Fase 4: Refinamento & Librarian (Semana 4)
1.  Implementar o `Analytics Agent`.
2.  Criar o arquivo de regras e o `Librarian Agent` (Prompt System).
3.  Ajustar o `Presenter` para formatar os JSONs de resposta para o frontend.

---

## 8. Resumo dos Ganhos

1.  **Resiliência:** O sistema não quebra com erros de SQL; ele se corrige (`Fixer`).
2.  **Segurança Real:** Filtros injetados via AST (`SQL Guard`), não via prompt.
3.  **Velocidade:** Short-circuits e modelos menores para tarefas simples (`Router`).
4.  **Inteligência de Negócio:** Capacidade de responder "O que é isso?" (`Librarian`) além de "Quanto é isso?".
5.  **Manutenibilidade:** Cada agente é um arquivo isolado. Lógica de controle centralizada no Orchestrator.