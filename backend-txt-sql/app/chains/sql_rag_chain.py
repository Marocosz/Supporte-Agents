# =================================================================================================
# =================================================================================================
#
#                 MÓDULO DE ORQUESTRAÇÃO DA CADEIA DE CONVERSA (RAG)
#
# -------------------------------------------------------------------------------------------------
# MANUTENÇÃO DE ROBUSTEZ:
# Funções de limpeza (Regex) para SQL e JSON garantem que a saída seja sempre válida,
# mesmo que o modelo tente conversar.
# =================================================================================================

import logging
import re
import json
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.runnables import Runnable, RunnablePassthrough, RunnableBranch, RunnableLambda

# Módulos internos
from app.core.llm import get_llm, get_answer_llm
from app.core.database import db_instance, get_compact_db_schema
from app.prompts.sql_prompts import SQL_PROMPT, FINAL_ANSWER_PROMPT, ROUTER_PROMPT, REPHRASER_PROMPT

logger = logging.getLogger(__name__)

store = {}

def get_session_data(session_id: str) -> dict:
    if session_id not in store:
        store[session_id] = {
            "history": ChatMessageHistory(),
            "last_sql": "Nenhuma query foi executada ainda."
        }
    return store[session_id]

def get_session_history(session_id: str) -> ChatMessageHistory:
    return get_session_data(session_id)["history"]

def update_last_sql(session_id: str, sql: str):
    if session_id in store:
        if sql and "erro:" not in sql.lower():
            logger.info(f"Atualizando last_sql para a sessão {session_id}: {sql}")
            store[session_id]["last_sql"] = sql

# --- FUNÇÃO DE LIMPEZA DE SQL ---
def clean_sql_output(text: str) -> str:
    pattern = r"```(?:sql)?\s*(.*?)```"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(1)
    return text.strip()

# --- FUNÇÃO DE LIMPEZA DE JSON ---
def clean_json_output(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            json_str = match.group(1)
            try:
                return json.loads(json_str)
            except:
                pass
        
        logger.error(f"Falha ao extrair JSON da resposta: {text}")
        return {
            "type": "text",
            "content": f"Não foi possível formatar a resposta. Conteúdo bruto: {text}"
        }

def create_master_chain() -> Runnable:
    
    def trim_history(data):
        history = data.get("chat_history", [])
        k = 6
        if len(history) > k:
            data["chat_history"] = history[-k:]
        return data

    def execute_sql_query(query: str) -> str:
        query = clean_sql_output(query)
        logger.info(f"Executando a query SQL: {query}")
        
        query_lower = query.lower()
        is_aggregation = any(agg in query_lower for agg in ["count(", "sum(", "avg("])
        has_group_by = "group by" in query_lower
        has_limit = "limit" in query_lower

        if query_lower.strip().startswith("select") and not has_limit:
            if not is_aggregation or has_group_by:
                if query.strip().endswith(';'):
                    query = query.strip()[:-1] + " LIMIT 100;"
                else:
                    query = query.strip() + " LIMIT 100;"
                logger.warning(f"Query modificada para incluir LIMIT: {query}")
                
        try:
            result = db_instance.run(query, include_columns=True)
            if not result or result == '[]':
                logger.warning("Query retornou resultado vazio. Informando ao LLM.")
                return "RESULTADO_VAZIO: Nenhuma informação encontrada para a sua solicitação."
            return result
        except Exception as e:
            logger.error(f"Erro ao executar a query: {e}")
            return f"ERRO_DB: A query falhou. Causa: {e}. Tente reformular a pergunta."
    
    parser = JsonOutputParser()

    # --- ROUTER ---
    router_prompt_with_history = ChatPromptTemplate.from_messages([
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", ROUTER_PROMPT.template) 
    ])
    def clean_router_output(text: str) -> str:
        return text.strip().strip("`").strip("'").strip('"')

    router_chain = router_prompt_with_history | get_answer_llm() | StrOutputParser() | RunnableLambda(clean_router_output)
    
    def format_simple_chat_output(text_content: str) -> dict:
        return {
            "type": "text",
            "content": text_content,
            "generated_sql": "Nenhuma query foi necessária para esta resposta."
        }

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

    # --- CADEIA 1: REPHRASER ---
    rephrasing_chain = (
        {
            "question": lambda x: x["question"],
            "chat_history": lambda x: x["chat_history"]
        }
        | REPHRASER_PROMPT
        | get_answer_llm()
        | StrOutputParser()
        | RunnableLambda(lambda x: x.strip('"').strip("'"))
    )

    # --- CADEIA 2: GERADOR SQL ---
    sql_generation_chain = (
        RunnablePassthrough.assign(schema=lambda _: get_compact_db_schema())
        | SQL_PROMPT
        | get_llm()
        | StrOutputParser()
        | RunnableLambda(clean_sql_output)
    )
    
    def execute_and_log_query(data: dict) -> str:
        query = data["generated_sql"]
        result = execute_sql_query(query)
        logger.info(f"===> RESULTADO BRUTO DO DB (VIA LANGCHAIN): {result!r}")
        return result

    # --- CADEIA 3: RESPOSTA FINAL ---
    final_response_chain = (
        {
            "result": lambda x: x["query_result"],
            "question": lambda x: x["question"],
            "format_instructions": lambda x: parser.get_format_instructions(),
        }
        | FINAL_ANSWER_PROMPT
        | get_answer_llm()
        | StrOutputParser()
        | RunnableLambda(clean_json_output)
    )

    def combine_sql_with_response(data: dict) -> dict:
        final_json_response = data["final_response_json"]
        if not isinstance(final_json_response, dict):
             final_json_response = {"type": "text", "content": str(final_json_response)}
        final_json_response["generated_sql"] = data["generated_sql"]
        return final_json_response

    # --- PIPELINE SQL ---
    sql_chain = (
        RunnablePassthrough.assign(standalone_question=rephrasing_chain)
        .assign(
            _log_standalone_question=RunnableLambda(
                lambda x: logger.info(f"Pergunta Reescrita pelo Rephraser: '{x['standalone_question']}'")
            )
        )
        .assign(generated_sql=lambda x: sql_generation_chain.invoke({"question": x["standalone_question"]}))
        .assign(
            query_result=execute_and_log_query,
            _update_sql=lambda x, config: update_last_sql(config["configurable"]["session_id"], x["generated_sql"])
        )
        .assign(
            final_response_json=lambda x: final_response_chain.invoke({
                "question": x["standalone_question"],
                "query_result": x["query_result"]
            })
        )
        | RunnableLambda(combine_sql_with_response)
    )

    fallback_chain = RunnableLambda(lambda x: {"type": "text", "content": "Desculpe, não entendi sua pergunta. Pode reformular?"})

    branch = RunnableBranch(
        (lambda x: "consulta_ao_banco_de_dados" in x["topic"], sql_chain),
        (lambda x: "saudacao_ou_conversa_simples" in x["topic"], simple_chat_chain),
        fallback_chain,
    )

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

    main_chain = (
        RunnableLambda(trim_history)
        | RunnablePassthrough.assign(topic=router_chain) 
        | branch
        | RunnableLambda(format_final_output)
    )

    chain_with_memory = RunnableWithMessageHistory(
        main_chain,
        get_session_history,
        input_messages_key="question",
        history_messages_key="chat_history",
        output_messages_key="history_message",
    )
    
    return chain_with_memory