# =================================================================================================
# =================================================================================================
#
#                 MÓDULO DE ORQUESTRAÇÃO DA CADEIA DE CONVERSA (RAG)
#
# Visão Geral da Arquitetura Lógica:
#
# Este arquivo constrói e orquestra a cadeia principal de conversação (a "master chain")
# usando a LangChain Expression Language (LCEL). A cadeia funciona como uma linha de montagem
# inteligente que processa cada pergunta do usuário através dos seguintes estágios:
#
# 1. Gerenciamento de Memória (`RunnableWithMessageHistory`):
#    - No início de cada turno, carrega o histórico da conversa da sessão atual.
#    - No final, salva a nova pergunta e resposta, tornando a conversa contínua.
#
# 2. Roteamento (`router_chain`):
#    - O primeiro passo lógico. Analisa a intenção da pergunta para decidir se é uma
#      conversa simples ou uma consulta complexa que exige acesso ao banco de dados.
#
# 3. Execução Condicional (`RunnableBranch`):
#    - Atua como um desvio, enviando a pergunta para a sub-cadeia apropriada com base
#      na decisão do roteador (ou para a `simple_chat_chain` ou para a `sql_chain`).
#
# 4. A Sub-Cadeia SQL (`sql_chain`):
#    a. Reescrita da Pergunta (`rephrasing_chain`): Resolve o contexto do histórico,
#        transformando perguntas ambíguas em perguntas claras e autônomas.
#    b. Geração de SQL (`sql_generation_chain`): Traduz a pergunta clara em uma query SQL.
#    c. Execução Segura da Query: Roda a query no banco com mecanismos de segurança.
#    d. Geração da Resposta Final (`final_response_chain`): Formata o resultado do
#        banco em uma resposta JSON amigável (texto ou gráfico).
#
# O resultado é uma aplicação robusta que separa as responsabilidades em componentes
# lógicos e especializados, facilitando a manutenção e a depuração.
#
# =================================================================================================
# =================================================================================================

import logging
# Componentes principais do LangChain para construir e gerenciar cadeias de conversação.
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.runnables import Runnable, RunnablePassthrough, RunnableBranch, RunnableLambda

# Módulos internos para acesso ao LLM e ao banco de dados.
from app.core.llm import get_llm, get_answer_llm
from app.core.database import db_instance, get_compact_db_schema

# Importa todos os prompts especializados do arquivo de prompts.
from app.prompts.sql_prompts import SQL_PROMPT, FINAL_ANSWER_PROMPT, ROUTER_PROMPT, REPHRASER_PROMPT

# Configura o logger para este módulo.
logger = logging.getLogger(__name__)

# Dicionário global que funciona como um armazenamento em memória para as sessões de chat.
# Para cada `session_id`, ele guarda o histórico de mensagens e a última query SQL executada.
store = {}

def get_session_data(session_id: str) -> dict:
    """
    Recupera ou cria o dicionário de dados para uma sessão de usuário específica no `store`.
    """
    if session_id not in store:
        store[session_id] = {
            "history": ChatMessageHistory(),
            "last_sql": "Nenhuma query foi executada ainda."
        }
    return store[session_id]

def get_session_history(session_id: str) -> ChatMessageHistory:
    """
    Função "getter" exigida pelo `RunnableWithMessageHistory`.
    Ela fornece o objeto de histórico de mensagens para uma sessão específica.
    """
    return get_session_data(session_id)["history"]

def update_last_sql(session_id: str, sql: str):
    """
    Atualiza a última query SQL executada para uma sessão.
    Isso é útil para depuração e lógicas de contexto futuras.
    """
    if session_id in store:
        if sql and "erro:" not in sql.lower():
            logger.info(f"Atualizando last_sql para a sessão {session_id}: {sql}")
            store[session_id]["last_sql"] = sql


