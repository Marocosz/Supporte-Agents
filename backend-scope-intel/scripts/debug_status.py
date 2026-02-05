
# ==============================================================================
# ARQUIVO: scripts/debug_status.py
#
# OBJETIVO:
#   Script auxiliar paara investigar o conteúdo real de colunas no banco de dados.
#   Útil quando uma coluna parece vazia ou com formato inesperado.
#
# PARTE DO SISTEMA:
#   Scripts / Diagnóstico
#
# RESPONSABILIDADES:
#   - Consultar registros brutos via data_fetcher
#   - Exibir tipos de dados e valores únicos (Cardinalidade)
#   - Ajudar a entender por que um campo (ex: status) não está aparecendo nos relatórios
# ==============================================================================

import sys
import os
import logging
import pandas as pd

# Adiciona a raiz do projeto ao Python Path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.services import data_fetcher

# Config básica de log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_status_column():
    sistema = 'NEW TRACKING' 
    dias = 180 # Aumentei para 180 dias para ter mais chance de ter dados
    
    db = SessionLocal()
    try:
        logger.info(f"START_DEBUG: Buscando dados para {sistema}...")
        records = data_fetcher.fetch_chamados(db, sistema, dias_atras=dias)
        
        if not records:
            logger.error("RESULT: Nenhum registro encontrado.")
            return

        logger.info(f"RESULT: Total registros: {len(records)}")
        
        # Pega o primeiro registro para ver as chaves
        first_record = records[0]
        
        # Verifica se 'status' está presente
        if 'status' in first_record:
            val = first_record['status']
            logger.info(f"RESULT: Status do primeiro registro: '{val}' (Tipo: {type(val)})")
        else:
            logger.error("RESULT: CHAVE 'status' NÃO ENCONTRADA nos registros!")
            
        # Análise de valores únicos usando DataFrame
        df = pd.DataFrame(records)
        if 'status' in df.columns:
            # Força conversão para string para ver o que tem
            df['status'] = df['status'].astype(str)
            unique_vals = df['status'].unique()
            logger.info(f"RESULT: Valores unicos: {unique_vals}")
            
            # Frequencia
            counts = df['status'].value_counts()
            logger.info(f"RESULT: Contagem top 5: {counts.head(5).to_dict()}")
        else:
            logger.error("RESULT: Coluna 'status' não existe no DataFrame.")
            
    except Exception as e:
        logger.error(f"Erro no debug: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    debug_status_column()
