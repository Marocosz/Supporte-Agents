# =============================================================================
# ARQUIVO DE CONFIGURAÇÃO CENTRALIZADA (SETTINGS)
#
# Este arquivo funciona como o "painel de controle" da nossa aplicação.
# Ele é responsável por carregar, validar e centralizar todas as 
# configurações externas, como chaves de API e credenciais de banco de dados,
# a partir do arquivo .env.
# =============================================================================

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Gerencia as configurações da aplicação, carregando variáveis do arquivo .env.
    """
    
    # Configura como o Pydantic deve se comportar ao carregar as configurações.
    model_config = SettingsConfigDict(
        env_file='.env', 
        env_file_encoding='utf-8',
        extra='ignore'
    )

    # --- Definição dos Atributos de Configuração ---

    # Seletor de Provedor de IA (padrão: openai)
    LLM_PROVIDER: str = "openai"
    
    # Credenciais
    GROQ_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None

    # --- ESTRATÉGIA DE MODELOS (ENTERPRISE TIER) ---
    # Definimos aqui explicitamente qual modelo usar para cada "papel" na arquitetura.
    
    # Router: Rápido e barato para classificação de intenção
    MODEL_ROUTER: str = "gpt-4o-mini" 
    
    # Specialists (Tracking/Analytics): Inteligente para gerar SQL complexo
    MODEL_SPECIALIST: str = "gpt-4o" 
    
    # Fixer: Raciocínio forte para corrigir erros de sintaxe (Self-Healing)
    MODEL_FIXER: str = "gpt-4o"

    # Librarian: Modelo equilibrado para explicar conceitos
    MODEL_LIBRARIAN: str = "gpt-4o-mini"

    # (Legado/Compatibilidade) Configurações antigas mantidas se necessário
    GROQ_SQL_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_ANSWER_MODEL: str = "llama-3.1-8b-instant"

    # Credenciais do Banco de Dados
    DB_HOST: str
    DB_NAME: str
    DB_USER: str
    DB_PASS: str
    DB_PORT: int = 5432

    # --- Propriedade Computada ---
    @property
    def DATABASE_URI(self) -> str:
        """Gera a URI de conexão para o SQLAlchemy/LangChain."""
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

# --- Instanciação do Objeto de Configurações ---
settings = Settings()