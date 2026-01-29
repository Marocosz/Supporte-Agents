# app/agents/router.py
import logging
import json
import re
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.core.config import settings
# Importação do Schema Pydantic
from app.core.schemas import RouterOutput

logger = logging.getLogger(__name__)

# Template atualizado para retornar JSON com explicação conforme Schema RouterOutput
ROUTER_TEMPLATE = """
Classifique a pergunta do usuário em EXATAMENTE UMA destas categorias:

1. TRACKING: Busca pontual de status, rastreamento, onde está, quem conferiu. (Ex: "Cadê a nota X?", "Status do pedido Y")
2. ANALYTICS: Agregações, somas, contagens, totais, rankings, métricas gerais. (Ex: "Total vendido", "Quantas notas...")
3. LISTING: Listagens de registros, busca de múltiplos itens, relatórios tabulares simples. (Ex: "Quais são as últimas 10 notas?", "Liste os pedidos de hoje")
4. KNOWLEDGE: Dúvidas conceituais, significados de termos, regras de negócio. (Ex: "O que é status bloqueado?", "Prazo de entrega")
5. CHAT: Conversa fiada, cumprimentos, agradecimentos que não exigem dados. (Ex: "Tchau", "Obrigado", "Quem é você?")

Pergunta: {question}

--- FORMATO DE SAÍDA ---
Responda APENAS um JSON válido:
{{
    "category": "TRACKING" | "ANALYTICS" | "LISTING" | "KNOWLEDGE" | "CHAT",
    "reasoning": "Breve explicação do porquê escolheu essa categoria"
}}
"""

def parse_json_output(text: str) -> dict:
    clean = re.sub(r"```json\s*|\s*```", "", text, flags=re.IGNORECASE).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        # Fallback simples se falhar o JSON: tenta achar a palavra chave no texto cru
        text_upper = text.upper()
        for cat in ["TRACKING", "ANALYTICS", "LISTING", "KNOWLEDGE", "CHAT"]:
            if cat in text_upper:
                return {"category": cat, "reasoning": "Fallback de parse (JSON inválido)"}
        return {"category": "CHAT", "reasoning": "Erro total de parse"}

def get_router_chain():
    """
    Retorna a cadeia LangChain responsável por classificar a intenção.
    """
    prompt = PromptTemplate.from_template(ROUTER_TEMPLATE)
    
    # Usamos temperature=0.0 para garantir consistência máxima
    llm = ChatOpenAI(
        model=settings.MODEL_ROUTER, 
        temperature=0.0,
        api_key=settings.OPENAI_API_KEY
    )

    chain = prompt | llm | StrOutputParser()
    return chain

def classify_intent(question: str) -> str:
    """Função wrapper para facilitar o uso no Orchestrator."""
    try:
        chain = get_router_chain()
        raw_result = chain.invoke({"question": question})
        
        # 1. Parse JSON
        parsed = parse_json_output(raw_result)
        
        # 2. Validação Pydantic
        # Garante que 'category' e 'reasoning' existem e category é válida
        validated_output = RouterOutput(**parsed)
        
        logger.info(f"🧭 [ROUTER] '{question}' -> {validated_output.category} (Motivo: {validated_output.reasoning})")
        
        # Retorna apenas a string da categoria para não quebrar a lógica do Orchestrator
        return validated_output.category
        
    except Exception as e:
        logger.error(f"Erro no Router: {e}")
        return "CHAT" # Fallback seguro