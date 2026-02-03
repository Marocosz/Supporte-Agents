# ==============================================================================
# ARQUIVO: scripts/run_pipeline.py
#
# OBJETIVO:
#   Script principal (Entrypoint) para rodar a análise de chamados em modo BATCH.
#   Orquestra: SQL -> Vetor -> Clustering Hierárquico -> Naming IA (Pai/Filho) -> JSON.
# ==============================================================================

import sys
import os
import argparse
import json
import logging
from datetime import datetime
import numpy as np # Import necessário para sampling

# Adiciona a raiz do projeto ao Python Path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.core.config import settings
from app.core.vector_store import vector_db

# Importa nossos serviços de domínio
from app.services import data_fetcher, vectorizer, cluster_engine, aggregator, llm_agent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main(sistema: str, dias: int):
    start_time = datetime.now()
    logger.info(f"=== Iniciando Pipeline HIERÁRQUICO para Sistema: {sistema} ===")

    db = SessionLocal()
    try:
        # 1. ETL e Vetorização (Mantido igual)
        logger.info(">>> ETAPA 1: Buscando dados no MySQL...")
        records = data_fetcher.fetch_chamados(db, sistema, dias_atras=dias)
        
        if not records:
            logger.error("Pipeline abortado: Sem dados encontrados.")
            return

        logger.info(">>> ETAPA 2: Gerando/Recuperando Vetores...")
        vectorizer.process_and_vectorize(records)
        
        logger.info(">>> ETAPA 3: Preparando dados...")
        all_vectors_qdrant = vector_db.get_all_vectors()
        vector_map = {point.id: point.vector for point in all_vectors_qdrant}
        
        vectors_ordered = []
        valid_records = []
        
        for r in records:
            uid = vectorizer.generate_uuid_from_string(r['id_chamado'])
            if uid in vector_map:
                vectors_ordered.append(vector_map[uid])
                valid_records.append(r)
        
        logger.info(f"Vetores alinhados: {len(vectors_ordered)} prontos.")

        # --- MUDANÇA PRINCIPAL AQUI ---
        
        # 2. Clustering Hierárquico
        logger.info(">>> ETAPA 4: Executando Clustering Hierárquico (Macro -> Micro)...")
        # O engine agora retorna DUAS coisas: labels finais (micro) e o mapa da árvore
        micro_labels, hierarchy_map = cluster_engine.perform_clustering(vectors_ordered)
        
        # 3. Consolidar Dados dos FILHOS (Micro-Clusters)
        logger.info(">>> ETAPA 5: Consolidando Estatísticas dos Micro-Clusters...")
        
        # O aggregator funciona bem com lista plana. Ele vai gerar stats para todos os micros.
        # clusters_raw agora contém a lista de todos os "filhos" (folhas da árvore).
        clusters_raw_list = aggregator.consolidate_clusters(valid_records, micro_labels)
        
        # Transformar em dicionário para acesso rápido pelo ID: { 12: {dados...}, 13: {dados...} }
        micro_clusters_data = {c['cluster_id']: c for c in clusters_raw_list}
        
        # 4. Montagem da Árvore e Naming (IA)
        logger.info(">>> ETAPA 6: Estruturando Árvore e Chamando OpenAI...")
        
        final_clusters_tree = []
        
        # Iteramos sobre o mapa de hierarquia (Os Pais)
        # hierarchy_map ex: { "macro_0": [0, 1, 2], "macro_1": [3] }
        
        for macro_key, children_ids in hierarchy_map.items():
            
            # Filtra filhos válidos (exclui ruído -1 se tiver entrado na lista)
            valid_children = [cid for cid in children_ids if cid in micro_clusters_data]
            if not valid_children:
                continue
                
            # --- A. Processar os FILHOS (Micro - Visão Técnica) ---
            lista_filhos_objs = []
            todos_textos_do_pai = [] 
            titulos_filhos = []
            
            for child_id in valid_children:
                child_obj = micro_clusters_data[child_id]
                
                # CHAMA IA TÉCNICA (MICRO)
                # logger.info(f"   > [MICRO] Analisando Cluster {child_id}...") # Comentado para menos spam no log
                analise_micro = llm_agent.gerar_analise_micro(
                    child_obj['amostras_texto'], 
                    child_obj['metricas'].get('top_servicos')
                )
                
                child_obj['titulo'] = analise_micro['titulo']
                child_obj['descricao'] = analise_micro['descricao']
                
                # Remove o campo pesado de amostras do filho final
                amostras_backup = child_obj.pop('amostras_texto', [])
                
                lista_filhos_objs.append(child_obj)
                titulos_filhos.append(analise_micro['titulo'])
                todos_textos_do_pai.extend(amostras_backup) # Acumula para o pai ler

            # --- B. Processar o PAI (Macro - Visão Executiva) ---
            
            # Caso Especial: Se o pai só tem 1 filho, ele vira o próprio filho (Lista Plana)
            if len(lista_filhos_objs) == 1:
                logger.info(f"   > [FLAT] Cluster Único: {lista_filhos_objs[0]['titulo']}")
                final_clusters_tree.append(lista_filhos_objs[0])
                continue
                
            # Caso Padrão: Tem vários filhos, cria o Pai Agrupador
            logger.info(f"   > [MACRO] Criando Categoria Pai para {len(valid_children)} sub-grupos...")
            
            # 1. Agregação de Texto para Amostragem (Item 3 - Safer Sampling)
            # Usamos list comprehension para filtrar vazios e garantir que é lista
            import random
            amostra_pai = []
            if todos_textos_do_pai:
                qtd_amostra = min(5, len(todos_textos_do_pai))
                amostra_pai = random.sample(todos_textos_do_pai, qtd_amostra)
            
            # CHAMA IA EXECUTIVA (MACRO)
            analise_pai = llm_agent.gerar_analise_macro(amostra_pai, titulos_filhos)
            
            # 2. Agregação de Métricas e IDs (Item 1 - Frontend Safety)
            # Acumula dados dos filhos para o Pai não ficar "vazio" no Dashboard
            all_ids_filhos = []
            agg_servicos = {}
            agg_solicitantes = {}
            volume_total = 0

            for child in lista_filhos_objs:
                volume_total += child['metricas']['volume']
                all_ids_filhos.extend(child.get('ids_chamados', []))
                
                # Soma Serviços
                for srv, qtd in child['metricas'].get('top_servicos', {}).items():
                    agg_servicos[srv] = agg_servicos.get(srv, 0) + qtd
                    
                # Soma Solicitantes
                for sol, qtd in child['metricas'].get('top_solicitantes', {}).items():
                    agg_solicitantes[sol] = agg_solicitantes.get(sol, 0) + qtd

            # Pega os Top 5 acumulados para o Pai
            top_servicos_pai = dict(sorted(agg_servicos.items(), key=lambda x: x[1], reverse=True)[:5])
            top_solicitantes_pai = dict(sorted(agg_solicitantes.items(), key=lambda x: x[1], reverse=True)[:5])
            
            # Gera ID fictício para o Pai (ex: 10000 + ID original)
            macro_id_num = int(macro_key.split('_')[1])
            
            macro_obj = {
                "cluster_id": 10000 + macro_id_num, 
                "titulo": analise_pai['titulo'], 
                "descricao": analise_pai['descricao'],
                "metricas": {
                    "volume": volume_total,
                    "top_servicos": top_servicos_pai,     # Agora preenchido!
                    "top_solicitantes": top_solicitantes_pai, # Agora preenchido!
                    "timeline": [] # Timeline agregada é complexa, deixamos vazia por enqto
                },
                "sub_clusters": lista_filhos_objs, 
                "ids_chamados": all_ids_filhos # <--- CRÍTICO: Frontend agora consegue clicar no Pai
            }
            
            logger.info(f"     -> Título Pai: {macro_obj['titulo']}")
            final_clusters_tree.append(macro_obj)

        # 5. Salvar Resultado (JSON Hierárquico)
        output_filename = f"analise_{sistema}_{datetime.now().strftime('%Y%m%d')}.json"
        output_path = os.path.join(settings.OUTPUT_DIR, output_filename)
        
        os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
        
        # Calcular ruído final
        total_items = len(vectors_ordered)
        noise_count = list(micro_labels).count(-1)
        noise_ratio = noise_count / total_items if total_items > 0 else 0

        final_json = {
            "metadata": {
                "sistema": sistema,
                "data_analise": datetime.now().isoformat(),
                "periodo_dias": dias,
                "total_chamados": len(valid_records),
                "total_grupos": len(final_clusters_tree), # Conta grupos raiz (Pais + Filhos Solteiros)
                "taxa_ruido": float(f"{noise_ratio:.4f}")
            },
            "clusters": final_clusters_tree
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_json, f, indent=2, ensure_ascii=False)
            
        logger.info(f"=== SUCESSO! Análise HIERÁRQUICA salva em: {output_path} ===")
        logger.info(f"Tempo total: {datetime.now() - start_time}")

    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Scope Intelligence - Pipeline Batch')
    parser.add_argument('--sistema', type=str, required=True)
    parser.add_argument('--dias', type=int, default=180)
    args = parser.parse_args()
    
    main(args.sistema, args.dias)