import sys
import os
import argparse
import json
import logging
from datetime import datetime

# Adiciona a raiz do projeto ao Python Path para importar 'app'
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.core.config import settings
from app.core.vector_store import vector_db

# Importa nossos serviços
from app.services import data_fetcher, vectorizer, cluster_engine, aggregator, llm_agent

# Configuração de Log para ver no terminal
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main(sistema: str, dias: int):
    start_time = datetime.now()
    logger.info(f"=== Iniciando Pipeline para Sistema: {sistema} ===")

    # 1. Conexão com Banco SQL
    db = SessionLocal()
    try:
        # A. Buscar Dados Brutos
        logger.info(">>> ETAPA 1: Buscando dados no MySQL...")
        records = data_fetcher.fetch_chamados(db, sistema, dias_atras=dias)
        
        if not records:
            logger.error("Pipeline abortado: Sem dados encontrados.")
            return

        # B. Vetorização (Cache Inteligente no Qdrant)
        logger.info(">>> ETAPA 2: Gerando/Recuperando Vetores...")
        vectorizer.process_and_vectorize(records)
        
        # C. Recuperar Vetores da Memória (Para o Clustering)
        # Como o HDBSCAN precisa dos vetores na mão, buscamos do Qdrant
        # (Isso garante que estamos usando o que foi salvo/cacheado)
        ids_para_busca = [vectorizer.generate_uuid_from_string(r['id_chamado']) for r in records]
        
        # Fazendo scroll/retrieve dos vetores (Simulação simplificada)
        # Em produção, faríamos um 'retrieve' em lote. Aqui, para o MVP,
        # vamos confiar que a ordem se mantém ou buscar um a um.
        # *Otimização:* Para não complicar o código de retrieve agora,
        # vamos regenerar o embedding se não for muito caro, OU (Melhor)
        # usar a função search_vectors que criamos no vector_store mas adaptar para retrieve by ID.
        
        # Vamos usar uma abordagem direta: Buscar todos os pontos da coleção e filtrar na memória 
        # (Funciona bem para até ~10k chamados).
        logger.info(">>> ETAPA 3: Preparando dados para Clustering...")
        all_vectors_qdrant = vector_db.get_all_vectors()
        
        # Criar mapa {id_qdrant: vetor}
        vector_map = {point.id: point.vector for point in all_vectors_qdrant}
        
        # Montar lista de vetores alinhada com 'records'
        vectors_ordered = []
        valid_records = [] # Registros que realmente tem vetor
        
        for r in records:
            uid = vectorizer.generate_uuid_from_string(r['id_chamado'])
            if uid in vector_map:
                vectors_ordered.append(vector_map[uid])
                valid_records.append(r)
        
        logger.info(f"Vetores alinhados: {len(vectors_ordered)} prontos para clusterização.")

        # D. Clustering (HDBSCAN)
        logger.info(">>> ETAPA 4: Executando HDBSCAN...")
        labels = cluster_engine.perform_clustering(vectors_ordered)
        
        # E. Agregação (Matemática)
        logger.info(">>> ETAPA 5: Consolidando Estatísticas...")
        clusters_raw = aggregator.consolidate_clusters(valid_records, labels)
        
        # F. Rotulagem (IA Generativa)
        logger.info(f">>> ETAPA 6: Chamando OpenAI para nomear {len(clusters_raw)} grupos...")
        final_clusters = []
        
        for cluster in clusters_raw:
            # Chama o GPT-4 passando as amostras de texto
            info_ia = llm_agent.summarize_cluster(cluster['cluster_id'], cluster['amostras_texto'])
            
            # Mescla o resultado da IA com as métricas do Python
            cluster_final = {**cluster, **info_ia}
            
            # Removemos as amostras de texto grandes para o JSON final ficar leve
            del cluster_final['amostras_texto'] 
            
            final_clusters.append(cluster_final)
            print(f"   > Grupo {cluster['cluster_id']}: {info_ia['titulo']}")

        # G. Salvar Resultado
        output_filename = f"analise_{sistema}_{datetime.now().strftime('%Y%m%d')}.json"
        output_path = os.path.join(settings.OUTPUT_DIR, output_filename)
        
        # Garantir que pasta existe
        os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
        
        final_json = {
            "metadata": {
                "sistema": sistema,
                "data_analise": datetime.now().isoformat(),
                "periodo_dias": dias,
                "total_chamados": len(valid_records),
                "total_grupos": len(final_clusters)
            },
            "clusters": final_clusters
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_json, f, indent=2, ensure_ascii=False)
            
        logger.info(f"=== SUCESSO! Análise salva em: {output_path} ===")
        logger.info(f"Tempo total: {datetime.now() - start_time}")

    finally:
        db.close()

if __name__ == "__main__":
    # Configuração dos Argumentos de Linha de Comando
    parser = argparse.ArgumentParser(description='Ticket Intel AI - Pipeline Batch')
    parser.add_argument('--sistema', type=str, required=True, help='Nome do sistema (Ex: Logix, Protheus)')
    parser.add_argument('--dias', type=int, default=180, help='Quantos dias atrás analisar (Padrão: 180)')
    
    args = parser.parse_args()
    
    main(args.sistema, args.dias)