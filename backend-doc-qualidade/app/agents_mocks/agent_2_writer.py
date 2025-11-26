import logging
from typing import List, Dict

# (Importações de IA e RAG são removidas)

logger = logging.getLogger(__name__)

# (Schema de Saída não é necessário para o mock)

class Agent2Writer_Mock:
    def __init__(self):
        logger.info("Agente 2 (Writer) [MOCK ATIVADO]")
        self.final_chain = True # Apenas para simular que está pronto

    async def generate_draft(self, resumo_original: str, sumario_aprovado: List[str]) -> Dict[str, str]:
        if not self.final_chain:
            return {"ERRO": "Agente 2 (Writer) Mock não inicializado."}
            
        logger.info(f"Agente 2 (Writer) MOCK: Gerando rascunho falso para {len(sumario_aprovado)} seções...")
        
        # --- DADOS FALSOS ---
        rascunho_mock = {}
        for secao in sumario_aprovado:
            if "Fluxograma" in secao:
                rascunho_mock[secao] = "Este é um placeholder MOCK para o fluxograma."
            elif "Registros" in secao:
                rascunho_mock[secao] = "NA (Mock)"
            else:
                rascunho_mock[secao] = f"Este é o conteúdo de rascunho gerado pelo **Agente 2 (Mock)** para a seção '{secao}'. O resumo original era: '{resumo_original[:50]}...'"
        
        logger.info("Agente 2 (Writer) MOCK: Rascunho completo falso gerado com sucesso.")
        return rascunho_mock

# Cria a instância única
agent_2_writer = Agent2Writer_Mock()