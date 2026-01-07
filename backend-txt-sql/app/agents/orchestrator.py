import logging
from langchain_core.runnables import RunnableLambda
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from app.core.llm import get_answer_llm
from app.core.schemas import TextResponse
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
    
    # Executa a cadeia selecionada
    res = chain.invoke(inputs)
    
    # --- LÓGICA DE EXTRAÇÃO E CONSOLIDAÇÃO ---
    # Precisamos garantir que o SQL gerado (se houver) seja passado para o output final
    
    final_obj = res
    generated_sql = None

    # Se 'res' for um dicionário (padrão dos agentes Tracking/Analytics que usam RunnablePassthrough)
    if isinstance(res, dict):
        # 1. Tenta capturar o SQL real gerado na etapa anterior
        if "sql" in res:
            generated_sql = res["sql"]
        
        # 2. Extrai o objeto de resposta final (Pydantic)
        if "final_response" in res:
            final_obj = res["final_response"]
    
    # Converte o objeto Pydantic (TextResponse ou ChartResponse) para Dict
    response_dict = final_obj.model_dump() if hasattr(final_obj, "model_dump") else final_obj

    # --- INJEÇÃO DE METADADOS TÉCNICOS ---
    # Se capturamos um SQL real e o retorno é um dicionário, garantimos que ele esteja lá
    if generated_sql and isinstance(response_dict, dict):
        # Limpeza extra para garantir visualização bonita no front
        clean_sql = str(generated_sql).replace("```sql", "").replace("```", "").strip()
        response_dict["sql"] = clean_sql

    return response_dict

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