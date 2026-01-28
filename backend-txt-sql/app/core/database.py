# =============================================================================
# ARQUIVO DE GERENCIAMENTO DO BANCO DE DADOS
# =============================================================================

import logging
import psycopg2
from functools import lru_cache 
from sqlalchemy import create_engine, text
from langchain_community.utilities import SQLDatabase
from .config import settings

logger = logging.getLogger(__name__)

# Tabelas e Schema Alvo (Mantido Intacto)
TARGET_TABLES = ['tab_situacao_nota_logi']
TARGET_SCHEMA = 'dw'

# Variável global para manter o Singleton
_db_instance = None

def get_db_connection() -> SQLDatabase:
    """
    Cria a conexão principal do LangChain (Singleton).
    Garante reconexão automática em caso de queda.
    """
    global _db_instance
    
    if _db_instance is not None:
        return _db_instance

    logger.info("🔌 [DATABASE] Iniciando conexão com o Banco de Dados...")
    
    DATABASE_URI_FULL = (
        f"postgresql://{settings.DB_USER}:{settings.DB_PASS}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )
    
    SSL_ARGS = {"sslmode": "disable"}
    
    try:
        # OTIMIZAÇÃO CRÍTICA: pool_pre_ping=True
        engine = create_engine(
            DATABASE_URI_FULL,
            connect_args=SSL_ARGS,
            pool_pre_ping=True, 
            pool_recycle=3600 
        )
        
        # sample_rows_in_table_info=0 para velocidade máxima
        _db_instance = SQLDatabase(
            engine=engine,
            schema=TARGET_SCHEMA, 
            include_tables=TARGET_TABLES,
            sample_rows_in_table_info=0 
        )
        
        logger.info(f"✅ [DATABASE] Conexão com o schema '{TARGET_SCHEMA}' estabelecida com sucesso.")
        return _db_instance
    
    except Exception as e:
        logger.critical(f"❌ [DATABASE] Falha fatal ao conectar (LangChain): {e}")
        raise

# --- ADIÇÃO CRÍTICA: Função para Execução Direta (Retorna JSON Puro) ---
def run_query_as_dict(query: str) -> list:
    """
    Executa SQL e retorna LISTA DE DICIONÁRIOS REAIS.
    Essencial para o Frontend receber JSON estruturado e não string.
    """
    db = get_db_connection()
    try:
        with db._engine.connect() as connection:
            result = connection.execute(text(query))
            
            # Se não retorna linhas (ex: UPDATE), retorna vazio
            if not result.returns_rows:
                return []
            
            # Converte as linhas do SQLAlchemy (Mapping) para Dicionários Python
            # Isso garante que as colunas venham nomeadas: {"NOTA_FISCAL": 40908}
            data = [dict(row._mapping) for row in result]
            return data
            
    except Exception as e:
        logger.error(f"Erro na execução da query direta: {e}")
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