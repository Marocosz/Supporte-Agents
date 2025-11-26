import logging
from typing import List

# (Importações de IA e RAG são removidas, pois não são necessárias)

logger = logging.getLogger(__name__)

# Nota: Não precisamos dos schemas Pydantic aqui, 
# pois estamos a retornar dados Python puros.

class Agent1Planner_Mock:
    def __init__(self):
        # Não carrega o RAG Singleton para um arranque rápido
        logger.info("Agente 1 (Planner) [MOCK ATIVADO]")
        self.final_chain = True # Apenas para simular que está pronto

    async def generate_toc(self, user_summary: str) -> List[str]:
        """
        Ponto de entrada: Gera um Sumário (Tabela de Conteúdo) FALSO.
        """
        logger.info(f"Agente 1 (Planner) MOCK: Gerando sumário falso para: '{user_summary[:50]}...'")
        
        # --- DADOS FALSOS ---
        mock_secoes = [
            "Objetivo (Mock)",
            "Aplicação (Mock)",
            "Descrição do Processo (Mock)",
            "Fluxograma (Mock)",
            "Registros (Mock)"
        ]
        
        logger.info(f"Agente 1 (Planner) MOCK: Sumário falso gerado com {len(mock_secoes)} seções.")
        return mock_secoes

# Cria a instância única
agent_1_planner = Agent1Planner_Mock()