"""
MÓDULO: app/main.py - PONTO DE ENTRADA PRINCIPAL DA APLICAÇÃO (FASTAPI)

FUNÇÃO:
Configura e inicializa a aplicação FastAPI. Este é o arquivo responsável por
configurar o servidor HTTP, o sistema de logging, o roteamento de API e,
criticamente, as políticas de Cross-Origin Resource Sharing (CORS) para
permitir que aplicações frontend (como React) se comuniquem com o backend.

ARQUITETURA:
1. **Configuração de Ambiente:** Configura o ambiente Python para garantir
   que as importações internas (`app.*`) funcionem corretamente.
2. **Instância FastAPI:** Cria a instância principal da aplicação (`app`).
3. **CORS Middleware:** Implementa a política de segurança CORSMiddleware
   para gerenciar o acesso de diferentes origens (domínios/portas).
4. **Roteamento:** Inclui o `api_router`, que agrupa todas as rotas (HTTP/WS)
   da aplicação.
5. **Execução:** Contém o bloco `if __name__ == "__main__":` para iniciar
   o servidor Uvicorn/FastAPI em modo de desenvolvimento/reload.

FLUXO DE SEGURANÇA (CORS):
- O CORSMiddleware é essencial, pois o frontend (ex: rodando em `localhost:5173`)
  e o backend (ex: rodando em `localhost:8000`) são origens diferentes.
- A configuração `allow_origins` deve listar explicitamente todos os domínios
  que são autorizados a fazer requisições à API.
- As opções `allow_credentials=True`, `allow_methods=["*"]` e `allow_headers=["*"]`
  garantem a máxima flexibilidade para o desenvolvimento.
"""
import logging
import sys
from pathlib import Path
import uvicorn
from fastapi import FastAPI
# Importação da biblioteca CORSMiddleware, essencial para comunicação frontend-backend
from fastapi.middleware.cors import CORSMiddleware

# --- Configuração de Path (Importante!) ---
# Determina o diretório base do projeto e o adiciona ao path do sistema.
# Isso garante que as importações internas (como 'from app.core.config') funcionem.
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))
# --- Fim da Configuração de Path ---

from app.api.router import api_router
from app.core.config import settings

# Configuração básica de logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - [%(levelname)s] - %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Cria a instância principal da aplicação FastAPI
app = FastAPI(
    title="SUPPORTE Qualidade Document Agent API",
    description="API para geração automática de documentos via chat interativo.",
    version="2.0.0 (Chatbot)"
)

# --- CONFIGURAÇÃO DO CORS (Cross-Origin Resource Sharing) ---
# Define quais "origens" (domínios e portas de frontend) podem conversar com esta API
origins = [
    "http://localhost:5173",  # Porta padrão do Vite (React)
    "http://localhost:5174",  # Porta alternativa comum do Vite
    "http://localhost:3000",  # Porta padrão do Create React App
    f"http://{settings.API_HOST}:{settings.API_PORT}",  # A própria API
    "http://localhost:8000",  # Porta padrão do Uvicorn (se não for o reload)
]

# Adiciona o middleware CORS à aplicação
app.add_middleware(
    CORSMiddleware,
    # ALTERAÇÃO AQUI: Mudado para ["*"] para liberar qualquer origem (IPv4, IPv6, Rede Local)
    allow_origins=["*"],        # Permite qualquer origem
    allow_credentials=True,       # Permite o uso de credenciais (cookies, auth headers)
    allow_methods=["*"],          # Permite todos os métodos HTTP (GET, POST, etc.)
    allow_headers=["*"],          # Permite todos os cabeçalhos nas requisições
)
# --- FIM DA CONFIGURAÇÃO DO CORS ---

# Inclui todas as rotas (HTTP e WS) definidas em app/api/router.py
app.include_router(api_router)

@app.get("/", include_in_schema=False)
def read_root():
    """Endpoint raiz para verificação de status e health check."""
    return {"message": "SUPPORTE Qualidade Document Agent API (v2.0 - Chatbot) está online."}

# Este bloco só é executado quando você roda `python app/main.py`
if __name__ == "__main__":
    logger.info(f"Iniciando servidor em http://{settings.API_HOST}:{settings.API_PORT}")
    logger.info(f"Lendo assets (logo) de: {settings.ASSETS_PATH}")
    logger.info(f"Salvando documentos (docx) em: {settings.OUTPUTS_PATH}")
    logger.info(f"Usando provedor LLM: {settings.LLM_PROVIDER}")

    # Garante que os diretórios de ativos e saídas existam
    settings.ASSETS_PATH.mkdir(parents=True, exist_ok=True)
    settings.OUTPUTS_PATH.mkdir(parents=True, exist_ok=True)
        
    # Inicializa o servidor Uvicorn
    uvicorn.run(
        # Especifica o módulo e a instância FastAPI para rodar
        "main:app",
        host=settings.API_HOST, 
        port=settings.API_PORT, 
        reload=True,  # Habilita o reload automático em desenvolvimento
        app_dir="app", # Define o diretório base para o reload
        # Exclui arquivos e diretórios que não devem causar um restart do servidor
        reload_excludes=["__pycache__", "*.pyc", "*.pyo", "*.log", ".git"]
    )