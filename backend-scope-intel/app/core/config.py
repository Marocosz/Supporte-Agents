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
    QDRANT_COLLECTION_PREFIX: str = "chamados_v1"
    
    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
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