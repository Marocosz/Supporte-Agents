# app/agents/listing.py
import logging
import json
from app.core.llm import get_llm
from app.core.database import get_compact_db_schema
from app.prompts.listing_prompts import LISTING_TEMPLATE

logger = logging.getLogger(__name__)

def generate_listing_sql(question: str, security_context: str = "") -> dict:
    """
    Gera SQL para listas de registros (ex: 'últimas 10 notas').
    """
    try:
        llm = get_llm()
        schema = get_compact_db_schema()
        
        chain = LISTING_TEMPLATE | llm
        
        response = chain.invoke({
            "schema": schema,
            "question": question,
            "security_context": security_context
        })
        
        content = response.content.strip()
        
        # Limpeza de markdown se houver
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()
            
        return json.loads(content)

    except Exception as e:
        logger.error(f"Erro no Listing Agent: {e}")
        return {"sql": "", "error": str(e)}