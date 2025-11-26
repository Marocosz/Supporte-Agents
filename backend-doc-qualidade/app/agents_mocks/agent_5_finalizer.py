import logging
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import json

# Importa os Schemas (necessários para a montagem)
from app.core.schemas import DocumentoFinalJSON, Secao, SubSecao

logger = logging.getLogger(__name__)

# (Schemas de Saída e Prompts são removidos, pois não usamos LLM)

class Agent5Finalizer_Mock:
    
    def __init__(self):
        logger.info("Agente 5 (Finalizer) [MOCK ATIVADO - SEM LLM]")
        # Este agente não precisa de LLM no modo mock
        self.chain = True

    async def generate_final_json(
        self, 
        dados_iniciais: DocumentoFinalJSON, # Usado para metadados
        rascunho_aprovado: Dict[str, str],
        ativos_aceitos: List[Dict[str, Any]],
        respostas_enriquecimento: List[Dict[str, Any]] # Ignorado no mock, pois o Agente 3 já injetou
    ) -> DocumentoFinalJSON:
        
        logger.info(f"Agente 5 (Finalizador) MOCK: Iniciando montagem final do {dados_iniciais.codificacao}...")
        
        try:
            # --- LÓGICA DE MONTAGEM (SEM IA) ---
            corpo_final = []
            
            # 1. Converte o rascunho em Seções
            for titulo, conteudo in rascunho_aprovado.items():
                nova_secao = Secao(titulo=titulo, conteudo=conteudo, subsecoes=[])
                corpo_final.append(nova_secao)

            # 2. Incorpora os Ativos Aceitos como SubSeções
            for ativo in ativos_aceitos:
                secao_alvo = ativo.get("secao_alvo")
                # Tenta encontrar a seção no corpo
                secao_encontrada = next((s for s in corpo_final if s.titulo == secao_alvo), None)
                
                if secao_encontrada:
                    nova_subsecao = SubSecao(
                        titulo=f"{ativo.get('tipo_ativo', 'Ativo')} (Mock)",
                        conteudo=ativo.get('conteudo', 'Placeholder de Ativo')
                    )
                    secao_encontrada.subsecoes.append(nova_subsecao)
                else:
                    logger.warning(f"Agente 5 MOCK: Não foi possível encontrar a seção alvo '{secao_alvo}' para o ativo.")

            # Monta o objeto final
            json_final = dados_iniciais.model_copy(deep=True)
            json_final.corpo_documento = corpo_final
            
            logger.info(f"Agente 5 (Finalizador) MOCK: JSON final montado com sucesso.")
            return json_final
            
        except Exception as e:
            logger.error(f"Agente 5 (Finalizador) MOCK: Erro ao montar JSON final: {e}", exc_info=True)
            # Levanta o erro para o Orquestrador
            raise e 

# Cria a instância única
agent_5_finalizer = Agent5Finalizer_Mock()