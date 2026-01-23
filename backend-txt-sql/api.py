# =================================================================================================
# =================================================================================================
#
#                           PONTO DE ENTRADA DA API (BACKEND) - v2.2 (OTIMIZADO)
#
# Visão Geral:
# Este arquivo conecta o servidor web (FastAPI) à nova Arquitetura Multi-Agente.
#
# Atualizações Recentes:
# - Integração com Short-Circuit do Orchestrator (zero latency para 'Oi').
# - Logs limpos (delegados para o Orchestrator).
#
# =================================================================================================
# =================================================================================================

import logging
import time
import uuid
from typing import List, Dict, Any, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- NOVOS IMPORTS DA ARQUITETURA ---
from app.agents.orchestrator import get_orchestrator_chain
# Importa o roteador que contém os endpoints do dashboard (mantido)
from app.api import dashboard

# Configuração de Logs
# (Mantido básico aqui, pois o Orchestrator cuida dos logs detalhados/coloridos)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)-25s - %(levelname)-8s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Inicialização da App
app = FastAPI(
    title="Supporte BI AI - SQL Agent",
    description="API de BI Logístico com Arquitetura Multi-Agente (Router -> Specialists)",
    version="6.5" # Bump de versão
)

# Configura CORS (Mantido para compatibilidade total)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:5173", # Vite
        "http://localhost:80",   # Nginx
        "http://localhost"
    ], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas de Dashboard (Mantidas)
app.include_router(dashboard.router, prefix="/api/dashboard")

# --- Modelos de Entrada (Request) ---

class ChatRequest(BaseModel):
    question: str
    session_id: str | None = None
    # NOVO: Recebemos o histórico do frontend para o Router tomar decisões melhores.
    # Ex: [{ "role": "user", "content": "..." }, { "role": "assistant", "content": "..." }]
    history: List[Dict[str, str]] = [] 

# --- Endpoint de Chat (O Cérebro) ---

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Endpoint principal.
    1. Recebe a pergunta e histórico.
    2. Passa para o Orquestrador (que chama Router -> Agente Especialista).
    3. Retorna JSON estruturado (Texto ou Gráfico) com metadados (query, tempo, sql).
    """
    start_time = time.monotonic()
    
    # Gerenciamento de ID de Sessão (Log e Rastreio)
    session_id = request.session_id or str(uuid.uuid4())

    # Logs removidos para evitar duplicação com o Orchestrator
    
    try:
        # 1. Preparar o Histórico para o Prompt
        # O Router precisa ler o histórico como texto para resolver pronomes ("dela", "isso").
        chat_history_text = ""
        if request.history:
            chat_history_text = "\n".join([
                f"{msg.get('role', 'user').title()}: {msg.get('content', '')}" 
                for msg in request.history[-6:] # Pega apenas as últimas 6 mensagens para economizar tokens
            ])

        # 2. Instanciar e Invocar o Orquestrador
        # Nota: O Orquestrador já contém o Router e os Agentes (Tracking/Analytics).
        orchestrator = get_orchestrator_chain()
        
        result = orchestrator.invoke({
            "question": request.question,
            "chat_history": chat_history_text,
            "category": "" # O próprio chain vai preencher isso via Router
        })

        # 3. Processar Resultado
        # O 'result' vindo do orchestrator já deve ser um dicionário limpo
        final_response = result

        # 4. Calcular Tempo e Montar Resposta Final da API
        end_time = time.monotonic()
        duration = end_time - start_time

        # Injetamos metadados técnicos no JSON de resposta
        if isinstance(final_response, dict):
            # Formatação do tempo
            final_response['execution_time'] = duration
            final_response['response_time'] = f"{duration:.2f}" # Mantido para compatibilidade legada
            
            # Injeta a query original (Pedido pelo usuário)
            final_response['query'] = request.question
            
            # Garante session_id
            final_response['session_id'] = session_id
            
        return final_response

    except Exception as e:
        logger.error(f"Erro CRÍTICO no processamento: {e}", exc_info=True)
        # Fallback seguro para não quebrar o frontend
        return {
            "type": "text",
            "content": f"Desculpe, ocorreu um erro interno ao processar sua solicitação. Detalhes: {str(e)}",
            "session_id": session_id,
            "query": request.question,
            "response_time": "0.00"
        }

@app.get("/")
def read_root():
    return {"status": "Supporte BI Multi-Agent API is running", "version": "2.2"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)