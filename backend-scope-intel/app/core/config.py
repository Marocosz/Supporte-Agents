import os
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    PROJECT_NAME: str = "Ticket Intel AI (Batch)"
    
    # Banco de Dados (MySQL Leitura)
    DATABASE_URL: str
    
    # Qdrant (Memória de Vetores)
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION_PREFIX: str = "chamados_v1"
    
    # OpenAI
    OPENAI_API_KEY: str
    
    # Onde vamos salvar os JSONs de resultado?
    OUTPUT_DIR: str = "data_output" 
    
    FLUIG_TABLE_NAME: str = "ml001292"

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()