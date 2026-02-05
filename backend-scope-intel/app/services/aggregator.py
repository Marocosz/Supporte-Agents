# ==============================================================================
# ARQUIVO: app/services/aggregator.py
#
# OBJETIVO:
#   Agrupar e resumir estatisticamente os dados dos clusters encontrados.
#   Este módulo transforma uma lista de IDs brutos e Labels do HDBSCAN em 
#   objetos ricos com métricas (Top Serviços, Solicitantes, etc).
#
# PARTE DO SISTEMA:
#   Backend / Processamento de Dados (Analytics)
#
# RESPONSABILIDADES:
#   - Cruzar os dados originais (Records) com os Labels do Clustering
#   - Calcular contagens e estatísticas descritivas por grupo
#   - Selecionar amostras representativas de texto para envio à IA (Amostragem Inteligente)
#   - Calcular Insights de Negócio (Tendência, Sazonalidade, Concentração)
#
# COMUNICAÇÃO:
#   Recebe dados de: cluster_engine.py (Labels) e data_fetcher.py (Records)
#   Envia dados para: llm_agent.py (textos para análise) e run_pipeline.py (JSON final)
# ==============================================================================

from collections import Counter
import re
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def _get_smart_samples(texts: list[str], n: int = 10) -> tuple[list[str], list[str]]:
    """
    Retorna (amostras_inteligentes, top_keywords).
    Seleciona textos que contêm o maior número de palavras-chave frequentes do cluster.
    Isso evita pegar chamados 'outliers' ou vazios que não representam o grupo.
    """
    if not texts:
        return [], []

    # 1. Tokenização simples e contagem de palavras
    # Stopwords básicas (hardcoded para evitar dependência externa pesada)
    stopwords = {
        'de', 'a', 'o', 'que', 'e', 'do', 'da', 'em', 'um', 'para', 'com', 'nao', 'uma',
        'os', 'no', 'se', 'na', 'por', 'mais', 'as', 'dos', 'como', 'mas', 'ao', 'ele',
        'das', 'tem', 'seu', 'sua', 'ou', 'ser', 'quando', 'muito', 'nos', 'ja', 'eu',
        'tambem', 'só', 'pelo', 'pela', 'ate', 'isso', 'ela', 'entre', 'depois', 'sem',
        'mesmo', 'aos', 'seus', 'quem', 'nas', 'me', 'esse', 'eles', 'voce', 'essa',
        'num', 'nem', 'suas', 'meu', 'as', 'minha', 'sao', 'título', 'descrição', 'detalhada',
        'sistema', 'serviço', 'chamado', 'solicitação', 'incidente', 'ola', 'bom', 'dia', 'tarde'
    }
    
    all_words = []
    text_word_sets = [] # Lista de sets de palavras para cada texto (cache)

    for t in texts:
        # Lowercase + regex para pegar apenas palavras com > 2 letras
        words = re.findall(r'\b[a-zà-ú]{3,}\b', t.lower())
        filtered = [w for w in words if w not in stopwords]
        all_words.extend(filtered)
        text_word_sets.append(set(filtered))
    
    # 2. Identifica Top 15 palavras mais frequentes no cluster inteiro
    counter = Counter(all_words)
    top_keywords = [w for w, count in counter.most_common(15)]
    
    # 3. Pontua cada texto baseado na presença dessas keywords
    # Score = quantas keywords do Top 15 aparecem nesse texto
    scores = []
    for i, w_set in enumerate(text_word_sets):
        score = sum(1 for kw in top_keywords if kw in w_set)
        scores.append((score, texts[i]))
    
    # 4. Ordena pelo score (maior primeiro) e pega os top N
    scores.sort(key=lambda x: x[0], reverse=True)
    
    # Retorna os textos vencedores e as keywords para injetar no prompt
    best_texts = [item[1] for item in scores[:n]]
    
    # Se por acaso todos tiverem score 0, faz fallback para random (os primeiros da lista original)
    if not best_texts:
        best_texts = texts[:n]
        
    return best_texts, top_keywords

