# ==============================================================================
# ARQUIVO: scripts/run_pipeline.py
#
# OBJETIVO:
#   Script principal (Entrypoint) para rodar a análise de chamados em modo BATCH.
#   Orquestra todo o fluxo: SQL -> Vetor -> Clustering Hierárquico -> Naming IA (Pai/Filho) -> JSON.
#
# PARTE DO SISTEMA:
#   Scripts / Pipeline de Dados (Orquestrador)
#
# RESPONSABILIDADES:
#   - Controlar o fluxo de execução passo-a-passo (ETL -> ML -> IA)
#   - Gerenciar o estado assíncrono para chamadas paralelas à OpenAI (Performance)
#   - Estruturar o objeto JSON final com a árvore hierárquica (Pais e Filhos)
#   - Calcular métricas finais agregadas do Pai
#
# COMUNICAÇÃO:
#   Chama: data_fetcher, vectorizer, cluster_engine, aggregator, llm_agent
#   Gera: Arquivo JSON na pasta data_output/
# ==============================================================================

import sys
import os
import argparse
import json
import logging
import asyncio
from datetime import datetime
import numpy as np 

# Adiciona a raiz do projeto ao Python Path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.core.config import settings
from app.core.vector_store import vector_db

# Importa nossos serviços de domínio
from app.services import data_fetcher, vectorizer, cluster_engine, aggregator, llm_agent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def process_micro_cluster(child_id, child_obj):
    """
    Função auxiliar para processar um único micro-cluster de forma assíncrona.
    Retorna uma tupla (child_id, dados_atualizados)
    """
    try:
        analise_micro = await llm_agent.gerar_analise_micro_async(
            child_obj['amostras_texto'], 
            child_obj['metricas'].get('top_servicos'),
            child_obj.get('top_keywords') # Passando os metadados novos
        )
        
        child_obj['titulo'] = analise_micro['titulo']
        child_obj['descricao'] = analise_micro['descricao']
        child_obj['tags'] = analise_micro.get('tags', []) # NOVO: Tags da IA
        child_obj['analise_racional'] = analise_micro.get('analise_racional', "") # NOVO: Raciocinio da IA
        
        # Remove o campo pesado de amostras do filho final
        # Mas guardamos num campo temporário se o Pai precisar (embora no macro usemos título+descrição)
        # Por segurança, limpamos aqui para o JSON final, e o Pai usa o que já tem.
        # child_obj.pop('amostras_texto', None)   <-- MANTENDO para Frontend
        # child_obj.pop('top_keywords', None)     <-- MANTENDO para Frontend
        
        return child_id, child_obj
    except Exception as e:
        logger.error(f"Erro ao processar cluster {child_id}: {e}")
        return child_id, None

