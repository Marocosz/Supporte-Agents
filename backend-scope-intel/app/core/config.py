# ==============================================================================
# ARQUIVO: app/core/config.py
#
# OBJETIVO:
#   Centralizar as variáveis de ambiente e configurações globais do sistema.
#   Usa Pydantic BaseSettings para carregar do arquivo .env com validação.
#
# PARTE DO SISTEMA:
#   Backend / Configuração
#
# RESPONSABILIDADES:
#   - Mapear chaves de API (OpenAI)
#   - Mapear credenciais de Banco de Dados
#   - Definir constantes do sistema (Modelos, Tabelas, Pastas)
#
# COMUNICAÇÃO:
#   Importado por: Quase todos os módulos do sistema.
# ==============================================================================

import os
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    PROJECT_NAME: str = "Scope Intelligence (Batch)"
    
    # Banco de Dados (MySQL Leitura)
    DATABASE_URL: str
    
    # Qdrant (Memória de Vetores)
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION_PREFIX: str = "chamados_large_v1"
    
    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-large"
    OPENAI_CHAT_MODEL: str = "gpt-5-nano"
    
    # Onde vamos salvar os JSONs de resultado?
    OUTPUT_DIR: str = "data_output" 
    
    FLUIG_TABLE_NAME: str = "ml001292"

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()