"""
MÓDULO: app/api/endpoints/http_session.py - ENDPOINT DE INÍCIO DE SESSÃO (HTTP)

FUNÇÃO:
Define o endpoint HTTP principal (`/start`) responsável por receber os
metadados iniciais do documento (Codificação, Título, Tipo) e, em seguida,
iniciar o ciclo de vida de uma nova sessão de geração de documento.

ARQUITETURA:
1. **Validação de Entrada:** Usa o schema Pydantic `SessionStartRequest`
   para validar os dados de entrada do corpo da requisição POST.
2. **Criação de Estado:** Chama o `session_manager.create_session` para:
   - Gerar um ID único (UUID) para a sessão.
   - Persistir o estado inicial da sessão no cache em memória.
   - Preencher os metadados fixos (data e revisão "00").
3. **Resposta:** Retorna o `session_id` gerado e uma mensagem de sucesso
   no formato `SessionStartResponse`. Este ID é crucial para que o frontend
   possa estabelecer a conexão WebSocket no próximo passo.

FLUXO DE USO:
Este é o primeiro endpoint a ser chamado pelo cliente, antes de iniciar
qualquer comunicação WebSocket.
"""
import logging
from fastapi import APIRouter, Body, HTTPException

# Importa os "contratos" (schemas) de entrada e saída
from app.core.schemas import SessionStartRequest, SessionStartResponse
# Importa o "serviço" de gerenciamento de sessão, que contém a lógica de criação
from app.services.session_manager import session_manager

logger = logging.getLogger(__name__)
# Cria o roteador específico para as rotas de sessão HTTP
router = APIRouter()


@router.post(
    "/start",
    response_model=SessionStartResponse,
    summary="Inicia uma nova sessão de geração de documento"
)
async def start_new_session(
    # Usa Body(...) para garantir que o corpo da requisição seja validado pelo Pydantic
    start_data: SessionStartRequest = Body(...)
):
    """
    Inicia uma nova sessão de chat.
    
    Recebe: Dados iniciais do documento (tipo, codificação, título).
    Ações: Cria o objeto de estado, gera o session_id e preenche metadados (data/revisão).
    Retorna: O session_id para uso no endpoint WebSocket.
    """
    try:
        logger.info(
            f"Recebida solicitação para iniciar sessão para: {start_data.codificacao}")

        # Chama o SessionManager para inicializar o estado da sessão.
        # A função retorna uma tupla (session_id, welcome_message).
        session_id, welcome_message = session_manager.create_session(
            start_data)

        # Retorna o modelo de resposta formatado
        return SessionStartResponse(
            session_id=session_id,
            message=welcome_message 
        )
        
    except Exception as e:
        # Tratamento de exceção em caso de falha na criação da sessão
        logger.error(f"Erro ao criar sessão: {e}", exc_info=True)
        # Retorna um erro HTTP 500 para o cliente
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao iniciar a sessão: {e}"
        )