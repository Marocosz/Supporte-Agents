# =============================================================================
# ARQUIVO DE CRIAÇÃO DOS LLMs (FÁBRICA DE MODELOS)
#
# O propósito deste arquivo é centralizar e abstrair a criação das instâncias
# dos modelos de linguagem (LLMs). Ao invés de configurar o ChatGroq em vários
# lugares, criamos funções "fábrica" que retornam um modelo já configurado.
# =============================================================================

# --- Bloco de Importações ---
from langchain_groq import ChatGroq
from .config import settings

def get_llm() -> ChatGroq:
    """
    Retorna uma instância configurada do LLM da Groq para a tarefa pesada de
    geração de SQL.
    """
    # Cria e retorna um objeto ChatGroq pronto para ser usado.
    return ChatGroq(
        model_name=settings.GROQ_SQL_MODEL,
        api_key=settings.GROQ_API_KEY,
        
        # O parâmetro 'temperature' controla a "criatividade" do modelo.
        # Um valor de 0.0 torna a saída o mais determinística e previsível possível.
        temperature=0.0
    )

def get_answer_llm() -> ChatGroq:
    """
    Retorna uma instância configurada do LLM da Groq para a tarefa mais simples de
    gerar respostas amigáveis em linguagem natural.
    """
    # Cria e retorna outro objeto ChatGroq, mas com uma configuração diferente.
    return ChatGroq(
        model_name=settings.GROQ_ANSWER_MODEL,
        api_key=settings.GROQ_API_KEY,
        
        # frases mais fluidas e naturais, sem se tornar aleatório ou imprevisível.
        temperature=0.3
    )