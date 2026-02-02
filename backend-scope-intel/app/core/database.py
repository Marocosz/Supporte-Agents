# ==============================================================================
# ARQUIVO: app/core/database.py
#
# OBJETIVO:
#   Gerenciar a conexão com o Banco de Dados Relacional (MySQL/PostgreSQL).
#   Fornece a sessão (Session) que será usada pelos Services para executar queries.
#
# RESPONSABILIDADES:
#   - Criar o Engine do SQLAlchemy (Pool de conexões)
#   - Configurar a fábrica de sessões (SessionLocal)
#   - Fornecer injeção de dependência para uso seguro (abrir/fechar conexões)
# ==============================================================================

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# 1. Criação do Engine (O "Motor" de Conexão)
# -------------------------------------------
# pool_pre_ping=True:
#   Verifica se a conexão ainda está viva antes de entregá-la.
#   Essencial para evitar erros de "MySQL has gone away" se a conexão ficar ociosa.
#
# pool_size=10:
#   Mantém até 10 conexões abertas permanentemente no pool.
#   Melhora performance pois evita o custo de handshake TCP a cada query.
#
# max_overflow=20:
#   Se as 10 conexões estiverem ocupadas, permite criar mais 20 temporárias
#   antes de começar a rejeitar novas requisições.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# 2. Fábrica de Sessões
# ---------------------
# autocommit=False:
#   Segurança transacional. Obriga o desenvolvedor a chamar session.commit() explicitamente
#   apenas quando tiver certeza que tudo deu certo. Evita salvar dados pela metade.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. Classe Base para os Models
# Todas as classes Python que representam tabelas devem herdar de 'Base'.
Base = declarative_base()

# 4. Injeção de Dependência (Generator)
# -------------------------------------
# Padrão recomendado pelo FastAPI/SQLAlchemy.
# Garante que a sessão é FECHADA (db.close()) mesmo se ocorrer um erro no meio do código.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()