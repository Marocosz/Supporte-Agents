"""
MÓDULO: app/api/endpoints/ws_chat.py - ENDPOINT PRINCIPAL DO CHAT (WEBSOCKET)

FUNÇÃO:
Define o endpoint WebSocket para a comunicação em tempo real entre o frontend
e o backend. Este endpoint atua como o **Gatekeeper** para as sessões de chat,
garantindo que apenas sessões válidas sejam conectadas e roteando todas as
mensagens recebidas para o `ChatOrchestrator` para processamento do fluxo
de trabalho.

ARQUITETURA:
- **Router:** Define a rota `/chat/{session_id}` sob o prefixo `/v1/session`.
- **Ciclo de Vida:** Gerencia as fases cruciais da conexão:
    1. **Validação:** Verifica se o `session_id` existe no `SessionManager`.
    2. **Aceitação:** Aceita a conexão e entrega a inicialização ao Orquestrador.
    3. **Loop de Escuta:** Fica em um `while True` para receber mensagens.
    4. **Limpeza (`finally`):** Garante que a sessão seja removida do cache
       em caso de desconexão, erro ou conclusão do fluxo.

FLUXO DE DADOS:
As mensagens chegam como texto (ou strings de ação) via WebSocket e são
repassadas ao `chat_orchestrator.handle_chat_message` para que a Máquina de
Estados da aplicação avance.
"""
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Path

# Importa o "Chefe" (Orquestrador) que contém a lógica de transição dos agentes
from app.services.orchestrator import chat_orchestrator
# Importa o "Cache" (Session Manager) para validar e remover sessões
from app.services.session_manager import session_manager

logger = logging.getLogger(__name__)
# Cria um roteador específico para as rotas WebSocket
router = APIRouter()

@router.websocket("/chat/{session_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    # O ID da sessão deve ser passado como parâmetro de caminho na URL
    session_id: str = Path(...) 
):
    """
    Endpoint WebSocket para o chat interativo.
    A URL completa é /v1/session/chat/{session_id}
    """
    
    # 1. Tenta pegar a sessão no cache
    session = session_manager.get_session(session_id)
    if not session:
        logger.warning(f"WS: Tentativa de conexão com session_id inválida: {session_id}")
        await websocket.close(code=1008, reason="Sessão inválida ou expirada.")
        return # Impede a continuação do código se a sessão não existir

    # 2. Aceita a conexão WebSocket (Estabelecimento do protocolo)
    await websocket.accept()
    logger.info(f"WS: Conexão aceita para sessão {session_id}")

    # 3. Entrega ao Orquestrador para enviar a mensagem de boas-vindas
    # e definir o status inicial (handle_new_connection)
    await chat_orchestrator.handle_new_connection(websocket, session_id)

    try:
        # 4. Loop principal: Fica ouvindo mensagens do usuário
        while True:
            # Bloqueia até receber uma mensagem de texto (user_message ou action_value)
            data = await websocket.receive_text()
            
            # 5. Repassa a mensagem do usuário para o Orquestrador
            await chat_orchestrator.handle_chat_message(websocket, session_id, data)
            
            # 6. Verifica se o Orquestrador encerrou a sessão após o processamento
            if not session_manager.get_session(session_id):
                logger.info(f"WS: Sessão {session_id} foi encerrada pelo Orquestrador. Fechando loop.")
                break # Sai do loop 'while True' para entrar no bloco 'finally'
            
    except WebSocketDisconnect:
        # Exceção tratada quando o cliente fecha a conexão (ex: fechar a aba)
        logger.info(f"WS: Cliente desconectado (WebSocketDisconnect) da sessão {session_id}")
    
    except RuntimeError as e:
        # Trata erros de runtime, como tentar enviar dados para uma conexão já fechada
        if "WebSocket is not connected" in str(e):
            logger.info(f"WS: Conexão fechada pelo servidor (RuntimeError): {session_id}")
        else:
            # Erro de runtime inesperado
            logger.error(f"WS: RuntimeError inesperado na sessão {session_id}: {e}", exc_info=True)
            try:
                # Tenta notificar o cliente sobre o erro (se a conexão ainda estiver minimamente viva)
                await websocket.send_json({
                    "type": "error", "content": f"Erro interno: {e}", "actions": []
                })
            except Exception:
                pass # A conexão está morta, ignora falha no envio
    
    except Exception as e:
        # Trata qualquer outra exceção inesperada durante o processamento
        logger.error(f"WS: Exceção inesperada na sessão {session_id}: {e}", exc_info=True)
        try:
            # Tenta notificar o cliente
            await websocket.send_json({
                "type": "error", "content": f"Erro interno do servidor: {e}", "actions": []
            })
        except Exception:
            pass # Conexão morta
    
    finally:
        # --- Bloco de Limpeza (Executado em qualquer saída do 'try') ---
        # Garante que a sessão seja removida do cache, independentemente do motivo do encerramento
        session_manager.remove_session(session_id)
        logger.info(f"WS: Limpeza final da sessão {session_id} concluída.")