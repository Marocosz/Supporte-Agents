import pandas as pd
import logging

logger = logging.getLogger(__name__)

def consolidate_clusters(records: list[dict], cluster_labels: list[int]) -> list[dict]:
    """
    Cruza os dados originais com os labels gerados pelo HDBSCAN.
    Calcula as estatísticas (Top Solicitantes, Serviços, etc).
    """
    if not records or len(records) != len(cluster_labels):
        logger.error("Tamanho dos registros e labels não batem!")
        return []

    # Criamos um DataFrame temporário para facilitar a matemática
    df = pd.DataFrame(records)
    df['cluster_id'] = cluster_labels

    results = []

    # Iterar por cada grupo encontrado
    unique_labels = sorted(list(set(cluster_labels)))
    
    for label in unique_labels:
        if label == -1:
            continue # Pula o ruído por enquanto (ou processa separado)

        # Filtra apenas chamados deste grupo
        grupo = df[df['cluster_id'] == label]
        
        # 1. Estatísticas Básicas
        total = len(grupo)
        
        # 2. Top Serviços (Ex: "NFe": 10, "Estoque": 5)
        top_servicos = grupo['servico'].value_counts().head(5).to_dict()
        
        # 3. Top Solicitantes
        top_solicitantes = grupo['solicitante'].value_counts().head(5).to_dict()
        
        # 4. Amostra de Textos (Para enviar pro GPT depois)
        # Pegamos 5 textos aleatórios para a IA entender o contexto
        amostras = grupo['texto_vetor'].sample(n=min(5, total), random_state=42).tolist()
        
        # 5. Lista de IDs (Para auditoria/drill-down no frontend)
        ids_chamados = grupo['id_chamado'].tolist()

        # Monta o objeto pré-IA
        cluster_data = {
            "cluster_id": int(label),
            "metricas": {
                "volume": int(total),
                "top_servicos": top_servicos,
                "top_solicitantes": top_solicitantes
            },
            "amostras_texto": amostras,
            "ids_chamados": ids_chamados
        }
        results.append(cluster_data)

    return results