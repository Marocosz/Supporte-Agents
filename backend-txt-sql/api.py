# api.py
import logging
import time
import uuid
from fastapi import FastAPI, Header # <--- Importado Header
from fastapi.middleware.cors import CORSMiddleware

# Imports da Aplicação
from app.services.orchestrator import Orchestrator
from app.api import dashboard
from app.core.schemas import ChatRequest, ChatResponse

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Inicialização da App
app = FastAPI(
    title="Supporte BI AI - Enterprise Backend",
    description="API Orquestrada com Arquitetura Hub-and-Spoke",
    version="2.2"
)

# Configura CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas de Dashboard (KPIs rápidos)
app.include_router(dashboard.router, prefix="/api/dashboard")

# --- Endpoint de Chat ---

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    # ALTERAÇÃO AQUI: Header X-User-ID opcional (default admin)
    x_user_id: str = Header(default="admin", alias="X-User-ID") 
):
    """
    Endpoint principal.
    Recebe a pergunta -> Passa para o Orchestrator -> Retorna resposta estruturada e validada.
    """
    start_time = time.time()
    
    # 1. Gestão de Sessão
    session_id = request.session_id or str(uuid.uuid4())
    logger.info(f"📨 [API] Nova requisição | Sessão: {session_id[:8]} | User: {x_user_id} | Pergunta: '{request.question}'")

    try:
        # 2. Execução da Pipeline
        result = Orchestrator.run_pipeline(
            session_id=session_id,
            question=request.question,
            user_key=x_user_id.lower() # Passamos a chave do usuário para o Mock de Segurança
        )

        # 3. Formatação Final
        total_duration = time.time() - start_time
        
        # Montamos um dicionário que o Pydantic (ChatResponse) irá validar e serializar
        response_data = {
            "type": result.get("type", "text"),
            "content": result.get("content", ""),
            "session_id": session_id,
            "query": request.question,
            "response_time": f"{total_duration:.2f}",
            "server_execution_time": result.get("execution_time", 0),
            
            # Campos opcionais (DataResponse)
            "sql": result.get("sql"),
            "data": result.get("data"),
            "chart_suggestion": result.get("chart_suggestion")
        }

        logger.info(f"✅ [API] Resposta enviada em {total_duration:.2f}s (Tipo: {response_data['type']})")
        return response_data

    except Exception as e:
        logger.critical(f"🔥 [API CRITICAL ERROR] {e}", exc_info=True)
        # Fallback de erro compatível com ErrorResponse
        return {
            "type": "error",
            "content": "Ocorreu um erro interno crítico no servidor.",
            "session_id": session_id,
            "query": request.question,
            "response_time": f"{time.time() - start_time:.2f}",
            "server_execution_time": 0.0,
            "debug_info": str(e)
        }

@app.get("/")
def read_root():
    return {"status": "online", "system": "Supporte BI Enterprise v2.2", "security_guard": "active"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)