def create_master_chain() -> Runnable:
    """
    Cria e retorna a cadeia principal de LangChain, que orquestra todo o fluxo de conversa.
    Esta função é o coração da lógica de orquestração.
    """

    def trim_history(data):
        """
        Função interna para limitar o histórico de chat a um número `k` de mensagens.
        Isso é crucial para evitar exceder o limite de tokens do LLM.
        """
        history = data.get("chat_history", [])
        k = 6
        if len(history) > k:
            data["chat_history"] = history[-k:]
        return data

    def execute_sql_query(query: str) -> str:
        """
        Executa a query SQL de forma segura, adicionando um LIMIT e tratando erros.
        Funciona como uma camada de proteção entre o LLM e o banco de dados.
        """
        logger.info(f"Executando a query SQL: {query}")
        query_lower = query.lower()

        # Verifica características da query para decidir se deve adicionar um LIMIT.
        is_aggregation = any(agg in query_lower for agg in ["count(", "sum(", "avg("])
        has_group_by = "group by" in query_lower
        has_limit = "limit" in query_lower

        # Adiciona 'LIMIT 100' para evitar que o LLM solicite dados em excesso,
        # a menos que seja uma agregação de valor único ou já possua um limite.
        if query_lower.strip().startswith("select") and not has_limit:
            if not is_aggregation or has_group_by:
                if query.strip().endswith(';'):
                    query = query.strip()[:-1] + " LIMIT 100;"
                else:
                    query = query.strip() + " LIMIT 100;"
                logger.warning(f"Query modificada para incluir LIMIT: {query}")
                
        try:
            # Executa a query usando a integração do LangChain com o banco.
            result = db_instance.run(query, include_columns=True)
            
            # Formata o resultado para o LLM em caso de não encontrar dados.
            if not result or result == '[]':
                logger.warning("Query retornou resultado vazio. Informando ao LLM.")
                return "RESULTADO_VAZIO: Nenhuma informação encontrada para a sua solicitação."
            
            return result
            
        except Exception as e:
            # Em caso de erro do banco, formata uma mensagem clara para o LLM.
            logger.error(f"Erro ao executar a query: {e}")
            return f"ERRO_DB: A query falhou. Causa: {e}. Tente reformular a pergunta."
    
    # Objeto que garante que a saída do LLM Analista de Dados seja um JSON válido.
    parser = JsonOutputParser()

    # Define a cadeia do "Porteiro", que classifica a intenção do usuário.
    router_prompt_with_history = ChatPromptTemplate.from_messages([
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", ROUTER_PROMPT.template) 
    ])
    router_chain = router_prompt_with_history | get_answer_llm() | StrOutputParser()
    
    # Função auxiliar para manter a estrutura da resposta da API consistente.
    def format_simple_chat_output(text_content: str) -> dict:
        return {
            "type": "text",
            "content": text_content,
            "generated_sql": "Nenhuma query foi necessária para esta resposta."
        }

    # Define a cadeia para conversas simples que não acessam o banco de dados.
    simple_chat_prompt_with_history = ChatPromptTemplate.from_messages([
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "Você é um assistente amigável chamado Supporte IA. Responda de forma concisa e útil.")
    ])
    simple_chat_chain = (
        simple_chat_prompt_with_history
        | get_answer_llm() 
        | StrOutputParser()
        | RunnableLambda(format_simple_chat_output)
    )

    # 1. Define a cadeia do "Especialista em Contexto" (Rephraser).
    rephrasing_chain = (
        {
            "question": lambda x: x["question"],
            "chat_history": lambda x: x["chat_history"]
        }
        | REPHRASER_PROMPT
        | get_answer_llm()
        | StrOutputParser()
    )

    # 2. Define a cadeia do "Engenheiro de Banco de Dados", que traduz uma pergunta clara em SQL.
    sql_generation_chain = (
        RunnablePassthrough.assign(schema=lambda _: get_compact_db_schema())
        | SQL_PROMPT
        | get_llm()
        | StrOutputParser()
    )
    
    # Função auxiliar para logar o resultado da query executada.
    def execute_and_log_query(data: dict) -> str:
        query = data["generated_sql"]
        result = execute_sql_query(query)
        logger.info(f"===> RESULTADO BRUTO DO DB (VIA LANGCHAIN): {result!r}")
        return result

    # Define a cadeia do "Analista de Dados", que formata a resposta final.
    final_response_chain = (
        {
            "result": lambda x: x["query_result"],
            "question": lambda x: x["question"],
            "format_instructions": lambda x: parser.get_format_instructions(),
        }
        | FINAL_ANSWER_PROMPT
        | get_answer_llm()
        | parser
    )

    # Função auxiliar para combinar a resposta final com o SQL gerado para a API.
    def combine_sql_with_response(data: dict) -> dict:
        final_json_response = data["final_response_json"]
        final_json_response["generated_sql"] = data["generated_sql"]
        return final_json_response

    # 3. Monta a `sql_chain`, a linha de montagem completa para consultas ao banco.
    sql_chain = (
        # Passo 1: Invoca o Rephraser para obter uma pergunta clara e autônoma.
        RunnablePassthrough.assign(standalone_question=rephrasing_chain)
        .assign(
            # Adiciona um log para vermos a pergunta reescrita. Ótimo para debug!
            _log_standalone_question=RunnableLambda(
                lambda x: logger.info(f"Pergunta Reescrita pelo Rephraser: '{x['standalone_question']}'")
            )
        )
        # Passo 2: Gera o SQL usando APENAS a pergunta autônoma.
        .assign(generated_sql=lambda x: sql_generation_chain.invoke({"question": x["standalone_question"]}))
        # Passo 3: Executa a query e atualiza o estado da sessão.
        .assign(
            query_result=execute_and_log_query,
            _update_sql=lambda x, config: update_last_sql(config["configurable"]["session_id"], x["generated_sql"])
        )
        # Passo 4: Gera a resposta final, também usando a pergunta autônoma para contexto.
        .assign(
            final_response_json=lambda x: final_response_chain.invoke({
                "question": x["standalone_question"],
                "query_result": x["query_result"]
            })
        )
        # Passo 5: Combina a resposta com o SQL gerado para a saída final da API.
        | RunnableLambda(combine_sql_with_response)
    )

    # Cadeia de fallback para quando o roteador não consegue classificar a pergunta.
    fallback_chain = RunnableLambda(lambda x: {"type": "text", "content": "Desculpe, não entendi sua pergunta. Pode reformular?"})

    # O componente de desvio que usa a saída do `router_chain` para escolher o caminho a seguir.
    branch = RunnableBranch(
        (lambda x: "consulta_ao_banco_de_dados" in x["topic"], sql_chain),
        (lambda x: "saudacao_ou_conversa_simples" in x["topic"], simple_chat_chain),
        fallback_chain,
    )

    # Função final para formatar a saída da cadeia em dois formatos:
    # `api_response`: O JSON completo para o frontend.
    # `history_message`: Um texto simplificado para ser salvo no histórico do chat.
    def format_final_output(chain_output: dict) -> dict:
        history_content = ""
        if isinstance(chain_output, dict):
            if chain_output.get("type") == "text":
                history_content = chain_output.get("content", "Não foi possível gerar uma resposta.")
            elif chain_output.get("type") == "chart":
                title = chain_output.get("title", "sem título")
                history_content = f"Gerei um gráfico para você sobre: '{title}'"
        
        return {
            "api_response": chain_output, 
            "history_message": history_content
        }

    # A cadeia principal que une os passos iniciais.
    main_chain = (
        RunnableLambda(trim_history)
        | RunnablePassthrough.assign(topic=router_chain) 
        | branch
        | RunnableLambda(format_final_output)
    )

    # O invólucro final que adiciona o gerenciamento automático de histórico de chat à cadeia principal.
    # Este é o objeto que será retornado e usado pela API.
    chain_with_memory = RunnableWithMessageHistory(
        main_chain,
        get_session_history,
        input_messages_key="question",
        history_messages_key="chat_history",
        output_messages_key="history_message",
    )
    
    return chain_with_memory