async def main(sistema: str, dias: int):
    start_time = datetime.now()
    logger.info(f"=== Iniciando Pipeline HIERÁRQUICO (ASYNC) para Sistema: {sistema} ===")

    db = SessionLocal()
    try:
        # 1. ETL e Vetorização 
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
            uid = vectorizer.generate_uuid_from_string(r['id_chamado'], sistema)
            if uid in vector_map:
                vectors_ordered.append(vector_map[uid])
                valid_records.append(r)
        
        logger.info(f"Vetores alinhados: {len(vectors_ordered)} prontos.")

        # 2. Clustering Hierárquico
        logger.info(">>> ETAPA 4: Executando Clustering Hierárquico (Macro -> Micro)...")
        micro_labels, hierarchy_map, params_used, coords_2d, final_probs = cluster_engine.perform_clustering(vectors_ordered)
        
        # Preparar metadados visuais para o aggregator
        extra_meta = {}
        for i in range(len(vectors_ordered)):
            # coords_2d é dict {index: [x,y]}
            c = coords_2d.get(i, [0.0, 0.0])
            extra_meta[i] = {
                "x": c[0],
                "y": c[1],
                "prob": final_probs[i]
            }

        # 3. Consolidar Dados dos FILHOS (Micro-Clusters)
        logger.info(">>> ETAPA 5: Consolidando Estatísticas dos Micro-Clusters...")
        
        # O aggregator gera stats para todos os micros encontrados nos labels
        clusters_raw_list = aggregator.consolidate_clusters(valid_records, micro_labels, extra_meta_map=extra_meta)
        
        # Separar quem é cluster válido e quem é ruído (-1)
        micro_clusters_data = {}
        noise_cluster_data = None
        
        for c in clusters_raw_list:
            cid = c['cluster_id']
            if cid == -1:
                noise_cluster_data = c
            else:
                micro_clusters_data[cid] = c
                
        # 4. Análise MICRO em Paralelo (Async)
        logger.info(f">>> ETAPA 6A: Disparando Análise IA para {len(micro_clusters_data)} Micro-Clusters em Paralelo...")
        
        tasks = []
        for cid, c_obj in micro_clusters_data.items():
            tasks.append(process_micro_cluster(cid, c_obj))
            
        # Executa tudo junto!
        results = await asyncio.gather(*tasks)
        
        # Atualiza o mapa com os resultados processados
        processed_micro_map = {}
        for res_id, res_obj in results:
            if res_obj:
                processed_micro_map[res_id] = res_obj
                
        logger.info(">>> Análise Micro concluída.")

        # 5. Montagem da Árvore e Naming MACRO (Pai/Filho)
        logger.info(">>> ETAPA 6B: Estruturando Árvore Macro...")
        
        final_clusters_tree = []
        
        # Iteramos sobre o mapa de hierarquia (Os Pais)
        for macro_key, children_ids in hierarchy_map.items():
            
            # Filtra filhos válidos que foram processados com sucesso
            lista_filhos_objs = []
            
            for child_id in children_ids:
                if child_id in processed_micro_map:
                    lista_filhos_objs.append(processed_micro_map[child_id])
            
            if not lista_filhos_objs:
                continue

            # --- Processar o PAI (Macro) ---
            
            # Caso Especial: Se o pai só tem 1 filho, ele vira o próprio filho (Lista Plana)
            # Acelera o processo e simplifica visualização
            if len(lista_filhos_objs) == 1:
                # logger.info(f"   > [FLAT] Cluster Único: {lista_filhos_objs[0]['titulo']}")
                final_clusters_tree.append(lista_filhos_objs[0])
                continue
                
            # Caso Padrão: Tem vários filhos, cria o Pai Agrupador
            # logger.info(f"   > [MACRO] Criando Categoria Pai para {len(lista_filhos_objs)} sub-grupos...")
            
            # Coleta Metadados dos Filhos para o Pai
            filhos_metadata = []
            for child in lista_filhos_objs:
                filhos_metadata.append({
                    "titulo": child['titulo'],
                    "descricao": child['descricao']
                })
            
            # CHAMA IA EXECUTIVA (MACRO)
            analise_pai = await llm_agent.gerar_analise_macro_async(filhos_metadata)
            
            # Agregação de Métricas do Pai
            all_ids_filhos = []
            agg_servicos = {}
            agg_solicitantes = {}
            agg_status = {}
            agg_subareas = {} 
            agg_timeline_map = {}
            agg_sazonalidade_map = {}
            agg_keywords = [] # Vamos agregar keywords tb

            volume_total = 0

            for child in lista_filhos_objs:
                volume_total += child['metricas']['volume']
                all_ids_filhos.extend(child.get('ids_chamados', []))
                agg_keywords.extend(child.get('top_keywords', []))
                
                for srv, qtd in child['metricas'].get('top_servicos', {}).items():
                    agg_servicos[srv] = agg_servicos.get(srv, 0) + qtd
                for sol, qtd in child['metricas'].get('top_solicitantes', {}).items():
                    agg_solicitantes[sol] = agg_solicitantes.get(sol, 0) + qtd
                for st, qtd in child['metricas'].get('top_status', {}).items():
                    agg_status[st] = agg_status.get(st, 0) + qtd
                for sub, qtd in child['metricas'].get('top_subareas', {}).items():
                    agg_subareas[sub] = agg_subareas.get(sub, 0) + qtd
                
                # Soma Timeline
                for time_item in child['metricas'].get('timeline', []):
                    # Suporte a dict ou objeto (defensivo)
                    if isinstance(time_item, dict):
                        mes = time_item.get('mes')
                        qtd = time_item.get('qtd')
                    else:
                        mes = getattr(time_item, 'mes', None)
                        qtd = getattr(time_item, 'qtd', 0)
                    
                    if mes:
                        agg_timeline_map[mes] = agg_timeline_map.get(mes, 0) + qtd
                    
                # Soma Sazonalidade
                for saz_item in child['metricas'].get('sazonalidade', []):
                    if isinstance(saz_item, dict):
                        dia = saz_item.get('dia')
                        qtd = saz_item.get('qtd')
                    else:
                        dia = getattr(saz_item, 'dia', None)
                        qtd = getattr(saz_item, 'qtd', 0)
                    
                    if dia:
                        agg_sazonalidade_map[dia] = agg_sazonalidade_map.get(dia, 0) + qtd

            # Top 5 Pai
            top_servicos_pai = dict(sorted(agg_servicos.items(), key=lambda x: x[1], reverse=True)[:5])
            top_solicitantes_pai = dict(sorted(agg_solicitantes.items(), key=lambda x: x[1], reverse=True)[:5])
            top_status_pai = dict(sorted(agg_status.items(), key=lambda x: x[1], reverse=True)[:5])
            top_subareas_pai = dict(sorted(agg_subareas.items(), key=lambda x: x[1], reverse=True)[:5])
            
            # Keywords Pai (Top 10 frequentes entre os filhos)
            from collections import Counter
            top_keywords_pai = [k for k, v in Counter(agg_keywords).most_common(15)]
            
            timeline_pai = [
                {"mes": m, "qtd": q} 
                for m, q in sorted(agg_timeline_map.items())
            ]
            
            # Ordenação de Sazonalidade (Seg -> Dom)
            dias_ordem = {'Seg': 0, 'Ter': 1, 'Qua': 2, 'Qui': 3, 'Sex': 4, 'Sab': 5, 'Dom': 6}
            sazonalidade_pai = [
                {"dia": d, "qtd": q}
                for d, q in sorted(agg_sazonalidade_map.items(), key=lambda x: dias_ordem.get(x[0], 99))
            ]
            
            macro_id_num = int(macro_key.split('_')[1])
            
            macro_obj = {
                "cluster_id": 10000 + macro_id_num, 
                "titulo": analise_pai['titulo'], 
                "descricao": analise_pai['descricao'],
                "analise_racional": analise_pai.get('analise_racional', ''), # NOVO: Raciocínio do Pai
                "tags": analise_pai.get('tags', []), 
                "top_keywords": top_keywords_pai, # Salvando também no pai
                "metricas": {
                    "volume": volume_total,
                    "top_servicos": top_servicos_pai,
                    "top_solicitantes": top_solicitantes_pai,
                    "top_status": top_status_pai,
                    "top_subareas": top_subareas_pai,
                    "timeline": timeline_pai,
                    "sazonalidade": sazonalidade_pai
                },
                "sub_clusters": lista_filhos_objs, 
                "ids_chamados": all_ids_filhos
            }
            
            final_clusters_tree.append(macro_obj)

        # --- 6. Tratamento do RUÍDO / Dispersos ---
        if noise_cluster_data:
            logger.info(f">>> Incluindo Grupo de Dispersos ({noise_cluster_data['metricas']['volume']} itens)...")
            
            # Formatamos manualmente para não gastar tokens, pois são dispersos
            noise_cluster_data['titulo'] = "Outros / Dispersos"
            noise_cluster_data['descricao'] = "Chamados que não apresentaram padrão claro de agrupamento com os demais."
            noise_cluster_data['tags'] = ["Variados", "Sem Padrão"]
            noise_cluster_data['analise_racional'] = "Este grupo contém incidentes heterogêneos que não atingiram a densidade mínima para formar um cluster coeso (Ruído Estatístico). Não refletem um problema sistêmico único."
            # noise_cluster_data.pop('amostras_texto', None) # MANTER AMOSTRAS (Pedido do user)
            
            # Adiciona ao final da lista
            final_clusters_tree.append(noise_cluster_data)

        # 7. Salvar Resultado (JSON Hierárquico)
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
                "total_grupos": len(final_clusters_tree), 
                "taxa_ruido": float(f"{noise_ratio:.4f}"),
                "clustering_params": params_used # SALVANDO OS PARÂMETROS
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
    
    # Executa o loop assíncrono
    asyncio.run(main(args.sistema, args.dias))