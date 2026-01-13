import logging
import re
import json
import time # <--- NOVO
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser

from app.core.llm import get_llm, get_answer_llm
from app.core.database import db_instance, get_compact_db_schema
from app.core.security import apply_security_filters
from app.prompts.specialized.analytics_prompts import ANALYTICS_PROMPT, ANALYTICS_RESPONSE_PROMPT

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
    # LOG: Resposta Bruta da IA
    logger.info(f"\n{BLUE}{BOLD}[ANALYTICS AGENT] RESPOSTA BRUTA DA IA (RAW):{RESET}\n{BLUE}{text}{RESET}\n")

    """Limpeza agressiva de JSON com suporte a Markdown."""
    # 1. Remove blocos de markdown ```json ... ```
    text_clean = re.sub(r"```json\s*", "", text, flags=re.IGNORECASE)
    text_clean = re.sub(r"```\s*$", "", text_clean, flags=re.IGNORECASE)
    text_clean = text_clean.strip()

    # 2. Tenta achar o bloco JSON entre chaves
    match = re.search(r"(\{.*\})", text_clean, re.DOTALL)
    json_candidate = match.group(1) if match else text_clean

    try:
        return json.loads(json_candidate)
    except json.JSONDecodeError:
        logger.warning(f"JSON Parse Error. Output raw: {text_clean[:50]}...")
        # Fallback para texto
        return {
            "type": "text",
            "content": text_clean 
        }

def get_analytics_chain():
    # 1. Gerador de SQL
    sql_gen = (
        RunnablePassthrough.assign(schema=lambda _: get_compact_db_schema())
        | ANALYTICS_PROMPT
        | get_llm()
        | StrOutputParser()
    )

    # 2. Executor Seguro
    def execute_analytics_query(inputs):
        raw_output = inputs["sql"]
        clean_sql = extract_sql_from_text(raw_output)
        secure_sql = apply_security_filters(clean_sql)
        inputs["sql"] = clean_sql
        
        sql_lower = secure_sql.lower()
        if "select" in sql_lower and "limit" not in sql_lower and "count(" not in sql_lower:
             secure_sql = secure_sql.rstrip(";") + " LIMIT 20;"
        
        # LOG: SQL Final
        logger.info(f"\n{YELLOW}{BOLD}[ANALYTICS AGENT] QUERY SQL FINAL:{RESET}\n{YELLOW}{secure_sql}{RESET}\n")
        
        try:
            # --- MEDIÇÃO DE TEMPO DE BANCO ---
            start_time = time.time()
            result = db_instance.run(secure_sql)
            end_time = time.time()
            db_duration = end_time - start_time
            
            logger.info(f"{MAGENTA}{BOLD}⏱️  TEMPO DE BANCO (Analytics): {db_duration:.4f}s{RESET}")
            # ---------------------------------

            if not result or result in ["[]", "None", ""]:
                return "DADOS_INSUFICIENTES_PARA_ANALISE"
            return result
        except Exception as e:
            logger.error(f"Erro Analytics: {e}")
            return f"Erro: {str(e)}"

    # 3. Formatador Seguro
    viz_gen = (
        ANALYTICS_RESPONSE_PROMPT
        | get_answer_llm()
        | StrOutputParser()
        | RunnableLambda(safe_parse_json)
    )

    chain = (
        RunnablePassthrough.assign(sql=sql_gen)
        .assign(result=execute_analytics_query)
        .assign(final_response=viz_gen)
    )

    return chain