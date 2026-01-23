# app/agents/analytics.py
import logging
import json
import re
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from app.core.config import settings
from app.core.database import get_compact_db_schema
from app.prompts.analytics_prompts import ANALYTICS_TEMPLATE
# Importação do Schema
from app.core.schemas import AgentSQLOutput

logger = logging.getLogger(__name__)

def parse_json_output(text: str) -> dict:
    clean = re.sub(r"```json\s*|\s*```", "", text, flags=re.IGNORECASE).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        return {"sql": "", "thought_process": "Erro JSON Analytics"}

def generate_analytics_sql(question: str) -> dict:
    """Gera SQL para agregação/BI."""
    try:
        schema = get_compact_db_schema()
        
        llm = ChatOpenAI(
            model=settings.MODEL_SPECIALIST, # Usa modelo forte (GPT-4o)
            temperature=0, 
            api_key=settings.OPENAI_API_KEY
        )
        
        chain = ANALYTICS_TEMPLATE | llm | StrOutputParser()
        
        logger.info(f"📊 [ANALYTICS] Gerando SQL para: '{question}'")
        raw_result = chain.invoke({"schema": schema, "question": question})
        
        parsed = parse_json_output(raw_result)
        
        # --- Validação Pydantic ---
        # Garante estrutura correta (sql, thought_process, chart_suggestion)
        validated_output = AgentSQLOutput(**parsed)
        
        return validated_output.model_dump()
        
    except Exception as e:
        logger.error(f"Erro Analytics: {e}")
        raise