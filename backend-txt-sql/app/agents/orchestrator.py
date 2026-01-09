import logging
import re
import json
from langchain_core.runnables import RunnableLambda
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.core.llm import get_answer_llm
from app.agents.router_agent import get_router_chain
from app.agents.tracking_agent import get_tracking_chain
from app.agents.analytics_agent import get_analytics_chain

logger = logging.getLogger(__name__)

def safe_parse_json(text: str) -> dict:
    """Parser seguro para o chat."""
    text_clean = re.sub(r"```json\s*", "", text, flags=re.IGNORECASE)
    text_clean = re.sub(r"```\s*$", "", text_clean, flags=re.IGNORECASE)
    text_clean = text_clean.strip()

    match = re.search(r"(\{.*\})", text_clean, re.DOTALL)
    json_candidate = match.group(1) if match else text_clean
    
    try:
        return json.loads(json_candidate)
    except json.JSONDecodeError:
        return {"type": "text", "content": text_clean}

# --- Agente de Chat Simples ---
CHAT_PROMPT = PromptTemplate.from_template(
    """
    Você é a assistente virtual da Supporte Logística.
    O usuário disse: "{question}"
    Histórico: {chat_history}

    Responda APENAS um JSON.
    {{ "type": "text", "content": "Sua resposta aqui." }}
    """
)

def get_chat_chain():
    return (
        CHAT_PROMPT 
        | get_answer_llm() 
        | StrOutputParser()
        | RunnableLambda(safe_parse_json)
    )

# --- Lógica de Orquestração ---

def route_request(inputs):
    # LOG: Entrada do Orchestrator
    logger.info(f"\n>>> [ORCHESTRATOR] INPUTS RECEBIDOS:\n{json.dumps(inputs, indent=2, ensure_ascii=False)}")

    category = inputs["category"]
    logger.info(f"[ORCHESTRATOR] Intenção detectada: {category.upper()}")

    if category == "tracking":
        chain = get_tracking_chain()
    elif category == "analytics":
        chain = get_analytics_chain()
    else:
        chain = get_chat_chain()
    
    res = chain.invoke(inputs)
    
    # Consolidação
    final_obj = res
    generated_sql = None

    if isinstance(res, dict):
        if "sql" in res: generated_sql = res["sql"]
        if "final_response" in res: final_obj = res["final_response"]
    
    # Garante dict
    response_dict = final_obj if isinstance(final_obj, dict) else {"type": "text", "content": str(final_obj)}

    if generated_sql and isinstance(response_dict, dict):
        clean_sql = str(generated_sql).replace("```sql", "").replace("```", "").strip()
        response_dict["sql"] = clean_sql

    # LOG: Saída Final para o Frontend
    logger.info(f"\n<<< [ORCHESTRATOR] SAÍDA FINAL (PARA O FRONT):\n{json.dumps(response_dict, indent=2, ensure_ascii=False)}\n")

    return response_dict

def get_orchestrator_chain():
    router = get_router_chain()
    return (
        {
            "question": lambda x: x["question"],
            "chat_history": lambda x: x.get("chat_history", ""),
            "category": router
        }
        | RunnableLambda(route_request)
    )