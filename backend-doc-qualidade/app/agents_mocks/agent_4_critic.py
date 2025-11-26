import logging
from pydantic import BaseModel, Field
from typing import List, Dict, Any

# (Importações de IA são removidas)

logger = logging.getLogger(__name__)

# (Os Schemas de Saída são mantidos para garantir a estrutura correta, 
# embora o PydanticOutputParser não seja usado)

class AtivoVisual(BaseModel):
    id: str = Field(description="Um ID único para o ativo, ex: 'ATIVO_001'")
    secao_alvo: str = Field(description="O TÍTULO EXATO da seção onde este ativo deve ser inserido (ex: 'Descrição do Processo').")
    tipo_ativo: str = Field(description="O tipo de ativo: 'mermaid_graph', 'raci_matrix', ou 'screenshot_placeholder'.")
    conteudo: str = Field(description="O código Mermaid ou o texto descritivo do placeholder.")

class PerguntaEnriquecimento(BaseModel):
    id: str = Field(description="Um ID único para a pergunta, ex: 'PERG_001'")
    secao_alvo: str = Field(description="O TÍTULO EXATO da seção que esta pergunta irá enriquecer.")
    pergunta: str = Field(description="A pergunta clara e concisa para o usuário (ex: 'Quais softwares são instalados na Etapa 2?').")

class AnaliseQA(BaseModel):
    ativos: List[AtivoVisual] = Field(description="A lista de todos os ativos visuais gerados para o documento.")
    perguntas: List[PerguntaEnriquecimento] = Field(description="A lista de perguntas de enriquecimento para o usuário.")

class Agent4Critic_Mock:
    def __init__(self):
        logger.info("Agente 4 (QA) [MOCK ATIVADO]")

    async def get_qa_analysis(self, rascunho_aprovado: Dict[str, str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Ponto de entrada principal. Retorna um dicionário FALSO com 'ativos' e 'perguntas'.
        """
        logger.info(f"Agente 4 (QA) MOCK: Analisando rascunho com {len(rascunho_aprovado)} seções...")
        
        # --- DADOS FALSOS ---
        mock_ativos = [
            {
                "id": "ATIVO_MOCK_001",
                "secao_alvo": "4. Fluxograma (Mock)",
                "tipo_ativo": "mermaid_graph",
                "conteudo": "graph TD; A[Início Mock] --> B[Fim Mock];"
            },
            {
                "id": "ATIVO_MOCK_002",
                "secao_alvo": "3. Descrição do Processo (Mock)",
                "tipo_ativo": "screenshot_placeholder",
                "conteudo": "[Placeholder Mock: Tela de login do sistema XYZ]"
            }
        ]
        
        mock_perguntas = [
            {
                "id": "PERG_MOCK_001",
                "secao_alvo": "2. Aplicação (Mock)",
                "pergunta": "Esta é a Pergunta Mock 1: O processo se aplica a estagiários?"
            },
            {
                "id": "PERG_MOCK_002",
                "secao_alvo": "3. Descrição do Processo (Mock)",
                "pergunta": "Esta é a Pergunta Mock 2: Qual sistema é usado para o controle?"
            }
        ]
        
        logger.info(f"Agente 4 (QA) MOCK: {len(mock_ativos)} ativos e {len(mock_perguntas)} perguntas falsas gerados.")
        
        return {
            "ativos": mock_ativos,
            "perguntas": mock_perguntas
        }

# Cria a instância única
agent_4_critic = Agent4Critic_Mock()