"""
MÓDULO: app/core/config.py - CONFIGURAÇÃO CENTRAL DA APLICAÇÃO (PYDANTIC SETTINGS)

FUNÇÃO:
Define a classe `Settings`, que é a única fonte de verdade para todas as
configurações e variáveis de ambiente da aplicação. Utiliza a biblioteca
`pydantic-settings` para carregar e validar as variáveis do arquivo `.env`
de forma segura e estrita.

ARQUITETURA:
- **`BaseSettings`:** Herda de `BaseSettings` (Pydantic v2), garantindo que
  o carregamento das variáveis ocorra automaticamente.
- **`SettingsConfigDict`:** Configura o Pydantic para buscar o arquivo `.env`
  na raiz do projeto (`BASE_DIR`).
- **Validação Estrita:** O design é intencionalmente *strict* (estrito):
  não há valores padrão para a maioria das variáveis críticas (API_HOST,
  API_KEYs). Se uma variável essencial estiver faltando no `.env`, a aplicação
  falhará no momento da inicialização (`raise`), garantindo que o ambiente
  esteja configurado corretamente.
- **`@computed_field`:** Cria propriedades de caminho (Path) que são geradas
  dinamicamente a partir de outras variáveis, fornecendo caminhos absolutos
  e fáceis de usar (e.g., `settings.ASSETS_PATH`) para o restante da aplicação.

FLUXO DE USO:
Outros módulos (`main.py`, `llm.py`, `docx_generator.py`) importam a instância
`settings` para acessar qualquer configuração de forma tipada e segura.
"""
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field
from pathlib import Path

# Encontra o diretório raiz do projeto (a pasta 'ai-agent-Qualidade-supp').
# Essencial para localizar o arquivo .env e construir caminhos absolutos.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """
    Carrega e valida as variáveis de ambiente do arquivo .env usando Pydantic.
    Esta classe não fornece valores padrão para variáveis críticas (strict mode).
    """
    
    # 1. Configuração do Pydantic v2 para carregar o .env
    model_config = SettingsConfigDict(
        # Especifica o caminho absoluto do arquivo .env
        env_file = BASE_DIR / ".env",
        env_file_encoding = "utf-8",
        # Ignora variáveis que existam no .env mas não nesta classe
        extra = 'ignore' 
    )
    
    # --- Configurações da API (Obrigatórias) ---
    API_HOST: str
    API_PORT: int
    
    # --- Nomes dos Diretórios (Obrigatórios, usados para criar Paths Computados) ---
    ASSETS_DIR: str  
    OUTPUTS_DIR: str
    
    # --- Configurações do LLM (Obrigatórias) ---
    GOOGLE_API_KEY: str
    GROQ_API_KEY: str
    LLM_PROVIDER: str       # Qual provedor usar ("google" ou "groq")
    GOOGLE_LLM_MODEL: str   # Nome do modelo Google (ex: gemini-2.5-flash)
    GROQ_LLM_MODEL: str     # Nome do modelo Groq (ex: llama3-8b-8192)
    
    # --- Configuração de Teste (Com valor padrão, se não estiver no .env) ---
    USE_MOCK_AGENTS: bool = False # Controla se agentes de mock (teste) ou de produção (IA) serão usados.

    # --- Propriedades Computadas (Caminhos Absolutos) ---
    # Estes campos são gerados dinamicamente e são apenas de leitura.
    
    @computed_field
    @property
    def ASSETS_PATH(self) -> Path:
        """
        Retorna o caminho absoluto (Pathlib) para a pasta de assets (app/assets).
        Essencial para carregar a logo e outros recursos.
        """
        return BASE_DIR / self.ASSETS_DIR

    @computed_field
    @property
    def OUTPUTS_PATH(self) -> Path:
        """
        Retorna o caminho absoluto (Pathlib) para a pasta de saídas (app/outputs).
        Essencial para salvar os arquivos .docx gerados.
        """
        return BASE_DIR / self.OUTPUTS_DIR

# Tenta carregar as configurações na instância global 'settings'.
# Este bloco garante que o aplicativo falhe de forma controlada se o .env for inválido ou faltar.
try:
    settings = Settings()
except Exception as e:
    logger.error(f"ERRO CRÍTICO: Não foi possível carregar as configurações do .env.")
    logger.error(f"Verifique se seu arquivo .env em {BASE_DIR / '.env'} existe e tem TODAS as variáveis necessárias.")
    logger.error(f"Erro de Validação: {e}")
    # Relança o erro para impedir a inicialização do app.
    # Se o app for iniciado sem as chaves, ele falharia em tempo de execução de forma pior.
    raise