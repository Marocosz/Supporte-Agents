# app/agents/fixer.py
import logging
import json
import re
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from app.core.config import settings
from app.core.database import get_compact_db_schema
from app.prompts.tracking_prompts import FIXER_TEMPLATE
# Importação do Schema
from app.core.schemas import AgentSQLOutput

logger = logging.getLogger(__name__)

def parse_json_output(text: str) -> dict:
    clean = re.sub(r"```json\s*|\s*```", "", text, flags=re.IGNORECASE).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        return {"fixed_sql": text} # Tenta usar o texto cru como fallback

def fix_sql_query(broken_sql: str, error_message: str) -> str:
    """
    Chama o LLM para corrigir o SQL baseado no erro do Postgres.
    """
    try:
        llm = ChatOpenAI(
            model=settings.MODEL_FIXER,
            temperature=0.0,
            api_key=settings.OPENAI_API_KEY
        )
        
        schema = get_compact_db_schema()
        chain = FIXER_TEMPLATE | llm | StrOutputParser()
        
        logger.warning(f"🔧 [FIXER] Tentando corrigir SQL. Erro: {str(error_message)[:100]}...")
        
        raw_result = chain.invoke({
            "schema": schema, 
            "broken_sql": broken_sql, 
            "error_message": error_message
        })
        
        parsed = parse_json_output(raw_result)
        
        # --- Validação e Mapeamento Pydantic ---
        # O prompt do Fixer retorna chaves "correction_logic" e "fixed_sql".
        # O Schema AgentSQLOutput espera "thought_process" e "sql".
        # Fazemos o mapeamento manual aqui para garantir conformidade.
        
        mapped_data = {
            "thought_process": parsed.get("correction_logic", "Correção automática"),
            "sql": parsed.get("fixed_sql", "")
        }
        
        # Valida com Pydantic (garante string não nula)
        validated_output = AgentSQLOutput(**mapped_data)
        
        logger.info(f"✅ [FIXER] SQL Corrigido: {validated_output.sql}")
        return validated_output.sql
        
    except Exception as e:
        logger.error(f"Fixer falhou: {e}")
        return broken_sql # Retorna o original se falhar, para abortar depois