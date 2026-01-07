import logging
from langchain_core.runnables import RunnableLambda
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from app.core.llm import get_answer_llm
from app.core.schemas import TextResponse # <--- Importar
from app.agents.router_agent import get_router_chain
from app.agents.tracking_agent import get_tracking_chain
from app.agents.analytics_agent import get_analytics_chain

logger = logging.getLogger(__name__)

# --- Agente de Chat Simples ---
CHAT_PROMPT = PromptTemplate.from_template(
    """
    Você é a assistente virtual da Supporte Logística.
    Seja cordial, profissional e breve.
    O usuário mandou uma mensagem que NÃO requer consulta ao banco de dados.
    Responda de forma útil.

    Histórico: {chat_history}
    Mensagem: {question}

    Responda SEMPRE seguindo este formato JSON:
    {{
        "type": "text",
        "content": "Sua resposta aqui."
    }}
    """
)

def get_chat_chain():
    # Valida saída como TextResponse
    return CHAT_PROMPT | get_answer_llm() | PydanticOutputParser(pydantic_object=TextResponse)

# --- Lógica de Orquestração ---

def route_request(inputs):
    category = inputs["category"]
    logger.info(f"[ORCHESTRATOR] Intenção detectada: {category.upper()}")

    if category == "tracking":
        chain = get_tracking_chain()
    elif category == "analytics":
        chain = get_analytics_chain()
    else:
        chain = get_chat_chain()
    
    # Executa e retorna o objeto Pydantic já convertido em Dict pelo invoke final do api.py
    # O PydanticOutputParser retorna um OBJETO Python (TextResponse ou ChartResponse).
    # Precisamos garantir que isso vire dict (JSON) para a API.
    res = chain.invoke(inputs)
    
    # Se o output for do tipo Pydantic, convertemos para dict.
    # Se for um dict aninhado (final_response), extraímos.
    if isinstance(res, dict) and "final_response" in res:
        final_obj = res["final_response"]
        return final_obj.model_dump() if hasattr(final_obj, "model_dump") else final_obj
    
    return res.model_dump() if hasattr(res, "model_dump") else res

def get_orchestrator_chain():
    """
    Cria a cadeia principal que encapsula todo o sistema Multi-Agent.
    """
    router = get_router_chain()

    main_chain = (
        {
            "question": lambda x: x["question"],
            "chat_history": lambda x: x.get("chat_history", ""),
            "category": router
        }
        | RunnableLambda(route_request)
    )

    return main_chain