from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# 1. Criação do Engine (O Motor de Conexão)
# pool_pre_ping=True: Testa a conexão antes de usar. Evita erro de "MySQL has gone away".
# pool_size=10: Mantém 10 conexões abertas prontas para uso (performance).
# max_overflow=20: Se precisar muito, abre mais 20 temporárias.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# 2. Fábrica de Sessões
# autocommit=False: Segurança transacional. Só salva se dermos commit explícito.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. Classe Base para os Models
# Todas as suas tabelas (classes Python) vão herdar desta classe.
Base = declarative_base()

# 4. Dependência para FastAPI (Injeção de Dependência)
# Garante que a conexão abre e FECHA corretamente a cada requisição.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()