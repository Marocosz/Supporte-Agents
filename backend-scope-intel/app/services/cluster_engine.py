# ==============================================================================
# ARQUIVO: app/services/cluster_engine.py
#
# OBJETIVO:
#   Realizar o agrupamento matemático (Non-supervised Clustering) dos vetores.
#   Identifica quais chamados falam sobre a mesma coisa baseado na proximidade semântica.
#
# PARTE DO SISTEMA:
#   Backend / Core ML (Machine Learning)
#
# RESPONSABILIDADES:
#   - Receber vetores (embeddings) de alta dimensionalidade (1536d/3072d)
#   - Calcular parâmetros dinâmicos baseados no volume de dados (Auto-Tuning)
#   - Reduzir a dimensionalidade para densificar os dados (UMAP)
#   - Aplicar o algoritmo HDBSCAN para encontrar densidades locais
#   - Implementar Lógica Recursiva (Macro -> Micro) para refinamento
#   - Retornar Labels (quem é quem) e Probabilidades (confiança)
#
# COMUNICAÇÃO:
#   Chamado por: run_pipeline.py
#   Usa bibliotecas: UMAP, HDBSCAN, Scikit-Learn (implícito), Numpy
# ==============================================================================

import hdbscan
import numpy as np
import logging
import umap
from app.core.vector_store import vector_db

logger = logging.getLogger(__name__)

def perform_clustering(vectors: list[list[float]]):
    """
    Executa o pipeline Híbrido Recursivo (UMAP + HDBSCAN) com AUTO-TUNING.
    
    Ajusta dinamicamente a sensibilidade do algoritmo baseada na quantidade
    de dados (evita overfitting em bases grandes e underfitting em bases pequenas).
    
    RETORNO:
        - final_labels: Array numpy com os IDs finais (nível Micro).
        - hierarchy_map: Dicionário mapeando { "macro_X": [id_micro_1, id_micro_2] }
        - params: Parâmetros usados.
        - coords_2d: Dict {index: [x, y]} para plotagem global.
        - final_probs: Array numpy com a confiança (0.0 a 1.0) de cada ponto.
    """
    # Validação mínima de dados para evitar crash do modelo
    if not vectors or len(vectors) < 5:
        logger.warning("Poucos dados para clusterização (min 5). Retornando vazio.")
        if vectors:
            return np.full(len(vectors), -1), {}, {}, {}, np.zeros(len(vectors))
        return [], {}, {}, {}, []

    total_items = len(vectors)
    
    # --- AUTO-TUNING: Calcula parâmetros baseado no volume ---
    params = _get_dynamic_params(total_items)
    
    logger.info(f"Iniciando Clusterização para {total_items} vetores com Auto-Tuning:")
    
    # Converter para formato numpy
    data = np.array(vectors)
    
    # --- NOVO: Cálculo de Coordenadas Globais para Visualização (Map Clean) ---
    logger.info(">>> Gerando Mapa 2D Global (UMAP) para visualização...")
    coords_2d = {}
    try:
        # UMAP 2D específico para visualização (focado em estética global)
        # n_neighbors maior ajuda a manter a estrutura global do mapa
        viz_reducer = umap.UMAP(
            n_neighbors=min(30, total_items - 1), 
            n_components=2, 
            min_dist=0.2,
            metric='cosine',
            random_state=42
        )
        embedding_2d = viz_reducer.fit_transform(data)
        
        # Converte para dict {index: [x, y]}
        for i, point in enumerate(embedding_2d):
            coords_2d[i] = [float(point[0]), float(point[1])]
    except Exception as e:
        logger.warning(f"Falha ao gerar mapa 2D: {e}")
        for i in range(total_items):
            coords_2d[i] = [0.0, 0.0]

    # Array final de labels (inicialmente tudo marcado como ruído -1)
    final_labels = np.full(total_items, -1)
    # Array final de probabilidades (inicialmente 0)
    final_probs = np.zeros(total_items)
    
    # Mapa de Hierarquia
    hierarchy_map = {} 

    # --- ETAPA 1: CLUSTERIZAÇÃO MACRO (Visão Geral) ---
    logger.info(f"1️⃣  Clusterização MACRO (Generalista)...")
    
    macro_labels, macro_probs = _run_umap_hdbscan(
        data, 
        n_neighbors=params['n_neighbors_macro'], 
        min_dist=0.2, 
        min_cluster_size=params['macro_min_size'], 
        min_samples=1
    )
    
    unique_labels = set(macro_labels) - {-1}
    next_label_id = 0 

    # --- ETAPA 2: ANÁLISE RECURSIVA (Refinamento Cirúrgico) ---
    for macro_id in unique_labels:
        # Pega os índices (posições) dos vetores que pertencem a este grupo macro
        indices_no_grupo = np.where(macro_labels == macro_id)[0]
        tamanho_grupo = len(indices_no_grupo)
        
        filhos_gerados = []

        # CENÁRIO A: Grupo Dentro do Limite -> Aceitamos como está.
        if tamanho_grupo <= params['max_cluster_size']:
            final_labels[indices_no_grupo] = next_label_id
            # Salvamos a probabilidade original do Macro, pois ele virou o cluster final
            final_probs[indices_no_grupo] = macro_probs[indices_no_grupo]
            
            filhos_gerados.append(next_label_id)
            next_label_id += 1
            
            hierarchy_map[f"macro_{macro_id}"] = filhos_gerados
            continue

        # CENÁRIO B: Grupo GIGANTE -> Tentamos quebrar.
        logger.info(f"🔨 Refinando Macro-Grupo {macro_id} ({tamanho_grupo} itens)...")
        
        sub_vectors = data[indices_no_grupo]
        
        sub_labels, sub_probs = _run_umap_hdbscan(
            sub_vectors, 
            n_neighbors=5, 
            min_dist=0.1, 
            min_cluster_size=params['micro_min_size'], 
            min_samples=1
        )
        
        sub_unique = set(sub_labels) - {-1}
        
        if len(sub_unique) <= 1:
            # Não quebrou bem, mantemos o bloco original
            final_labels[indices_no_grupo] = next_label_id
            final_probs[indices_no_grupo] = macro_probs[indices_no_grupo] # Prob do pai
            
            filhos_gerados.append(next_label_id)
            next_label_id += 1
        else:
            # Sucesso na quebra
            for sub_l in sub_unique:
                mask_sub = (sub_labels == sub_l)
                indices_reais = indices_no_grupo[mask_sub]
                
                final_labels[indices_reais] = next_label_id
                # Aqui usamos a probabilidade calculada no sub-clustering (mais precisa)
                final_probs[indices_reais] = sub_probs[mask_sub]
                
                filhos_gerados.append(next_label_id)
                next_label_id += 1
            
            # Nota: O que virou ruído (-1) no sub-clustering fica com label -1 e prob 0 (default)
        
        hierarchy_map[f"macro_{macro_id}"] = filhos_gerados

    # --- Análise Final ---
    num_clusters = len(set(final_labels)) - (1 if -1 in final_labels else 0)
    noise_ratio = list(final_labels).count(-1) / total_items
    
    logger.info(f"🏁 Clusterização Final: {num_clusters} micro-grupos. Ruído: {noise_ratio:.1%}")

    return final_labels, hierarchy_map, params, coords_2d, final_probs

