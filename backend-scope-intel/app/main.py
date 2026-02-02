from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import routes

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="API de Leitura de Análises de Chamados (Batch Output)"
)

# Configuração de CORS (Permite que o Frontend acesse o Backend)
origins = [
    "http://localhost:3000",  # Frontend React padrão
    "http://localhost:5173",  # Frontend Vite/Vue padrão
    "*"                       # ⚠️ Em produção, restrinja isso!
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir as rotas
app.include_router(routes.router, prefix="/api")

@app.get("/")
def health_check():
    return {"status": "online", "mode": "batch_read_only"}