# =================================================================================================
# Análise de Fluxo e Dados das Cadeias (Chains)
#
# =================================================================================================
#
# 1. router_chain
# Propósito: Classificar a intenção do usuário para decidir se a pergunta requer uma consulta
# ao banco de dados ou se é uma conversa casual.
# Fluxo Detalhado:
#   1. Recebe a pergunta do usuário e o histórico da conversa.
#   2. Monta o ROUTER_PROMPT com essas informações.
#   3. Envia o prompt para um LLM.
#   4. O StrOutputParser garante que a saída seja uma string de texto limpa.
# Exemplo de Entrada:
#   {
#     "question": "e qual o total de mercadorias dele?",
#     "chat_history": ["Human: Qual o cliente com mais operações? AI: O cliente é 'Porto'."]
#   }
# Exemplo de Saída:
#   "consulta_ao_banco_de_dados"
#
# -------------------------------------------------------------------------------------------------
#
# 2. simple_chat_chain
# Propósito: Gerar uma resposta amigável e conversacional para perguntas que não precisam
# de acesso ao banco de dados.
# Fluxo Detalhado:
#   1. Recebe a pergunta e o histórico.
#   2. Monta o simple_chat_prompt_with_history.
#   3. Envia para um LLM que gera a resposta textual.
#   4. O StrOutputParser limpa a resposta.
#   5. A função format_simple_chat_output envolve a resposta em um dicionário JSON padronizado.
# Exemplo de Entrada:
#   {
#     "question": "Olá, tudo bem?",
#     "chat_history": []
#   }
# Exemplo de Saída:
#   {
#     "type": "text",
#     "content": "Olá! Tudo bem. Como posso te ajudar hoje?",
#     "generated_sql": "Nenhuma query foi necessária para esta resposta."
#   }
#
# -------------------------------------------------------------------------------------------------
#
# 3. rephrasing_chain
# Propósito: Atuar como o "Especialista em Contexto". Transforma uma pergunta ambígua ou de
# acompanhamento em uma pergunta completa e autônoma.
# Fluxo Detalhado:
#   1. Recebe a pergunta do usuário e o histórico da conversa.
#   2. Usa o REPHRASER_PROMPT (um FewShotPromptTemplate) para instruir o LLM a reescrever a pergunta.
#   3. O LLM analisa o histórico e a nova pergunta para resolver o contexto.
#   4. O StrOutputParser extrai a pergunta reescrita como uma string.
# Exemplo de Entrada:
#   {
#     "question": "e qual o total de mercadorias dele?",
#     "chat_history": ["Human: Qual o cliente com mais operações? AI: O cliente é 'Porto'."]
#   }
# Exemplo de Saída:
#   "Qual o valor total de mercadorias do cliente 'Porto'?"
#
# -------------------------------------------------------------------------------------------------
#
# 4. sql_generation_chain
# Propósito: Atuar como o "Engenheiro SQL". Traduz uma pergunta clara e completa em uma
# query SQL válida.
# Fluxo Detalhado:
#   1. Recebe a pergunta já reescrita (autônoma).
#   2. O RunnablePassthrough.assign adiciona o schema do banco de dados ao contexto.
#   3. Monta o SQL_PROMPT com a pergunta e o schema.
#   4. Envia para um LLM (geralmente um modelo mais poderoso) para gerar o código SQL.
#   5. O StrOutputParser extrai a query SQL como uma string.
# Exemplo de Entrada:
#   {
#     "question": "Qual o valor total de mercadorias do cliente 'Porto'?"
#   }
# Exemplo de Saída:
#   SELECT SUM(o.valor_mercadoria) FROM operacoes_logisticas o
#   JOIN clientes c ON o.cliente_id = c.id
#   WHERE c.nome_razao_social = 'Porto'
#
# -------------------------------------------------------------------------------------------------
#
# 5. final_response_chain
# Propósito: Atuar como o "Analista de Dados". Converte o resultado bruto do banco de dados
# em uma resposta JSON amigável e estruturada (texto ou gráfico).
# Fluxo Detalhado:
#   1. Recebe a pergunta reescrita e o resultado da query.
#   2. O dicionário de entrada prepara as chaves result, question e format_instructions.
#   3. Monta o FINAL_ANSWER_PROMPT com essas informações.
#   4. Envia para um LLM que decide entre texto ou gráfico e gera uma string JSON.
#   5. O JsonOutputParser valida e converte a string em um objeto dicionário Python.
# Exemplo de Entrada:
#   {
#     "question": "Qual o valor total de mercadorias do cliente 'Porto'?",
#     "query_result": "[{'sum': 108396678.02}]"
#   }
# Exemplo de Saída:
#   {
#     "type": "text",
#     "content": "O valor total de mercadorias para o cliente 'Porto' é de R$ 108.396.678,02."
#   }
#
# -------------------------------------------------------------------------------------------------
#
# 6. sql_chain (A Linha de Montagem Completa)
# Propósito: Orquestrar a sequência completa de passos para uma consulta ao banco.
# Fluxo Detalhado:
#   1. Entrada: Recebe a pergunta original do usuário e o histórico.
#   2. Passo 1: Invoca a rephrasing_chain para obter a pergunta autônoma.
#   3. Passo 2: Passa a standalone_question para a sql_generation_chain para obter o SQL.
#   4. Passo 3: Passa a generated_sql para a função execute_and_log_query para obter o resultado.
#   5. Passo 4: Passa a standalone_question e o query_result para a final_response_chain.
#   6. Passo 5: Combina o final_response_json com a generated_sql no dicionário final.
#   7. Saída: O JSON completo, pronto para ser enviado ao frontend.
# Exemplo de Entrada:
#   {
#     "question": "e qual o total de mercadorias dele?",
#     "chat_history": ["Human: Qual o cliente com mais operações? AI: O cliente é 'Porto'."],
#     "topic": "consulta_ao_banco_de_dados"
#   }
# Exemplo de Saída:
#   {
#     "type": "text",
#     "content": "O valor total de mercadorias para o cliente 'Porto' é de R$ 108.396.678,02.",
#     "generated_sql": "SELECT SUM(o.valor_mercadoria) FROM ..."
#   }
#
# -------------------------------------------------------------------------------------------------
#
# 7. main_chain
# Propósito: A cadeia principal que orquestra o fluxo de alto nível, desde o roteamento
# até a formatação final da saída.
# Fluxo Detalhado:
#   1. Entrada: Recebe a pergunta original e o histórico.
#   2. Invoca trim_history para encurtar o histórico.
#   3. Invoca router_chain para obter o topic.
#   4. Invoca o branch que, com base no topic, escolhe entre sql_chain ou simple_chat_chain.
#   5. Passa a saída da cadeia escolhida para a função format_final_output.
# Exemplo de Entrada:
#   {
#     "question": "e qual o total de mercadorias dele?",
#     "chat_history": ["..."]
#   }
# Exemplo de Saída:
#   {
#     "api_response": {
#       "type": "text",
#       "content": "O valor total de mercadorias...",
#       "generated_sql": "SELECT SUM(...)"
#     },
#     "history_message": "O valor total de mercadorias para o cliente 'Porto' é de R$ 108.396.678,02."
#   }
#
# -------------------------------------------------------------------------------------------------
#
# 8. chain_with_memory
# Propósito: A cadeia final exportada pelo módulo. Ela envolve a main_chain com a lógica
# de gerenciamento automático de memória.
# Fluxo Detalhado:
#   1. Entrada: Recebe a pergunta do usuário e o session_id no objeto config.
#   2. Carregar Memória: Usa a função get_session_history para carregar o histórico da conversa.
#   3. Invocar a main_chain: Executa a cadeia principal com a pergunta e o histórico carregado.
#   4. Salvar Memória: Pega a question de entrada e a history_message de saída e salva de volta.
# Exemplo de Entrada (como a API a chama):
#   Input: {"question": "e qual o total de mercadorias dele?"}
#   Config: {"configurable": {"session_id": "sessao-456"}}
# Exemplo de Saída (o que a API recebe):
#   {
#     "api_response": { "..."},
#     "history_message": "..."
#   }
#
# =================================================================================================


