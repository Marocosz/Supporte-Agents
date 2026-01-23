# app/services/context.py
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Armazenamento em memória: {session_id: {data}}
# Em produção, substitua por Redis.
_MEMORY_STORE: Dict[str, Dict[str, Any]] = {}

class ContextManager:
    """
    Gerencia a memória de curto prazo da sessão do usuário.
    Permite que o sistema lembre da 'última entidade citada'.
    """

    @staticmethod
    def get_context(session_id: str) -> Dict[str, Any]:
        return _MEMORY_STORE.get(session_id, {})

    @staticmethod
    def update_context(session_id: str, key: str, value: Any):
        if session_id not in _MEMORY_STORE:
            _MEMORY_STORE[session_id] = {}
        
        _MEMORY_STORE[session_id][key] = value
        logger.debug(f"🧠 [CONTEXT] Sessão {session_id[:8]} atualizada: {key}={value}")

    @staticmethod
    def get_last_entity(session_id: str) -> Optional[str]:
        """Retorna a última entidade (ex: Nota 40908) para resolver pronomes."""
        ctx = ContextManager.get_context(session_id)
        return ctx.get("last_entity_id")

    @staticmethod
    def clear_session(session_id: str):
        if session_id in _MEMORY_STORE:
            del _MEMORY_STORE[session_id]