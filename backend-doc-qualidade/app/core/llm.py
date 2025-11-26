"""
MÓDULO: app/core/llm.py - FÁBRICA DE MODELOS DE LINGUAGEM (LLM Factory)

FUNÇÃO:
Este módulo implementa o padrão *Factory* para inicializar e fornecer instâncias
de Modelos de Linguagem Grande (LLMs) para os Agentes de IA. Ele centraliza a
lógica de configuração, permitindo que a aplicação alterne facilmente entre
diferentes provedores (Google, Groq, etc.) e configure dinamicamente
parâmetros cruciais como a *Temperatura*.

ARQUITETURA:
1. **Funções Específicas (`get_llm_google`, `get_llm_groq`):** Cada provedor
   possui uma função dedicada para inicializar seu respectivo wrapper LangChain
   (`ChatGoogleGenerativeAI`, `ChatGroq`), utilizando as chaves e modelos
   definidos em `settings.py`.
2. **Função Fábrica (`get_llm`):** Atua como o ponto de decisão, lendo a variável
   `settings.LLM_PROVIDER` para determinar qual função específica de inicialização
   chamar. Isso permite que a escolha do LLM seja feita através de uma variável
   de ambiente, sem alterar o código do Agente.
3. **Controle de Temperatura:** Permite que o agente solicitante defina um valor
   de `temperature` específico, que é vital para controlar a criatividade
   (alta temperatura) ou o determinismo/fidelidade (baixa temperatura) do LLM.

FLUXO DE USO:
Os Agentes de IA chamam `get_llm()` (ou `get_llm(temperature=X)`) e recebem
uma instância pronta do LLM, abstraindo a complexidade de autenticação e
configuração.
"""
import logging
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
# Importa o contrato base que todos os modelos de chat devem seguir
from langchain_core.language_models.chat_models import BaseChatModel

# Importa nossas configurações (variáveis de ambiente)
from app.core.config import settings

logger = logging.getLogger(__name__)

def get_llm_google(temperature: Optional[float] = None) -> BaseChatModel:
    """
    Inicializa e retorna o LLM do Google (Gemini), utilizando o wrapper LangChain.
    """
    # Define a temperatura final: usa o valor passado ou o padrão (0.3)
    final_temp = temperature if temperature is not None else 0.3
    
    logger.info(f"Inicializando LLM: Google (Modelo: {settings.GOOGLE_LLM_MODEL}, Temp: {final_temp})")
    
    return ChatGoogleGenerativeAI(
        model=settings.GOOGLE_LLM_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=final_temp,
        # Importante para garantir que System Prompts sejam corretamente interpretados
        convert_system_message_to_human=True 
    )

def get_llm_groq(temperature: Optional[float] = None) -> BaseChatModel:
    """
    Inicializa e retorna o LLM da Groq (ex: Llama 3), utilizando o wrapper LangChain.
    """
    # Define a temperatura final: usa o valor passado ou o padrão (0.3)
    final_temp = temperature if temperature is not None else 0.3
    
    logger.info(f"Inicializando LLM: Groq (Modelo: {settings.GROQ_LLM_MODEL}, Temp: {final_temp})")
    
    return ChatGroq(
        model_name=settings.GROQ_LLM_MODEL,
        groq_api_key=settings.GROQ_API_KEY,
        temperature=final_temp
    )

def get_llm(temperature: Optional[float] = None) -> BaseChatModel:
    """
    Função "Fábrica" principal. Retorna a instância do LLM configurado
    em LLM_PROVIDER.
    
    Args:
        temperature (float, optional): Sobrescreve a temperatura padrão. 
                                        Vital para agentes que precisam de mais 
                                        criatividade (Writer) ou determinismo (Finalizer).
                                        
    Returns:
        BaseChatModel: Uma instância do modelo de linguagem configurado.
    """
    provider = settings.LLM_PROVIDER.lower()
    
    # Roteamento baseado na variável de ambiente
    if provider == "google":
        return get_llm_google(temperature)
    elif provider == "groq":
        return get_llm_groq(temperature)
    else:
        # Fallback de segurança se o provedor não for reconhecido
        logger.error(f"Provedor LLM desconhecido: '{provider}'. "
                     f"Verifique seu .env. Usando 'google' como fallback.")
        return get_llm_google(temperature)

# --- Instância Global Padrão ---
# Instância de LLM inicializada com a temperatura padrão, para uso imediato.
# Agentes mais antigos podem importar esta variável diretamente.
llm = get_llm()