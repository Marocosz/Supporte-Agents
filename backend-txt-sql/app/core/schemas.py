# app/core/schemas.py
from typing import List, Optional, Any, Literal, Union, Dict
from pydantic import BaseModel, Field

# ==========================================
# 1. MODELOS INTERNOS (Saída dos Agentes)
# ==========================================

class AgentSQLOutput(BaseModel):
    """Contrato para Tracking, Analytics e Fixer"""
    thought_process: str = Field(description="Raciocínio da IA")
    sql: str = Field(description="Query SQL gerada")
    chart_suggestion: Optional[Literal['bar', 'line', 'pie', 'number', 'table']] = None

class LibrarianOutput(BaseModel):
    """Contrato para o Librarian"""
    thought_process: str = Field(description="Análise da regra")
    used_rules: List[str] = Field(description="Regras consultadas")
    answer: str = Field(description="Resposta final ao usuário")

class RouterOutput(BaseModel):
    """Contrato para o Router"""
    category: Literal["TRACKING", "ANALYTICS", "KNOWLEDGE", "CHAT"]
    reasoning: str = Field(description="Por que escolheu essa categoria")

# ==========================================
# 2. MODELOS EXTERNOS (API Request/Response)
# ==========================================

class ChatRequest(BaseModel):
    """Entrada da API"""
    question: str
    session_id: Optional[str] = None
    # Mantemos history opcional para compatibilidade com Frontend antigo, 
    # embora o backend novo use memória interna.
    history: Optional[List[Dict[str, str]]] = [] 

class BaseResponse(BaseModel):
    """Campos comuns a todas as respostas"""
    type: Literal["text", "data_result", "chart_data", "error"]
    content: str
    session_id: str
    query: str
    response_time: str
    server_execution_time: float

class TextResponse(BaseResponse):
    """Resposta simples (Librarian/Chat)"""
    type: Literal["text"]

class DataResponse(BaseResponse):
    """Resposta com dados (Tracking/Analytics)"""
    type: Literal["data_result", "chart_data"]
    sql: Optional[str] = None
    data: Optional[Any] = None
    chart_suggestion: Optional[str] = None

class ErrorResponse(BaseResponse):
    """Resposta de erro"""
    type: Literal["error"]
    debug_info: Optional[str] = None

# Union Type para o FastAPI documentar corretamente no Swagger
ChatResponse = Union[TextResponse, DataResponse, ErrorResponse]