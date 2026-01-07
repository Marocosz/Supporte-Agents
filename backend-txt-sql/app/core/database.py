# =============================================================================
# ARQUIVO DE GERENCIAMENTO DO BANCO DE DADOS
#
# Este módulo centraliza toda a interação com o banco de dados PostgreSQL.
# Ele é responsável por:
# 1. Criar uma instância de conexão que o LangChain pode usar para EXECUTAR queries.
# 2. Gerar uma representação de texto compacta do schema do banco para ser
#    enviada como CONTEXTO para o LLM, evitando erros de requisição muito grande.
# =============================================================================

import logging
import psycopg2
from functools import lru_cache # <--- OTIMIZAÇÃO: Cache de memória eficiente
from langchain_community.utilities import SQLDatabase
# Necessário para criar a engine e usar variáveis separadas.
from sqlalchemy import create_engine 
from .config import settings

# Obtém um logger específico para este módulo.
logger = logging.getLogger(__name__)

# Lista de tabelas que o sistema deve focar (Atualizado para o novo BD)
TARGET_TABLES = ['tab_situacao_nota_logi']
# Define o schema onde a tabela reside (Data Warehouse)
TARGET_SCHEMA = 'dw'

def get_db_connection() -> SQLDatabase:
    """
    Cria a conexão principal do LangChain, que será usada para EXECUTAR as queries SQL
    geradas pela IA.
    
    Esta função foi modificada para montar a URI a partir das variáveis separadas do .env.

    Returns:
        Uma instância de SQLDatabase configurada para o banco de dados do projeto.
    
    Raises:
        Exception: Se a conexão com o banco de dados falhar.
    """
    
    # 1. Monta a URI completa a partir das variáveis do .env
    DATABASE_URI_FULL = (
        f"postgresql://{settings.DB_USER}:{settings.DB_PASS}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )
    
    # 2. Configuração de SSL
    # ALTERADO: 'disable' para conexões locais ou IPs de rede interna que não suportam SSL.
    # Se for usar nuvem (Render/AWS) com SSL obrigatório, altere para 'require'.
    SSL_ARGS = {"sslmode": "disable"}
    
    try:
        # 3. Criamos a Engine explicitamente, passando os argumentos de conexão (SSL)
        engine = create_engine(
            DATABASE_URI_FULL,
            connect_args=SSL_ARGS
        )
        
        # 4. Criamos a instância SQLDatabase do LangChain usando a Engine customizada.
        # Atualizado: include_tables agora usa a lista TARGET_TABLES definida acima.
        # Adicionado: schema=TARGET_SCHEMA para indicar onde buscar as tabelas.
        
        # OTIMIZAÇÃO CRÍTICA DE VELOCIDADE:
        # sample_rows_in_table_info=0 -> Evita que o LangChain faça um SELECT * LIMIT X
        # toda vez que inicia. Como já passamos exemplos nos prompts, isso é desnecessário e lento.
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
    Gera uma string de schema muito compacta para guiar melhor a IA.
    Esta função se conecta ao banco e faz a leitura das colunas.
    
    OTIMIZAÇÃO: O decorador @lru_cache garante que esta função seja executada
    apenas UMA vez. Nas chamadas subsequentes, o resultado é retornado da memória.

    Returns:
        Uma string formatada com o esquema do banco de dados.
    """
    conn = None
    try:
        logger.info("Gerando schema compacto do banco de dados (CACHE MISS - Executando query real)...")
        
        # Conexão direta com psycopg2 para ler o schema
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            dbname=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASS,
            port=settings.DB_PORT,
            # ALTERADO: 'disable' para permitir conexão sem SSL na rede local
            sslmode='disable' 
        )
        cur = conn.cursor()
        
        schema_parts = []
        # Usa a lista definida no topo do arquivo
        tables = TARGET_TABLES
        
        for table in tables:
            # Consulta as colunas e tipos de dados de cada tabela.
            # Adicionado filtro pelo table_schema
            cur.execute(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = '{table}'
                AND table_schema = '{TARGET_SCHEMA}'
            """)
            columns = []
            rows = cur.fetchall()
            
            if not rows:
                logger.warning(f"A tabela '{TARGET_SCHEMA}.{table}' não foi encontrada ou não tem colunas acessíveis.")
                continue

            for row in rows:
                column_name, data_type = row
                
                # ALTERAÇÃO IMPORTANTE: Adicionamos aspas duplas ao redor do nome da coluna.
                # Isso ensina a IA a gerar queries como SELECT "VALOR" em vez de SELECT VALOR,
                # resolvendo erros de Case Sensitivity no PostgreSQL.
                columns.append(f'"{column_name}" ({data_type})')

            # Adiciona o nome do schema para garantir contexto correto
            schema_parts.append(f"Tabela: {TARGET_SCHEMA}.{table}\nColunas: {', '.join(columns)}")
            
        cur.close()
        logger.info("Schema compacto gerado e armazenado em CACHE.")
        return "\n\n".join(schema_parts)
    except Exception as e:
        logger.error(f"Erro ao gerar schema compacto: {e}")
        return "Erro ao obter schema do banco de dados."
    finally:
        # Fecha a conexão direta para liberar recursos.
        if conn:
            conn.close()

# Cria uma instância única da conexão do LangChain quando a aplicação é iniciada.
# Esta linha tentará se conectar ao banco imediatamente, levantando um erro se falhar.
db_instance = get_db_connection()