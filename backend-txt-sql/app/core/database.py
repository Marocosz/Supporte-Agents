# =============================================================================
# ARQUIVO DE GERENCIAMENTO DO BANCO DE DADOS
# =============================================================================

import logging
import psycopg2
from functools import lru_cache 
from langchain_community.utilities import SQLDatabase
from sqlalchemy import create_engine 
from .config import settings

logger = logging.getLogger(__name__)

TARGET_TABLES = ['tab_situacao_nota_logi']
TARGET_SCHEMA = 'dw'

def get_db_connection() -> SQLDatabase:
    """
    Cria a conexão principal do LangChain.
    """
    DATABASE_URI_FULL = (
        f"postgresql://{settings.DB_USER}:{settings.DB_PASS}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )
    
    SSL_ARGS = {"sslmode": "disable"}
    
    try:
        # OTIMIZAÇÃO CRÍTICA: pool_pre_ping=True
        # Isso verifica se a conexão está viva antes de executar a query.
        # Resolve o erro "server closed the connection unexpectedly".
        engine = create_engine(
            DATABASE_URI_FULL,
            connect_args=SSL_ARGS,
            pool_pre_ping=True, 
            pool_recycle=3600 
        )
        
        # sample_rows_in_table_info=0 para velocidade máxima (não faz SELECT * ao iniciar)
        db = SQLDatabase(
            engine=engine,
            schema=TARGET_SCHEMA, 
            include_tables=TARGET_TABLES,
            sample_rows_in_table_info=0 
        )
        
        logger.info(f"Conexão com o banco de dados (Schema: {TARGET_SCHEMA}) estabelecida com sucesso.")
        return db
    
    except Exception as e:
        logger.error(f"Falha ao conectar com o banco de dados (LangChain): {e}")
        raise

@lru_cache(maxsize=1)
def get_compact_db_schema() -> str:
    """
    Gera schema compacto (cacheado) para a IA.
    """
    conn = None
    try:
        logger.info("Gerando schema compacto do banco de dados (CACHE MISS - Executando query real)...")
        
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            dbname=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASS,
            port=settings.DB_PORT,
            sslmode='disable' 
        )
        cur = conn.cursor()
        
        schema_parts = []
        tables = TARGET_TABLES
        
        for table in tables:
            cur.execute(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = '{table}'
                AND table_schema = '{TARGET_SCHEMA}'
            """)
            columns = []
            rows = cur.fetchall()
            
            if not rows:
                logger.warning(f"A tabela '{TARGET_SCHEMA}.{table}' não foi encontrada.")
                continue

            for row in rows:
                column_name, data_type = row
                # Aspas duplas para evitar erros de case sensitivity
                columns.append(f'"{column_name}" ({data_type})')

            schema_parts.append(f"Tabela: {TARGET_SCHEMA}.{table}\nColunas: {', '.join(columns)}")
            
        cur.close()
        logger.info("Schema compacto gerado e armazenado em CACHE.")
        return "\n\n".join(schema_parts)
    except Exception as e:
        logger.error(f"Erro ao gerar schema compacto: {e}")
        return "Erro ao obter schema do banco de dados."
    finally:
        if conn:
            conn.close()

db_instance = get_db_connection()