def _get_dynamic_params(total_items: int):
    """
    Lógica Matemática para definir os parâmetros baseado no tamanho do dataset.
    Isso equilibra sistemas pequenos (200) e grandes (2000).
    """
    params = {}

    # 1. Régua MACRO (min_cluster_size)
    # Regra: Pelo menos 1% dos dados, mas nunca menos que 4 nem mais que 15.
    raw_macro = int(total_items * 0.01) # 1%
    params['macro_min_size'] = max(4, min(15, raw_macro))

    # 2. Teto para Quebra (max_cluster_size)
    # Regra: Se um grupo tem mais de 10% dos dados ou mais de 50 itens, é gigante.
    raw_max = int(total_items * 0.10) # 10%
    params['max_cluster_size'] = max(20, min(50, raw_max))

    # 3. Régua MICRO (min_cluster_size para sub-grupos)
    if total_items < 500:
        params['micro_min_size'] = 3
    else:
        params['micro_min_size'] = 4

    # 4. Vizinhos UMAP (n_neighbors) para Macro
    params['n_neighbors_macro'] = min(15, total_items - 1)

    return params

def _run_umap_hdbscan(data, n_neighbors, min_dist, min_cluster_size, min_samples):
    """
    Função interna auxiliar que permite rodar UMAP+HDBSCAN com parâmetros dinâmicos.
    Retorna LABELS e PROBABILITIES.
    """
    # Proteção: n_neighbors não pode ser maior que o número de dados - 1.
    safe_neighbors = min(n_neighbors, len(data) - 1)
    if safe_neighbors < 2: 
        return np.full(len(data), -1), np.zeros(len(data))

    # 1. UMAP (Parametrizado)
    reducer = umap.UMAP(
        n_neighbors=safe_neighbors,
        n_components=5,
        min_dist=min_dist,
        metric='cosine',
        random_state=42
    )
    embedding_reduzido = reducer.fit_transform(data)

    # 2. HDBSCAN (Parametrizado)
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric='euclidean',
        cluster_selection_method='eom'
    )
    clusterer.fit(embedding_reduzido)
    
    return clusterer.labels_, clusterer.probabilities_

def get_vectors_from_qdrant_for_ids(ids_chamados: list[str]):
    pass