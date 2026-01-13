import logging
import re
import json
import time  # <--- NOVO
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser

from app.core.llm import get_llm, get_answer_llm
from app.core.database import db_instance, get_compact_db_schema
from app.core.security import apply_security_filters
from app.prompts.specialized.tracking_prompts import TRACKING_PROMPT, TRACKING_RESPONSE_PROMPT

logger = logging.getLogger(__name__)

# --- CORES PARA LOG (ANSI) ---
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

def extract_sql_from_text(text: str) -> str:
    match_markdown = re.search(r"```sql\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match_markdown: return match_markdown.group(1).strip()
    match_select = re.search(r"(SELECT\s.*)", text, re.DOTALL | re.IGNORECASE)
    if match_select:
        sql = match_select.group(1).strip()
        return sql.split(";")[0] + ";" if ";" in sql else sql
    return text.strip()

def safe_parse_json(text: str) -> dict:
    # LOG: Resposta Bruta da IA antes do processamento
    logger.info(f"\n{BLUE}{BOLD}[TRACKING AGENT] RESPOSTA BRUTA DA IA (RAW):{RESET}\n{BLUE}{text}{RESET}\n")

    text_clean = re.sub(r"```json\s*", "", text, flags=re.IGNORECASE)
    text_clean = re.sub(r"```\s*$", "", text_clean, flags=re.IGNORECASE)
    text_clean = text_clean.strip()

    match = re.search(r"(\{.*\})", text_clean, re.DOTALL)
    json_candidate = match.group(1) if match else text_clean

    try:
        return json.loads(json_candidate)
    except json.JSONDecodeError:
        logger.warning("JSON Parse Error (Tracking). Usando Fallback.")
        return {
            "type": "text",
            "content": text_clean
        }

def get_tracking_chain():
    # 1. Gerador de SQL
    sql_gen = (
        RunnablePassthrough.assign(schema=lambda _: get_compact_db_schema())
        | TRACKING_PROMPT
        | get_llm()
        | StrOutputParser()
    )

    # 2. Executor Seguro
    def execute_tracking_query(inputs):
        raw_output = inputs["sql"]
        clean_sql = extract_sql_from_text(raw_output)
        secure_sql = apply_security_filters(clean_sql)
        inputs["sql"] = clean_sql 
        
        # LOG: SQL Gerado
        logger.info(f"\n{YELLOW}{BOLD}[TRACKING AGENT] QUERY SQL FINAL:{RESET}\n{YELLOW}{secure_sql}{RESET}\n")
        
        try:
            # --- MEDIÇÃO DE TEMPO DE BANCO ---
            start_time = time.time()
            result = db_instance.run(secure_sql)
            end_time = time.time()
            db_duration = end_time - start_time
            
            logger.info(f"{MAGENTA}{BOLD}⏱️  TEMPO DE BANCO (Tracking): {db_duration:.4f}s{RESET}")
            # ---------------------------------

            # Se o resultado for string vazia ou lista vazia stringificada
            if not result or result == "[]":
                return "REGISTRO_NAO_ENCONTRADO"
            return result
        except Exception as e:
            logger.error(f"Erro Tracking: {e}")
            return f"Erro técnico: {str(e)}"

    # 3. Formatador de Resposta
    response_gen = (
        TRACKING_RESPONSE_PROMPT
        | get_answer_llm()
        | StrOutputParser()
        | RunnableLambda(safe_parse_json)
    )

    chain = (
        RunnablePassthrough.assign(sql=sql_gen)
        .assign(result=execute_tracking_query)
        .assign(final_response=response_gen)
    )
    
    return chain