def consolidate_clusters(records: list[dict], cluster_labels: list[int], extra_meta_map: dict = None) -> list[dict]:
    """
    RECEBE:
        - records: Lista completa de dicionários com os dados brutos dos chamados.
        - cluster_labels: Lista de inteiros do mesmo tamanho.
        - extra_meta_map: (Opcional) Dict {index_original: {x, y, prob}}
    
    RETORNA:
        - Lista de dicionários, onde cada item representa um GRUPO CONSOLIDADO.
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
        # if label == -1:
        #    continue

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
        
        # 4. Amostragem Inteligente & Extração de Keywords (UPDATED)
        # Em vez de sample random, usamos a função inteligente
        textos_cluster = grupo['texto_vetor'].tolist()
        amostras, top_keywords = _get_smart_samples(textos_cluster, n=min(10, total))
        
        # 5. Lista de IDs para permitir "Drill-down" no Frontend
        ids_chamados = grupo['id_chamado'].tolist()
        
        # 5b. Monta lista rica com coordenadas para visualização (NOVO)
        chamados_viz = []
        if extra_meta_map:
            # grupo.index contem os índices originais da lista 'records'
            for idx_orig in grupo.index:
                rec_id = grupo.at[idx_orig, 'id_chamado']
                meta = extra_meta_map.get(idx_orig, {})
                chamados_viz.append({
                    "id": rec_id,
                    "x": meta.get("x", 0.0),
                    "y": meta.get("y", 0.0),
                    "prob": round(meta.get("prob", 0.0), 4)
                })

        # 6. Timeline (Evolução Temporal) & Sazonalidade (Dia da Semana)
        sazonalidade_data = []
        timeline_data = []
        tendencia_analise = {"tipo": "Estável", "variacao_pct": 0.0, "alerta": False}
        concentracao_analise = {"tipo": "Disperso", "ratio": 0.0}

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

            # --- TENDÊNCIA (Últimos 15 dias vs Anterior) ---
            try:
                # Agrupa por semana para suavizar
                ts_semanal = grupo.groupby(grupo['dt_temp'].dt.to_period('W')).size().sort_index()
                if len(ts_semanal) >= 2:
                    last_col = ts_semanal.iloc[-1]   # Semana mais recente
                    prev_col = ts_semanal.iloc[-2]   # Semana anterior
                    
                    # Evita divisão por zero
                    if prev_col > 0:
                        var_pct = ((last_col - prev_col) / prev_col) * 100
                    else:
                        var_pct = 100.0 if last_col > 0 else 0.0
                    
                    tipo_tend = "Estável"
                    alerta = False
                    if var_pct > 30: 
                        tipo_tend = "Crescente"
                        alerta = True 
                    elif var_pct < -30:
                        tipo_tend = "Decrescente"
                    
                    tendencia_analise = {
                        "tipo": tipo_tend,
                        "variacao_pct": round(var_pct, 1),
                        "alerta": alerta,
                        "detalhe": f"Volume {tipo_tend.lower()} de {prev_col} para {last_col} na última semana."
                    }
            except Exception as e:
                logger.warning(f"Erro ao calcular tendencia cluster {label}: {e}")

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
            
        # --- CONCENTRAÇÃO (Qtd Usuários Únicos / Total Chamados) ---
        if 'solicitante' in grupo.columns and total > 0:
            uniq_users = grupo['solicitante'].nunique()
            ratio = uniq_users / total # 1.0 = cada chamado é um user diferente (Massivo)
                                     # 0.1 = poucos users abrindo muito (Concentrado)
            
            tipo_conc = "Normal"
            if ratio < 0.2 and total > 5: # Ex: 10 chamados, 1 ou 2 usuarios
                tipo_conc = "Altamente Concentrado (Nicho)"
            elif ratio > 0.9:
                tipo_conc = "Massivo (Generalizado)"
                
            concentracao_analise = {
                "tipo": tipo_conc,
                "ratio": round(ratio, 2),
                "usuarios_unicos": uniq_users
            }

        # Monta o objeto intermediário que será enriquecido pela IA posteriormente
        cluster_data = {
            "cluster_id": int(label),
            "metricas": {
                "volume": int(total),
                "top_servicos": top_servicos,
                "top_subareas": top_subareas, 
                "top_solicitantes": top_solicitantes,
                "top_status": top_status, 
                "timeline": timeline_data,
                "sazonalidade": sazonalidade_data,
                "tendencia": tendencia_analise,        # NOVO INSIGHT
                "concentracao": concentracao_analise   # NOVO INSIGHT
            },
            "amostras_texto": amostras,    # Inteligente
            "top_keywords": top_keywords,  # Metadados para IA (NOVO)
            "ids_chamados": ids_chamados,
            "chamados_viz": chamados_viz   # NOVO: Dados ricos para plot
        }
        results.append(cluster_data)

    return results