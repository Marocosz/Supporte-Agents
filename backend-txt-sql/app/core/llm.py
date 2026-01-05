# =============================================================================
# ARQUIVO DE CRIAÇÃO DOS LLMs (FÁBRICA DE MODELOS)
#
# O propósito deste arquivo é centralizar e abstrair a criação das instâncias
# dos modelos de linguagem (LLMs). Ao invés de configurar o ChatGroq em vários
# lugares, criamos funções "fábrica" que retornam um modelo já configurado.
# =============================================================================

# --- Bloco de Importações ---
from langchain_core.language_models import BaseChatModel
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from .config import settings

def _create_llm_instance(model_name: str, temperature: float) -> BaseChatModel:
    """
    Função auxiliar interna que verifica o LLM_PROVIDER configurado e retorna
    a instância correta (Groq, OpenAI ou Gemini).
    """
    provider = settings.LLM_PROVIDER.lower().strip()

    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("LLM_PROVIDER é 'openai', mas OPENAI_API_KEY não está definida.")
        return ChatOpenAI(
            model_name=model_name,
            api_key=settings.OPENAI_API_KEY,
            temperature=temperature
        )
    
    elif provider == "gemini":
        if not settings.GOOGLE_API_KEY:
            raise ValueError("LLM_PROVIDER é 'gemini', mas GOOGLE_API_KEY não está definida.")
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=temperature,
            convert_system_message_to_human=True # Necessário para alguns casos do Gemini
        )
    
    # Default para Groq
    else:
        if not settings.GROQ_API_KEY:
            raise ValueError("LLM_PROVIDER é 'groq', mas GROQ_API_KEY não está definida.")
        return ChatGroq(
            model_name=model_name,
            api_key=settings.GROQ_API_KEY,
            temperature=temperature
        )

def get_llm() -> BaseChatModel:
    """
    Retorna uma instância configurada do LLM escolhido para a tarefa pesada de
    geração de SQL.
    """
    # Define qual modelo usar baseado no provedor
    provider = settings.LLM_PROVIDER.lower().strip()
    
    if provider == "openai":
        model = settings.OPENAI_SQL_MODEL
    elif provider == "gemini":
        model = settings.GEMINI_SQL_MODEL
    else:
        model = settings.GROQ_SQL_MODEL

    # Cria e retorna um objeto Chat pronto para ser usado.
    # O parâmetro 'temperature' controla a "criatividade" do modelo.
    # Um valor de 0.0 torna a saída o mais determinística e previsível possível.
    return _create_llm_instance(model_name=model, temperature=0.0)

def get_answer_llm() -> BaseChatModel:
    """
    Retorna uma instância configurada do LLM escolhido para a tarefa mais simples de
    gerar respostas amigáveis em linguagem natural.
    """
    # Define qual modelo usar baseado no provedor
    provider = settings.LLM_PROVIDER.lower().strip()
    
    if provider == "openai":
        model = settings.OPENAI_ANSWER_MODEL
    elif provider == "gemini":
        model = settings.GEMINI_ANSWER_MODEL
    else:
        model = settings.GROQ_ANSWER_MODEL

    # Cria e retorna outro objeto Chat, mas com uma configuração diferente.
    # frases mais fluidas e naturais, sem se tornar aleatório ou imprevisível.
    return _create_llm_instance(model_name=model, temperature=0.3)