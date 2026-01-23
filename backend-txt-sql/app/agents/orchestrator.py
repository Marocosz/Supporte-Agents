import logging
import re
import json
import time 
from langchain_core.runnables import RunnableLambda
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.core.llm import get_answer_llm
from app.agents.router_agent import get_router_chain
from app.agents.tracking_agent import get_tracking_chain
from app.agents.analytics_agent import get_analytics_chain

logger = logging.getLogger(__name__)

# --- CORES PARA LOG (ANSI) ---
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Mensagem padrão de boas-vindas (Centralizada para consistência)
WELCOME_MESSAGE = "Olá! Sou seu assistente de BI Logístico. Posso gerar gráficos e relatórios sobre suas notas, pedidos e filiais. Como posso ajudar?"

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

# --- Funções Auxiliares de Limpeza ---

def clean_chat_history(history: str) -> str:
    """
    Remove ruídos do histórico, como a mensagem de boas-vindas repetida,
    para que a IA foque apenas na conversa real.
    """
    if not history:
        return ""
    # Remove a mensagem de boas-vindas se ela aparecer no histórico
    cleaned = history.replace(WELCOME_MESSAGE, "")
    return cleaned.strip()

# --- Lógica de Orquestração ---

def route_request(inputs):
    start_total = time.time() # <--- INÍCIO CRONÔMETRO

    # 1. Short-Circuit: Verificação de Boas-Vindas (Latência Zero)
    question = inputs.get("question", "").strip().lower()
    greetings = ["start", "ola", "olá", "oi", "bom dia", "boa tarde", "inicio", "começar"]
    
    if not question or question in greetings:
        logger.info(f"\n{CYAN}{BOLD}>>> [ORCHESTRATOR] START/SAUDAÇÃO DETECTADO (BYPASS IA){RESET}")
        return {
            "type": "text",
            "content": WELCOME_MESSAGE,
            "server_execution_time": 0.0
        }

    # 2. Higienização do Input
    raw_history = inputs.get("chat_history", "")
    inputs["chat_history"] = clean_chat_history(raw_history)

    # LOG: Entrada do Orchestrator
    print("\n") # Quebra de linha inicial para limpar
    logger.info(f"{CYAN}================================================================================{RESET}")
    logger.info(f"{CYAN}{BOLD}>>> [ORCHESTRATOR] NOVA REQUISIÇÃO INICIADA{RESET}")
    logger.info(f"{GREEN}{BOLD}INPUTS RECEBIDOS (LIMPOS):{RESET}\n{json.dumps(inputs, indent=2, ensure_ascii=False)}")

    # 3. Roteamento Inteligente
    category = inputs["category"]
    logger.info(f"{CYAN}[ORCHESTRATOR] Intenção detectada: {BOLD}{category.upper()}{RESET}")

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

    end_total = time.time() # <--- FIM CRONÔMETRO
    total_duration = end_total - start_total
    
    # Adicionamos o tempo total no objeto de resposta (útil para debug no front se quiser)
    response_dict["server_execution_time"] = round(total_duration, 4)

    # LOG: Saída Final
    logger.info(f"{CYAN}--------------------------------------------------------------------------------{RESET}")
    logger.info(f"{GREEN}{BOLD}<<< [ORCHESTRATOR] SAÍDA FINAL (PARA O FRONT):{RESET}\n{json.dumps(response_dict, indent=2, ensure_ascii=False)}")
    logger.info(f"{MAGENTA}{BOLD}⏱️  TEMPO TOTAL DA REQUISIÇÃO: {total_duration:.4f}s{RESET}")
    logger.info(f"{CYAN}================================================================================{RESET}\n")

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