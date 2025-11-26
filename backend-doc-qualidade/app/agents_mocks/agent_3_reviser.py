import logging
from typing import List, Dict
import json

# (Importações de IA e RAG são removidas)

logger = logging.getLogger(__name__)

class Agent3Reviser_Mock:
    def __init__(self):
        logger.info("Agente 3 (Reviser) [MOCK ATIVADO]")
        self.final_chain = True

    async def revise_draft(self, resumo_original: str, rascunho_atual: Dict[str, str], user_feedback: str) -> Dict[str, str]:
        if not self.final_chain:
            return {"ERRO": "Agente 3 (Reviser) Mock não inicializado."}

        logger.info(f"Agente 3 (Reviser) MOCK: Refinando rascunho com feedback: '{user_feedback[:50]}...'")
        
        # --- LÓGICA FALSA ---
        # Simula a injeção de respostas
        if "INJETAR" in user_feedback:
            # Encontra a primeira seção de Descrição para injetar
            target_key = next((k for k in rascunho_atual if "Descrição" in k), None)
            if target_key:
                rascunho_atual[target_key] += "\n\n**INJEÇÃO (Mock):** O usuário forneceu novos detalhes que foram injetados aqui."
            else:
                 rascunho_atual["Injeção (Mock)"] = f"Não foi possível encontrar a seção alvo. Feedback: {user_feedback}"

        # Simula uma revisão de texto normal
        else:
            rascunho_atual["Revisão (Mock)"] = f"O usuário pediu a seguinte revisão: '{user_feedback}'"
        
        logger.info("Agente 3 (Reviser) MOCK: Rascunho revisado com sucesso.")
        return rascunho_atual

# Cria a instância única
agent_3_reviser = Agent3Reviser_Mock()