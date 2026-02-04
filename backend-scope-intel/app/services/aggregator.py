# ==============================================================================
# ARQUIVO: app/services/aggregator.py
#
# OBJETIVO:
#   Agrupar e resumir estatisticamente os dados dos clusters encontrados.
#   Este módulo transforma uma lista de IDs brutos e Labels do HDBSCAN em 
#   objetos ricos com métricas (Top Serviços, Solicitantes, etc).
#
# RESPONSABILIDADES:
#   - Cruzar os dados originais (Records) com os Labels do Clustering
#   - Calcular contagens e estatísticas descritivas por grupo
#   - Selecionar amostras representativas de texto para envio à IA
#
# COMUNICAÇÃO:
#   Recebe dados de: cluster_engine.py (Labels) e data_fetcher.py (Records)
#   Envia dados para: llm_agent.py (textos para análise) e run_pipeline.py (JSON final)
# ==============================================================================

import pandas as pd
import logging

logger = logging.getLogger(__name__)

def consolidate_clusters(records: list[dict], cluster_labels: list[int]) -> list[dict]:
    """
    RECEBE:
        - records: Lista completa de dicionários com os dados brutos dos chamados.
        - cluster_labels: Lista de inteiros do mesmo tamanho, onde cada índice corresponde
          ao grupo do chamado na mesma posição.
    
    RETORNA:
        - Lista de dicionários, onde cada item representa um GRUPO CONSOLIDADO contendo:
          volume, top ofensores, amostras de texto e metadados.
    
    LÓGICA:
        1. Cria um DataFrame pandas unindo dados + label.
        2. Itera por cada Label único (excluindo ruído -1 se necessário).
        3. Calcula estatísticas de frequência (Top 5 Serviços, Quem mais abre chamado, etc).
        4. Separa textos aleatórios para servir de contexto para a IA Generativa.
    """
    if not records or len(records) != len(cluster_labels):
        logger.error("Tamanho dos registros e labels não batem!")
        return []

    # Cria DataFrame temporário para facilitar manipulação e cálculos de frequência
    df = pd.DataFrame(records)
    df['cluster_id'] = cluster_labels

    results = []

    # Identifica quais grupos foram formados
    unique_labels = sorted(list(set(cluster_labels)))
    
    for label in unique_labels:
        # Pula o grupo de Ruído (-1) se a regra de negócio for focar apenas em padrões fortes.
        # Caso queira analisar o ruído, remover este if.
        if label == -1:
            continue

        # Filtra apenas os chamados pertencentes ao grupo atual da iteração
        grupo = df[df['cluster_id'] == label].copy()
        
        # --- CÁLCULO DE MÉTRICAS ---
        
        # 1. Volume total do problema
        total = len(grupo)
        
        # 2. Identifica quais serviços/módulos são mais afetados neste grupo
        top_servicos = grupo['servico'].value_counts().head(5).to_dict()
        
        # 3. Identifica quem são os usuários que mais sofrem com este problema
        top_solicitantes = grupo['solicitante'].value_counts().head(5).to_dict()
        
        # 3a. Identifica estatística de Status (Abertos vs Fechados)
        top_status = {}
        if 'status' in grupo.columns:
            # Preenche nulos e vazios para contabilizar tudo
            status_series = grupo['status'].fillna('Não Informado').replace('', 'Não Informado')
            # Opcional: Normalizar texto (ex: 'finalizado' -> 'Finalizado')
            status_series = status_series.apply(lambda x: x.title() if isinstance(x, str) else str(x))
            top_status = status_series.value_counts().head(5).to_dict()

        # 3b. Identifica estatística de Sub-Área (Mais granular que serviço)
        top_subareas = {}
        if 'subarea' in grupo.columns:
            top_subareas = grupo['subarea'].value_counts().head(5).to_dict()
        
        # 4. Seleção de Amostra para IA (Context Window)
        # Seleciona até 5 textos aleatórios para evitar viés de ordem (ex: pegar só antigos ou só novos)
        # O random_state garante que sempre pegaremos as mesmas amostras se rodar de novo (determinístico)
        amostras = grupo['texto_vetor'].sample(n=min(5, total), random_state=42).tolist()
        
        # 5. Lista de IDs para permitir "Drill-down" no Frontend (ver os chamados reais)
        ids_chamados = grupo['id_chamado'].tolist()

        # 6. Timeline (Evolução Temporal) & Sazonalidade (Dia da Semana)
        sazonalidade_data = []
        timeline_data = []

        if 'data_abertura' in grupo.columns:
             # Garante formato datetime
            grupo['dt_temp'] = pd.to_datetime(grupo['data_abertura'], errors='coerce')
            
            # --- TIMELINE (Mês) ---
            timeline_series = grupo.groupby(grupo['dt_temp'].dt.to_period('M')).size()
            timeline_data = [
                {"mes": str(period), "qtd": int(count)} 
                for period, count in timeline_series.items()
            ]
            timeline_data.sort(key=lambda x: x['mes'])

            # --- SAZONALIDADE (Dia da Semana) ---
            # 0=Segunda, 6=Domingo
            dias_map = {0: 'Seg', 1: 'Ter', 2: 'Qua', 3: 'Qui', 4: 'Sex', 5: 'Sab', 6: 'Dom'}
            sazonal_counts = grupo['dt_temp'].dt.dayofweek.value_counts().sort_index()
            
            sazonalidade_data = [
                {"dia": dias_map.get(idx, str(idx)), "qtd": int(val)}
                for idx, val in sazonal_counts.items()
            ]
        else:
            timeline_data = []
            sazonalidade_data = []

        # Monta o objeto intermediário que será enriquecido pela IA posteriormente
        cluster_data = {
            "cluster_id": int(label),
            "metricas": {
                "volume": int(total),
                "top_servicos": top_servicos,
                "top_subareas": top_subareas, 
                "top_solicitantes": top_solicitantes,
                "top_status": top_status, # NOVO
                "timeline": timeline_data,
                "sazonalidade": sazonalidade_data 
            },
            "amostras_texto": amostras, # Será consumido pelo llm_agent
            "ids_chamados": ids_chamados
        }
        results.append(cluster_data)

    return results