# =================================================================================================
# Análise Detalhada das Variáveis Runnable
#
# =================================================================================================
#
# 1. router_prompt_with_history
# Tipo: ChatPromptTemplate
# Propósito: Preparar a instrução (prompt) completa para o LLM Roteador. Ele combina a instrução
# de roteamento fixa com o histórico dinâmico da conversa.
# Como Funciona:
#   1. Recebe um dicionário com question e chat_history.
#   2. O MessagesPlaceholder(variable_name="chat_history") atua como espaço reservado
#      onde a lista de mensagens do histórico é injetada.
#   3. A instrução do ROUTER_PROMPT (que contém {question}) é adicionada como a mensagem final.
# Exemplo de Entrada:
#   {
#     "question": "e o total de frete deles?",
#     "chat_history": [
#       "HumanMessage(content='Liste os 5 maiores clientes.')",
#       "AIMessage(content='Os 5 maiores clientes são...')"
#     ]
#   }
# Exemplo de Saída (o que é enviado para o LLM):
#   [
#     HumanMessage(content='Liste os 5 maiores clientes.'),
#     AIMessage(content='Os 5 maiores clientes são...'),
#     HumanMessage(content='Sua tarefa é classificar o texto do usuário... Categoria:')
#   ]
#
# -------------------------------------------------------------------------------------------------
#
# 2. simple_chat_prompt_with_history
# Tipo: ChatPromptTemplate
# Propósito: Preparar o prompt para o LLM de conversa simples, dando a ele o histórico da
# conversa e definindo sua persona como "assistente amigável".
# Como Funciona:
#   1. Recebe um dicionário com question e chat_history.
#   2. Injeta o histórico da conversa através do MessagesPlaceholder.
#   3. Adiciona a instrução de persona ("Você é um assistente amigável...") como mensagem final.
# Exemplo de Entrada:
#   {
#     "question": "Olá, tudo bem?",
#     "chat_history": []
#   }
# Exemplo de Saída (o que é enviado para o LLM):
#   [
#     HumanMessage(content='Você é um assistente amigável chamado SupporteIA. Responda de forma concisa e útil.')
#   ]
#
# -------------------------------------------------------------------------------------------------
#
# 3. O Dicionário de Preparação da final_response_chain
# Variável: (anônima, o primeiro elemento da final_response_chain)
#   {
#     "result": lambda x: x["query_result"],
#     "question": lambda x: x["question"],
#     "format_instructions": lambda x: parser.get_format_instructions(),
#   }
# Tipo: RunnableParallel
# Propósito: Preparar de forma eficiente (em paralelo) todas as peças de informação que o
# prompt FINAL_ANSWER_PROMPT precisa para funcionar.
# Como Funciona:
#   1. Recebe o dicionário de dados que está fluindo pela sql_chain.
#   2. A lambda x: x["query_result"] extrai o resultado do banco e coloca em result.
#   3. A lambda x: x["question"] extrai a pergunta (já reescrita) e coloca em question.
#   4. A lambda x: parser.get_format_instructions() gera instruções técnicas JSON e coloca
#      em format_instructions.
# Exemplo de Entrada:
#   {
#     "question": "Qual o status da operação VV820450103ER?",
#     "standalone_question": "Qual o status da operação VV820450103ER?",
#     "generated_sql": "SELECT status FROM operacoes_logisticas WHERE codigo_rastreio = 'VV820450103ER'",
#     "query_result": "[{'status': 'EM_TRANSITO'}]"
#   }
# Exemplo de Saída (o que é passado para o FINAL_ANSWER_PROMPT):
#   {
#     "result": "[{'status': 'EM_TRANSITO'}]",
#     "question": "Qual o status da operação VV820450103ER?",
#     "format_instructions": "A resposta DEVE ser um JSON formatado da seguinte maneira..."
#   }
#
# -------------------------------------------------------------------------------------------------
#
# 4. branch
# Tipo: RunnableBranch
# Propósito: Funcionar como um if/elif/else dentro da cadeia. Examina o estado atual da
# conversa (topic) e decide qual sub-cadeia deve ser executada a seguir.
# Como Funciona:
#   1. Recebe o dicionário de dados que já passou pelo router_chain e contém a chave topic.
#   2. Primeira condição: verifica se "consulta_ao_banco_de_dados" está em topic. Se sim, invoca sql_chain.
#   3. Se não, verifica se "saudacao_ou_conversa_simples" está em topic. Se sim, invoca simple_chat_chain.
#   4. Se nenhuma condição for atendida, invoca a fallback_chain como último recurso.
# Exemplo de Entrada:
#   {
#     "question": "Olá!",
#     "chat_history": [],
#     "topic": "saudacao_ou_conversa_simples"
#   }
# Exemplo de Saída:
#   {
#     "type": "text",
#     "content": "Olá! Como vai?",
#     "generated_sql": "Nenhuma query foi necessária para esta resposta."
#   }
#
# =================================================================================================
