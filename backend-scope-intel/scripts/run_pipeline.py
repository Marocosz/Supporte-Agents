# ==============================================================================
# ARQUIVO: scripts/run_pipeline.py
#
# OBJETIVO:
#   Script principal (Entrypoint) para rodar a análise de chamados em modo BATCH.
#   Orquestra todos os micro-serviços (Extração -> Vetorização -> Clustering -> Resumo).
#
# COMO USAR:
#   python scripts/run_pipeline.py --sistema "Logix" --dias 30
#
# FLUXO DE EXECUÇÃO:
#   1. Conecta no MySQL
#   2. Baixa chamados recentes
#   3. Onde não tem vetor, chama OpenAI e salva no Qdrant
#   4. Pega todos os vetores e roda HDBSCAN para achar grupos
#   5. Cruza grupos com dados de negócio (Top Serviços, etc)
#   6. Pede pro GPT-4 dar nome aos grupos
#   7. Salva um JSON final com o relatório de inteligência
# ==============================================================================

import sys
import os
import argparse
import json
import logging
from datetime import datetime

# Adiciona a raiz do projeto ao Python Path para importar 'app' corretamente
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.core.config import settings
from app.core.vector_store import vector_db

# Importa nossos serviços de domínio
from app.services import data_fetcher, vectorizer, cluster_engine, aggregator, llm_agent

# Configuração de Log para ver no terminal o que está acontecendo
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main(sistema: str, dias: int):
    """
    Função Mestra que roda o pipeline passo-a-passo.
    Se um passo falhar (exception), o processo para.
    """
    start_time = datetime.now()
    logger.info(f"=== Iniciando Pipeline para Sistema: {sistema} ===")

    # 1. Conexão com Banco SQL
    # Criamos a sessão aqui e garantimos o fechamento no 'finally'
    db = SessionLocal()
    try:
        # A. Buscar Dados Brutos (ETL Extraction)
        # ---------------------------------------
        logger.info(">>> ETAPA 1: Buscando dados no MySQL...")
        records = data_fetcher.fetch_chamados(db, sistema, dias_atras=dias)
        
        if not records:
            logger.error("Pipeline abortado: Sem dados encontrados.")
            return

        # B. Vetorização (ETL Transformation / Embedding)
        # -----------------------------------------------
        # Esta função é inteligente: ela gera IDs únicos e salva no Qdrant.
        logger.info(">>> ETAPA 2: Gerando/Recuperando Vetores...")
        vectorizer.process_and_vectorize(records)
        
        # C. Recuperar Vetores da Memória (Data Preparation for ML)
        # ---------------------------------------------------------
        # O HDBSCAN roda na memória (RAM), então precisamos puxar os vetores do Qdrant.
        # Embora tenhamos os dados em 'records', precisamos garantir que a ordem dos vetores
        # esteja 100% alinhada para não misturar os IDs depois.
        
        logger.info(">>> ETAPA 3: Preparando dados para Clustering...")
        all_vectors_qdrant = vector_db.get_all_vectors()
        
        # Otimização: Criar mapa {id -> vetor} para acesso O(1)
        vector_map = {point.id: point.vector for point in all_vectors_qdrant}
        
        # Montar listas alinhadas (Records <-> Vetores)
        vectors_ordered = []
        valid_records = [] # Apenas registros que realmente têm vetor (segurança)
        
        for r in records:
            # Recalcula o UUID para bater com o ID do Qdrant
            uid = vectorizer.generate_uuid_from_string(r['id_chamado'])
            if uid in vector_map:
                vectors_ordered.append(vector_map[uid])
                valid_records.append(r)
        
        logger.info(f"Vetores alinhados: {len(vectors_ordered)} prontos para clusterização.")

        # D. Clustering (Machine Learning / HDBSCAN)
        # ------------------------------------------
        # Aqui o algoritmo "descobre" os grupos baseados na matemática.
        logger.info(">>> ETAPA 4: Executando HDBSCAN...")
        labels, noise_ratio = cluster_engine.perform_clustering(vectors_ordered)
        
        # E. Agregação e Estatística (Data Analysis)
        # ------------------------------------------
        # Transforma "Grupo 1" em "Grupo 1: 50 chamados, NFe, Erro XML..."
        logger.info(">>> ETAPA 5: Consolidando Estatísticas...")
        clusters_raw = aggregator.consolidate_clusters(valid_records, labels)
        
        # F. Rotulagem Semântica (Generative AI)
        # --------------------------------------
        # O passo mais caro e lento. Enviamos amostras pro GPT entender o que é o grupo.
        logger.info(f">>> ETAPA 6: Chamando OpenAI para nomear {len(clusters_raw)} grupos...")
        final_clusters = []
        
        for cluster in clusters_raw:
            # Chama o GPT-4 passando as amostras de texto
            # A função já trata o cluster -1 (ruído) internamente
            info_ia = llm_agent.summarize_cluster(cluster['cluster_id'], cluster['amostras_texto'])
            
            # Mescla o resultado da IA (Titulo/Descricao) com as métricas do Python
            cluster_final = {**cluster, **info_ia}
            
            # Limpeza: Removemos as amostras de texto originais gigantes para o JSON final ficar leve
            del cluster_final['amostras_texto'] 
            
            final_clusters.append(cluster_final)
            print(f"   > Grupo {cluster['cluster_id']}: {info_ia['titulo']}")

        # G. Salvar Resultado (Persistência)
        # ----------------------------------
        # Salva em JSON para ser consumido pelo Frontend ou Dashboard depois.
        output_filename = f"analise_{sistema}_{datetime.now().strftime('%Y%m%d')}.json"
        output_path = os.path.join(settings.OUTPUT_DIR, output_filename)
        
        os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
        
        final_json = {
            "metadata": {
                "sistema": sistema,
                "data_analise": datetime.now().isoformat(),
                "periodo_dias": dias,
                "total_chamados": len(valid_records),
                "total_grupos": len(final_clusters),
                "taxa_ruido": float(f"{noise_ratio:.4f}") # Percentual de chamados únicos (0.0 a 1.0)
            },
            "clusters": final_clusters
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_json, f, indent=2, ensure_ascii=False)
            
        logger.info(f"=== SUCESSO! Análise salva em: {output_path} ===")
        logger.info(f"Tempo total: {datetime.now() - start_time}")

    finally:
        # Garante que a conexão com o MySQL seja devolvida ao pool
        db.close()

if __name__ == "__main__":
    # Configuração da Interface de Linha de Comando (CLI)
    parser = argparse.ArgumentParser(description='Scope Intelligence - Pipeline Batch')
    parser.add_argument('--sistema', type=str, required=True, help='Nome do sistema (Ex: Logix, Protheus)')
    parser.add_argument('--dias', type=int, default=180, help='Quantos dias atrás analisar (Padrão: 180)')
    
    args = parser.parse_args()
    
    main(args.sistema, args.dias)