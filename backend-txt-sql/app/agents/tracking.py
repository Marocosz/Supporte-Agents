# app/agents/tracking.py
import logging
import json
import re
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from app.core.config import settings
from app.core.database import get_compact_db_schema
from app.prompts.tracking_prompts import TRACKING_TEMPLATE
# Importação do Schema para validação
from app.core.schemas import AgentSQLOutput

logger = logging.getLogger(__name__)

def parse_json_output(text: str) -> dict:
    """Remove markdown ```json ... ``` se o LLM colocar."""
    clean = re.sub(r"```json\s*|\s*```", "", text, flags=re.IGNORECASE).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        logger.error(f"Falha ao parsear JSON do agente: {text}")
        return {"sql": "", "thought_process": "Falha no parse JSON"} # Fallback

def get_tracking_agent():
    """Retorna a chain do Tracking Agent."""
    llm = ChatOpenAI(
        model=settings.MODEL_SPECIALIST, # Usa o modelo mais inteligente (GPT-4o)
        temperature=0.0, # Zero criatividade, pura lógica
        api_key=settings.OPENAI_API_KEY
    )
    
    chain = TRACKING_TEMPLATE | llm | StrOutputParser()
    return chain

def generate_tracking_sql(question: str) -> dict:
    """Gera o SQL candidato para uma pergunta de rastreamento."""
    try:
        schema = get_compact_db_schema()
        chain = get_tracking_agent()
        
        logger.info(f"🚚 [TRACKING] Gerando SQL para: '{question}'")
        raw_result = chain.invoke({"schema": schema, "question": question})
        
        # 1. Parseia string para dict
        parsed = parse_json_output(raw_result)
        
        # 2. Validação Pydantic
        # Garante que os campos thought_process e sql existem.
        # Se faltar campo, o Pydantic levanta erro e vai para o except.
        validated_output = AgentSQLOutput(**parsed)
        
        # 3. Retorna como dict para o Orchestrator
        return validated_output.model_dump()
        
    except Exception as e:
        logger.error(f"Erro no Tracking Agent: {e}")
        raise