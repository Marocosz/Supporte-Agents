# api.py
import logging
import time
import uuid
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Importa o Cérebro da Nova Arquitetura
from app.services.orchestrator import Orchestrator
# Importa o módulo de dashboard (KPIs estáticos) - Mantido para não quebrar a tela de gráficos
from app.api import dashboard

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
    description="API Orquestrada com Arquitetura Hub-and-Spoke (Router -> Specialists)",
    version="2.1"
)

# Configura CORS (Permite que o Frontend React acesse)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Em produção, restrinja para o domínio do front
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas de Dashboard (KPIs rápidos que não dependem da IA)
app.include_router(dashboard.router, prefix="/api/dashboard")

# --- Modelos de Entrada (DTOs) ---

class ChatRequest(BaseModel):
    question: str
    session_id: str | None = None
    # Histórico opcional (O Orchestrator gerencia contexto internamente agora, 
    # mas mantemos o campo para compatibilidade)
    history: List[Dict[str, str]] = [] 

# --- Endpoint de Chat (O Coração do Sistema) ---

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Endpoint principal.
    Recebe a pergunta -> Passa para o Orchestrator -> Retorna resposta estruturada.
    """
    start_time = time.time()
    
    # 1. Gestão de Sessão
    session_id = request.session_id or str(uuid.uuid4())
    logger.info(f"📨 [API] Nova requisição | Sessão: {session_id[:8]} | Pergunta: '{request.question}'")

    try:
        # 2. Execução da Pipeline (Onde a mágica acontece)
        # O Orchestrator cuida de tudo: Routing, SQL, Segurança, RAG.
        result = Orchestrator.run_pipeline(
            session_id=session_id,
            question=request.question
        )

        # 3. Formatação Final para o Frontend
        # Garantimos que os campos técnicos estejam presentes para debug
        total_duration = time.time() - start_time
        
        response = {
            "type": result.get("type", "text"),
            "content": result.get("content", ""),
            "session_id": session_id,
            "query": request.question,
            # Metadados técnicos
            "sql": result.get("sql"),          # Só existe se for Tracking/Analytics
            "data": result.get("data"),        # Dados brutos para gráficos
            "category": result.get("category"), # TRACKING, ANALYTICS, etc.
            "response_time": f"{total_duration:.2f}",
            "server_execution_time": result.get("execution_time", 0)
        }

        logger.info(f"✅ [API] Resposta enviada em {total_duration:.2f}s (Tipo: {response['type']})")
        return response

    except Exception as e:
        logger.critical(f"🔥 [API CRITICAL ERROR] {e}", exc_info=True)
        # Fallback seguro: Nunca deixe o frontend sem resposta
        return {
            "type": "error",
            "content": "Ocorreu um erro interno crítico no servidor. Por favor, tente novamente em instantes.",
            "session_id": session_id,
            "response_time": f"{time.time() - start_time:.2f}"
        }

@app.get("/")
def read_root():
    return {"status": "online", "system": "Supporte BI Enterprise v2.1", "security_guard": "active"}

# Permite rodar como script: python api.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)