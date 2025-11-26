"""
MÓDULO: app/api/router.py - ROTEADOR PRINCIPAL DA API (FASTAPI)

FUNÇÃO:
Define o `api_router` principal, que atua como o ponto de agregação para
todas as rotas e endpoints definidos na aplicação. Ele organiza a API em
módulos lógicos, aplicando prefixos de URL e tags de documentação para
manter a estrutura limpa e o Swagger UI (documentação interativa da API)
organizado.

ARQUITETURA:
Implementa o padrão de agregação de roteadores do FastAPI:

1. **Roteador Principal:** `api_router = APIRouter()`
2. **Inclusão de Módulos:** Inclui roteadores menores (`http_session.router`,
   `ws_chat.router`, `download.router`), aplicando:
   - **`prefix`:** Para definir o caminho base de cada grupo de rotas (ex: `/v1/session`).
   - **`tags`:** Para categorizar e agrupar as rotas na documentação (Swagger/OpenAPI).

FLUXO DE DADOS:
Este roteador é importado pelo `app/main.py`, que o inclui na instância
principal do FastAPI.
"""
from fastapi import APIRouter

# Importa os módulos de endpoint que contêm as rotas específicas
from app.api.endpoints import http_session, ws_chat
from app.api.endpoints import download

# Cria o roteador principal da API
api_router = APIRouter()

# --- 1. Rotas HTTP (Gerenciamento de Sessão) ---
# Endpoint: POST /v1/session/start
api_router.include_router(
    http_session.router, 
    prefix="/v1/session", 
    tags=["1. Gerenciamento de Sessão (HTTP)"]
)

# --- 2. Rotas WebSocket (Chat Interativo) ---
# Endpoint: WS /v1/session/{session_id}
api_router.include_router(
    ws_chat.router, 
    prefix="/v1/session", 
    tags=["2. Chat de Geração (WebSocket)"]
)

# --- 3. Rotas HTTP (Download de Arquivos) ---
# Endpoint: GET /v1/download/{file_name}
api_router.include_router(
    download.router,
    prefix="/v1", # Prefixo simples para download na raiz da v1
    tags=["3. Download de Arquivos"]
)