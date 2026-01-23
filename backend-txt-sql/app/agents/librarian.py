# app/agents/librarian.py
import logging
import json
import re
from typing import List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.core.config import settings
# Importação do Schema Pydantic
from app.core.schemas import LibrarianOutput

logger = logging.getLogger(__name__)

# --- DICIONÁRIO DE REGRAS DE NEGÓCIO ---
BUSINESS_RULES = """
1. STATUS 'BLOQUEADO': Significa que há pendência financeira ou divergência no cadastro. O cliente deve contatar o financeiro.
2. STATUS 'ACOLHIDO': O pedido entrou no sistema mas ainda não foi separado.
3. STATUS 'EM SEPARAÇÃO': O pedido está no armazém sendo coletado. Não pode mais ser cancelado automaticamente.
4. STATUS 'EXPEDIDO': A nota fiscal foi emitida e a carga entregue à transportadora.
5. PRAZO DE ENTREGA: O prazo padrão é de 3 a 5 dias úteis após a expedição.
6. HORÁRIO DE CORTE: Pedidos feitos até as 14h são processados no mesmo dia.
"""

# Prompt atualizado para exigir JSON estruturado conforme o Schema LibrarianOutput
LIBRARIAN_TEMPLATE = """
Você é o Guardião do Conhecimento da Empresa.
Responda à dúvida do usuário baseando-se EXCLUSIVAMENTE nas regras abaixo.

--- REGRAS E DEFINIÇÕES ---
{rules}

--- PERGUNTA ---
{question}

--- FORMATO DE SAÍDA (OBRIGATÓRIO) ---
Responda APENAS um JSON válido seguindo exatamente esta estrutura:
{{
    "thought_process": "Analise a pergunta e encontre a regra correspondente.",
    "used_rules": ["Regra X", "Regra Y"],
    "answer": "Sua resposta final, polida e direta em português."
}}

Se a resposta não estiver nas regras, o campo "answer" deve ser: "Desculpe, essa informação não consta nas minhas regras de negócio."
"""

def parse_json_output(text: str) -> dict:
    """Remove markdown e converte para dict."""
    clean = re.sub(r"```json\s*|\s*```", "", text, flags=re.IGNORECASE).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        logger.error(f"Falha JSON Librarian: {text}")
        # Fallback se o modelo falhar em gerar JSON
        return {
            "thought_process": "Erro de parse no JSON",
            "used_rules": [],
            "answer": text # Tenta devolver o texto cru como resposta
        }

def consult_librarian(question: str) -> str:
    """Responde dúvidas conceituais usando validação Pydantic."""
    try:
        prompt = PromptTemplate.from_template(LIBRARIAN_TEMPLATE)
        
        llm = ChatOpenAI(
            model=settings.MODEL_LIBRARIAN, 
            temperature=0.1,
            api_key=settings.OPENAI_API_KEY
        )
        
        chain = prompt | llm | StrOutputParser()
        
        logger.info(f"📚 [LIBRARIAN] Consultando regras para: '{question}'")
        raw_result = chain.invoke({"rules": BUSINESS_RULES, "question": question})
        
        # 1. Parse JSON
        parsed = parse_json_output(raw_result)
        
        # 2. Validação Pydantic
        # Garante que os campos "answer", "used_rules" e "thought_process" existem
        validated_output = LibrarianOutput(**parsed)
        
        # Log para auditoria (mostra quais regras ele usou)
        logger.info(f"   📜 Regras citadas: {validated_output.used_rules}")
        
        # Retorna apenas a resposta textual para o usuário (pois o Orchestrator espera str)
        return validated_output.answer
        
    except Exception as e:
        logger.error(f"Erro Librarian: {e}")
        return "Desculpe, não consegui consultar as regras de negócio no momento."