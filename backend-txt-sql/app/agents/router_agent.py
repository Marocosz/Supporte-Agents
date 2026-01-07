import logging
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from app.core.llm import get_llm
from app.prompts.specialized.router_prompts import ROUTER_PROMPT

logger = logging.getLogger(__name__)

def get_router_chain():
    """
    Cria a cadeia de Roteamento.
    Analisa a pergunta + histórico e define a categoria (tracking, analytics, chat).
    """
    
    # Parser simples que remove espaços e garante minúsculas
    def clean_category(text: str) -> str:
        cleaned = text.strip().lower()
        # Fallback de segurança se o LLM for prolixo
        if "tracking" in cleaned: return "tracking"
        if "analytics" in cleaned: return "analytics"
        if "chat" in cleaned: return "chat"
        return "chat" # Default seguro

    chain = (
        ROUTER_PROMPT
        | get_llm()
        | StrOutputParser()
        | clean_category
    )
    
    return chain