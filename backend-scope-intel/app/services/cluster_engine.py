import hdbscan
import numpy as np
import logging
from app.core.vector_store import vector_db

logger = logging.getLogger(__name__)

def perform_clustering(vectors: list[list[float]]):
    """
    Recebe uma lista de vetores (embeddings) e retorna os Labels (ID do grupo).
    
    Retorno:
    - labels: Lista de inteiros. 
       -1 = Ruído (Não agrupou com nada)
       0, 1, 2... = IDs dos clusters encontrados
    """
    if not vectors or len(vectors) < 5:
        logger.warning("Poucos dados para clusterização (min 5). Retornando vazio.")
        return []

    logger.info(f"Iniciando HDBSCAN para {len(vectors)} vetores...")

    # Converter para formato numpy (necessário para o algoritmo)
    data = np.array(vectors)

    # Configuração do HDBSCAN
    # min_cluster_size: O tamanho mínimo para considerar um grupo. 
    # Para chamados de TI, 5 a 10 é um bom número inicial.
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=5, 
        min_samples=2,
        metric='euclidean', 
        cluster_selection_method='eom' # Excess of Mass (Geralmente melhor para dados reais)
    )

    clusterer.fit(data)
    
    # Quantos grupos achamos?
    num_clusters = len(set(clusterer.labels_)) - (1 if -1 in clusterer.labels_ else 0)
    noise_ratio = list(clusterer.labels_).count(-1) / len(vectors)
    
    logger.info(f"Clusterização concluída. Grupos encontrados: {num_clusters}")
    logger.info(f"Taxa de Ruído (chamados únicos): {noise_ratio:.1%}")

    return clusterer.labels_

def get_vectors_from_qdrant_for_ids(ids_chamados: list[str]):
    """
    Busca no Qdrant apenas os vetores dos chamados que estamos analisando agora.
    Isso é crucial pois o Qdrant pode ter chamados de outros sistemas/datas.
    """
    # Nota: Em um cenário Batch simplificado, poderíamos assumir que 
    # o 'process_and_vectorize' retornou os vetores na memória.
    # Mas para ser robusto, buscamos do Qdrant (Scroll com filtro).
    
    # *Simplificação para o MVP:* # Como acabamos de rodar o vectorizer, os vetores estão "quentes".
    # Vamos assumir que o orquestrador (run_pipeline) vai passar os vetores 
    # diretamente para evitar re-ler o banco agora.
    pass