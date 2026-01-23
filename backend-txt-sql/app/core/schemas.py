from typing import List, Optional, Any, Literal, Union
from pydantic import BaseModel, Field

# ==========================================
# 1. MODELOS INTERNOS (O que a IA gera)
# ==========================================

class AgentSQLOutput(BaseModel):
    """Contrato de saída para agentes geradores de SQL (Tracking/Analytics/Fixer)"""
    thought_process: str = Field(description="Raciocínio breve da IA antes de gerar o SQL")
    sql: str = Field(description="A query SQL gerada")
    chart_suggestion: Optional[Literal['bar', 'line', 'pie', 'number', 'table']] = Field(default=None, description="Sugestão visual (apenas Analytics)")

class LibrarianOutput(BaseModel):
    """Contrato de saída para o Librarian"""
    answer: str = Field(description="A resposta textual baseada nas regras")

# ==========================================
# 2. MODELOS EXTERNOS (O que o Front recebe)
# ==========================================

class ChatRequest(BaseModel):
    """Entrada da API"""
    question: str
    session_id: Optional[str] = None

class BaseResponse(BaseModel):
    """Campos comuns a todas as respostas"""
    type: Literal["text", "data_result", "chart_data", "error"]
    content: str
    session_id: str
    query: str
    response_time: str
    server_execution_time: float

class TextResponse(BaseResponse):
    """Resposta simples de texto (Librarian/Chat)"""
    type: Literal["text"]

class DataResponse(BaseResponse):
    """Resposta com dados do banco (Tracking/Analytics)"""
    type: Literal["data_result", "chart_data"]
    sql: Optional[str] = None
    data: Optional[Any] = None # Lista de tuplas ou dicts
    chart_suggestion: Optional[str] = None

class ErrorResponse(BaseResponse):
    """Resposta de erro controlado"""
    type: Literal["error"]
    debug_info: Optional[str] = None

# Union Type para facilitar o FastAPI
ChatResponse = Union[TextResponse, DataResponse, ErrorResponse]

class RouterOutput(BaseModel):
    """Schema para o Classificador de Intenção"""
    category: Literal["TRACKING", "ANALYTICS", "KNOWLEDGE", "CHAT"]
    reasoning: Optional[str] = None # Opcional: explicar pq escolheu essa categoria

class LibrarianOutput(BaseModel):
    """Contrato de saída para o Guardião de Conhecimento"""
    thought_process: str = Field(description="Raciocínio sobre qual regra aplicar")
    answer: str = Field(description="A resposta final para o usuário")
    used_rules: List[str] = Field(description="Quais regras foram consultadas (ex: ['Regra 1', 'Regra 5'])")
    