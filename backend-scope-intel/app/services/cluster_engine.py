# ==============================================================================
# ARQUIVO: app/services/cluster_engine.py
#
# OBJETIVO:
#   Realizar o agrupamento matemático (Non-supervised Clustering) dos vetores.
#   Identifica quais chamados falam sobre a mesma coisa baseado na proximidade semântica.
#
# RESPONSABILIDADES:
#   - Receber vetores (embeddings) de alta dimensionalidade (1536d)
#   - Calcular parâmetros dinâmicos baseados no volume de dados (Auto-Tuning)
#   - Reduzir a dimensionalidade para densificar os dados (UMAP)
#   - Aplicar o algoritmo HDBSCAN para encontrar densidades locais
#   - Implementar Lógica Recursiva (Macro -> Micro)
#   - Retornar quais IDs pertencem a quais Grupos e o Mapa de Paternidade
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
    Executa o pipeline Híbrido Recursivo (UMAP + HDBSCAN) com AUTO-TUNING.
    
    Ajusta dinamicamente a sensibilidade do algoritmo baseada na quantidade
    de dados (evita overfitting em bases grandes e underfitting em bases pequenas).
    
    RETORNO:
        - final_labels: Array numpy com os IDs finais (nível Micro).
        - hierarchy_map: Dicionário mapeando { "macro_X": [id_micro_1, id_micro_2] }
          Isso permite reconstruir a árvore Pai -> Filhos depois.
    """
    # Validação mínima de dados para evitar crash do modelo
    if not vectors or len(vectors) < 5:
        logger.warning("Poucos dados para clusterização (min 5). Retornando vazio.")
        if vectors:
            return np.full(len(vectors), -1), {}
        return [], {}

    total_items = len(vectors)
    
    # --- AUTO-TUNING: Calcula parâmetros baseado no volume ---
    # Isso substitui as constantes fixas anteriores
    params = _get_dynamic_params(total_items)
    
    logger.info(f"Iniciando Clusterização para {total_items} vetores com Auto-Tuning:")
    logger.info(f"   > Régua Macro (Min Size): {params['macro_min_size']}")
    logger.info(f"   > Teto Quebra (Max Size): {params['max_cluster_size']}")
    logger.info(f"   > Régua Micro (Min Size): {params['micro_min_size']}")

    # Converter para formato numpy
    data = np.array(vectors)
    
    # Array final de labels (inicialmente tudo marcado como ruído -1)
    final_labels = np.full(total_items, -1)
    
    # Mapa de Hierarquia: Vai guardar quem é pai de quem
    hierarchy_map = {} 

    # --- ETAPA 1: CLUSTERIZAÇÃO MACRO (Visão Geral) ---
    logger.info(f"1️⃣  Clusterização MACRO (Generalista)...")
    
    # UMAP "Míope": Olha para muitos vizinhos (calculado dinamicamente) e compacta bem.
    # HDBSCAN: Min Cluster dinâmico.
    macro_labels = _run_umap_hdbscan(
        data, 
        n_neighbors=params['n_neighbors_macro'], 
        min_dist=0.2, 
        min_cluster_size=params['macro_min_size'], # <--- Dinâmico
        min_samples=1
    )
    
    unique_labels = set(macro_labels) - {-1}
    next_label_id = 0 # Contador global para os novos IDs finais

    # --- ETAPA 2: ANÁLISE RECURSIVA (Refinamento Cirúrgico) ---
    for macro_id in unique_labels:
        # Pega os índices (posições) dos vetores que pertencem a este grupo macro
        indices_no_grupo = np.where(macro_labels == macro_id)[0]
        tamanho_grupo = len(indices_no_grupo)
        
        filhos_gerados = []

        # CENÁRIO A: Grupo Dentro do Limite -> Aceitamos como está.
        # Usamos o parâmetro dinâmico 'max_cluster_size'
        if tamanho_grupo <= params['max_cluster_size']:
            final_labels[indices_no_grupo] = next_label_id
            filhos_gerados.append(next_label_id)
            next_label_id += 1
            
            # Registra no mapa (Macro -> Filho Único)
            hierarchy_map[f"macro_{macro_id}"] = filhos_gerados
            continue

        # CENÁRIO B: Grupo GIGANTE -> Tentamos quebrar.
        logger.info(f"🔨 Refinando Macro-Grupo {macro_id} ({tamanho_grupo} itens > {params['max_cluster_size']})...")
        
        # Isolamos os vetores deste grupo
        sub_vectors = data[indices_no_grupo]
        
        # UMAP "Cirúrgico": n_neighbors=5 (Fixo para foco local), min_dist=0.1 (Fixo para separar).
        # HDBSCAN: Usa a régua 'micro_min_size' calculada dinamicamente.
        sub_labels = _run_umap_hdbscan(
            sub_vectors, 
            n_neighbors=5, 
            min_dist=0.1, 
            min_cluster_size=params['micro_min_size'], # <--- Dinâmico
            min_samples=1
        )
        
        sub_unique = set(sub_labels) - {-1}
        
        # Se não conseguiu quebrar (só achou 1 grupo ou tudo ruído), mantém original
        if len(sub_unique) <= 1:
            logger.info(f"   -> Grupo sólido (indivisível). Mantendo como único.")
            final_labels[indices_no_grupo] = next_label_id
            filhos_gerados.append(next_label_id)
            next_label_id += 1
        else:
            # Quebrou em vários sub-temas!
            logger.info(f"   -> SUCESSO! Dividido em {len(sub_unique)} sub-especialidades.")
            for sub_l in sub_unique:
                # Mapeia de volta para os índices originais
                mask_sub = (sub_labels == sub_l)
                indices_reais = indices_no_grupo[mask_sub]
                
                final_labels[indices_reais] = next_label_id
                filhos_gerados.append(next_label_id)
                next_label_id += 1
            
            # Nota: O que virou ruído (-1) na quebra fica como -1 no final
        
        # Salva a relação: Este Macro ID gerou estes Micro IDs
        hierarchy_map[f"macro_{macro_id}"] = filhos_gerados

    # --- Análise Final ---
    num_clusters = len(set(final_labels)) - (1 if -1 in final_labels else 0)
    noise_ratio = list(final_labels).count(-1) / total_items
    
    logger.info(f"🏁 Clusterização Final: {num_clusters} micro-grupos confirmados.")
    logger.info(f"   Taxa de Ruído Global: {noise_ratio:.1%}")

    return final_labels, hierarchy_map

def _get_dynamic_params(total_items: int):
    """
    Lógica Matemática para definir os parâmetros baseado no tamanho do dataset.
    Isso equilibra sistemas pequenos (200) e grandes (2000).
    """
    params = {}

    # 1. Régua MACRO (min_cluster_size)
    # Regra: Pelo menos 1% dos dados, mas nunca menos que 4 nem mais que 15.
    # Ex: 200 itens -> 1% = 2 -> Assume piso 4.
    # Ex: 1000 itens -> 1% = 10 -> Usa 10.
    raw_macro = int(total_items * 0.01) # 1%
    params['macro_min_size'] = max(4, min(15, raw_macro))

    # 2. Teto para Quebra (max_cluster_size)
    # Regra: Se um grupo tem mais de 10% dos dados ou mais de 50 itens, é gigante.
    # Ex: 200 itens -> 10% = 20. (Quebra se grupo > 20)
    # Ex: 1000 itens -> 10% = 100. (Mas travamos no teto 50).
    raw_max = int(total_items * 0.10) # 10%
    params['max_cluster_size'] = max(20, min(50, raw_max))

    # 3. Régua MICRO (min_cluster_size para sub-grupos)
    # Regra: Para detalhes, aceitamos grupos pequenos (3), mas em sistemas
    # gigantes, evitamos ruído subindo para 4.
    if total_items < 500:
        params['micro_min_size'] = 3
    else:
        params['micro_min_size'] = 4

    # 4. Vizinhos UMAP (n_neighbors) para Macro
    # Regra: Nunca maior que o total de itens - 1
    params['n_neighbors_macro'] = min(15, total_items - 1)

    return params

def _run_umap_hdbscan(data, n_neighbors, min_dist, min_cluster_size, min_samples):
    """
    Função interna auxiliar que permite rodar UMAP+HDBSCAN com parâmetros dinâmicos.
    """
    # Proteção: n_neighbors não pode ser maior que o número de dados - 1.
    safe_neighbors = min(n_neighbors, len(data) - 1)
    if safe_neighbors < 2: return np.full(len(data), -1)

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
    
    return clusterer.labels_

def get_vectors_from_qdrant_for_ids(ids_chamados: list[str]):
    pass