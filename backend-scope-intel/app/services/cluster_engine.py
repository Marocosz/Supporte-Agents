# ==============================================================================
# ARQUIVO: app/services/cluster_engine.py
#
# OBJETIVO:
#   Realizar o agrupamento matemático (Non-supervised Clustering) dos vetores.
#   Identifica quais chamados falam sobre a mesma coisa baseado na proximidade semântica.
#
# RESPONSABILIDADES:
#   - Receber vetores (embeddings) de alta dimensionalidade (1536d)
#   - Reduzir a dimensionalidade para densificar os dados (UMAP)
#   - Aplicar o algoritmo HDBSCAN para encontrar densidades locais
#   - Retornar quais IDs pertencem a quais Grupos
#
# DEPENDÊNCIAS:
#   - UMAP (Redução de dimensionalidade / Manifold Learning)
#   - HDBSCAN (Biblioteca de Machine Learning para clustering hierárquico)
#   - Numpy (Operações matriciais)
# ==============================================================================

import hdbscan
import numpy as np
import logging
import umap
from app.core.vector_store import vector_db

logger = logging.getLogger(__name__)

def perform_clustering(vectors: list[list[float]]):
    """
    Executa o pipeline Híbrido (UMAP + HDBSCAN) sobre a lista de vetores.
    
    PARÂMETROS:
        - vectors: Lista de listas (matriz) onde cada linha é um embedding de 1536 dimensões.
    
    RETORNO:
        - labels: Um array numpy onde cada posição corresponde ao índice do vetor original.
          Valor -1: Indica ruído (o algoritmo decidiu que este ponto não pertence a nenhum grupo coeso).
          Valor >= 0: ID do grupo encontrado (0, 1, 2, ...).
    
    ESTRATÉGIA HÍBRIDA:
        1. UMAP: Reduz de 1536 dimensões para 5. Isso "aproxima" matematicamente
           chamados que estariam distantes na vastidão de 1536d.
        2. HDBSCAN: Agrupa esses pontos densificados.
    """
    # Validação mínima de dados para evitar crash do modelo
    if not vectors or len(vectors) < 5:
        logger.warning("Poucos dados para clusterização (min 5). Retornando vazio.")
        # Retorna lista de -1 (tudo ruído) para não quebrar o pipeline
        if vectors:
            return np.full(len(vectors), -1)
        return []

    logger.info(f"Iniciando Clusterização Híbrida (UMAP + HDBSCAN) para {len(vectors)} vetores...")

    # Converter para formato numpy (Formato nativo exigido pela lib scikit-learn/hdbscan)
    data = np.array(vectors)

    # --- ETAPA 1: REDUÇÃO DE DIMENSIONALIDADE (UMAP) ---
    # O UMAP é crucial para datasets pequenos (< 1000 itens). Ele cria uma topologia
    # simplificada dos dados, facilitando o trabalho do HDBSCAN.
    
    # Proteção: O n_neighbors não pode ser maior que o número de dados - 1.
    # Ajustamos dinamicamente para evitar erros em testes pequenos.
    n_neighbors = min(15, len(vectors) - 1)
    
    logger.info(f"Executando UMAP (Reduzindo 1536d -> 5d, Vizinhos={n_neighbors})...")
    
    reducer = umap.UMAP(
        n_neighbors=n_neighbors,
        n_components=5,       # Reduz para 5 dimensões (Número mágico para clustering de texto)
        min_dist=0.0,         # 0.0 força os pontos a ficarem bem compactos
        metric='cosine',      # Cosseno é a métrica correta para Embeddings da OpenAI
        random_state=42       # Tenta manter determinístico
    )
    
    embedding_reduzido = reducer.fit_transform(data)

    # --- ETAPA 2: CLUSTERING (HDBSCAN) ---
    # Agora rodamos o HDBSCAN nos dados "simplificados" (embedding_reduzido).
    
    logger.info("Executando HDBSCAN nos dados reduzidos...")
    
    # CONFIGURAÇÃO AJUSTADA (Sensibilidade Alta)
    # ---------------------
    # min_cluster_size=3: Aceita micro-padrões. Se 3 pessoas tiverem o mesmo erro, é grupo.
    # min_samples=1: Super agressivo. Tenta puxar qualquer ponto vizinho para dentro do grupo,
    #                reduzindo drasticamente a taxa de ruído.
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=3, 
        min_samples=1,
        metric='euclidean', # No espaço reduzido do UMAP, euclidiana funciona bem
        cluster_selection_method='eom' 
    )

    # Treinamento e Predição
    clusterer.fit(embedding_reduzido)
    
    # --- Análise do Resultado ---
    # Contamos quantos labels únicos existem (excluindo o -1 se houver)
    num_clusters = len(set(clusterer.labels_)) - (1 if -1 in clusterer.labels_ else 0)
    
    # Calculamos a % de chamados que não se encaixaram em lugar nenhum (Ruído)
    noise_ratio = list(clusterer.labels_).count(-1) / len(vectors)
    
    logger.info(f"Clusterização concluída.")
    logger.info(f"   > Grupos encontrados: {num_clusters}")
    logger.info(f"   > Taxa de Ruído: {noise_ratio:.1%}")

    return clusterer.labels_

def get_vectors_from_qdrant_for_ids(ids_chamados: list[str]):
    """
    Placeholder: Função auxiliar futura para buscar vetores específicos no Qdrant.
    """
    pass