# ==============================================================================
# ARQUIVO: app/services/cluster_engine.py
#
# OBJETIVO:
#   Realizar o agrupamento matemático (Non-supervised Clustering) dos vetores.
#   Identifica quais chamados falam sobre a mesma coisa baseado na proximidade semântica.
#
# RESPONSABILIDADES:
#   - Receber vetores (embeddings) de alta dimensionalidade (1536d)
#   - Aplicar o algoritmo HDBSCAN para encontrar densidades locais
#   - Retornar quais IDs pertencem a quais Grupos
#
# DEPENDÊNCIAS:
#   - HDBSCAN (Biblioteca de Machine Learning para clustering hierárquico)
#   - Numpy (Operações matriciais)
# ==============================================================================

import hdbscan
import numpy as np
import logging
from app.core.vector_store import vector_db

logger = logging.getLogger(__name__)

def perform_clustering(vectors: list[list[float]]):
    """
    Executa o algoritmo de machine learning HDBSCAN sobre a lista de vetores.
    
    PARÂMETROS:
        - vectors: Lista de listas (matriz) onde cada linha é um embedding de 1536 dimensões.
    
    RETORNO:
        - labels: Um array numpy onde cada posição corresponde ao índice do vetor original.
          Valor -1: Indica ruído (o algoritmo decidiu que este ponto não pertence a nenhum grupo coeso).
          Valor >= 0: ID do grupo encontrado (0, 1, 2, ...).
    
    POR QUE HDBSCAN?
        Diferente do K-Means que exige que você chute o número de clusters (K), o HDBSCAN
        encontra o número "natural" de grupos baseado na densidade dos pontos. Isso é ideal
        para chamados de suporte, onde não sabemos a priori quantos problemas existem.
    """
    # Validação mínima de dados para evitar crash do modelo
    if not vectors or len(vectors) < 5:
        logger.warning("Poucos dados para clusterização (min 5). Retornando vazio.")
        return []

    logger.info(f"Iniciando HDBSCAN para {len(vectors)} vetores...")

    # Converter para formato numpy (Formato nativo exigido pela lib scikit-learn/hdbscan)
    data = np.array(vectors)

    # CONFIGURAÇÃO DO MODELO
    # ---------------------
    # min_cluster_size: O parâmetro mais crítico. Define quão pequeno um grupo pode ser.
    #   - Valor baixo (ex: 3): Encontra muitos micro-problemas, mais sensível.
    #   - Valor alto (ex: 20): Só encontra grandes tendências globais.
    #
    # min_samples: Controla o quão "conservador" é o algoritmo.
    #   - Valor alto faz com que pontos duvidosos sejam jogados como Ruído (-1).
    #
    # metric='euclidean': Distância euclidiana padrão. (Para cosseno, teríamos que pré-normalizar,
    # mas a OpenAI já entrega normalizado, então euclidiana ~ cosseno).
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=5, 
        min_samples=2,
        metric='euclidean', 
        cluster_selection_method='eom' # Excess of Mass: Método padrão robusto para dados variáveis
    )

    # Treinamento e Predição em passo único
    clusterer.fit(data)
    
    # --- Análise do Resultado ---
    # Contamos quantos labels únicos existem (excluindo o -1 se houver)
    num_clusters = len(set(clusterer.labels_)) - (1 if -1 in clusterer.labels_ else 0)
    
    # Calculamos a % de chamados que não se encaixaram em lugar nenhum (Ruído)
    noise_ratio = list(clusterer.labels_).count(-1) / len(vectors)
    
    logger.info(f"Clusterização concluída. Grupos encontrados: {num_clusters}")
    logger.info(f"Taxa de Ruído (chamados únicos): {noise_ratio:.1%}")

    return clusterer.labels_, noise_ratio

def get_vectors_from_qdrant_for_ids(ids_chamados: list[str]):
    """
    Placeholder: Função auxiliar futura para buscar vetores específicos no Qdrant
    caso o pipeline evolua para processamento incremental (não-batch).
    
    Atualmente o 'run_pipeline.py' cuida de buscar os vetores, então esta função
    está aqui apenas para referência arquitetural.
    """
    pass