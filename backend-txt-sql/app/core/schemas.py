# =================================================================================================
# SCHEMAS DE SAÍDA (CONTRATO DE DADOS BACKEND -> FRONTEND)
# =================================================================================================
from typing import List, Literal, Union, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict

class BaseResponse(BaseModel):
    """Campos comuns injetados pela API (api.py) após o processamento do Agente."""
    # Configuração de segurança: Ignora campos extras que o LLM possa inventar
    model_config = ConfigDict(extra='ignore')

    session_id: Optional[str] = Field(
        default=None, 
        description="ID único da sessão para rastreamento."
    )
    response_time: Optional[str] = Field(
        default=None, 
        description="Tempo total de processamento em segundos."
    )
    # O Orchestrator injeta como 'sql', mas mantemos 'generated_sql' aqui por compatibilidade
    generated_sql: Optional[str] = Field(
        default=None, 
        description="O SQL gerado pelo agente."
    )

# --- Modelo 1: Resposta de Texto (Cards, Listas, KPIs) ---
class TextResponse(BaseResponse):
    type: Literal["text"] = Field(
        description="Identificador fixo para renderização de texto."
    )
    content: str = Field(
        description="O conteúdo da resposta em PT-BR, formatado."
    )

# --- Modelo 2: Resposta de Gráfico (Analytics) ---
class ChartResponse(BaseResponse):
    type: Literal["chart"] = Field(
        description="Identificador fixo para renderização de gráficos."
    )
    
    chart_type: Literal["bar", "line", "pie"] = Field(
        description="O tipo de visualização."
    )
    
    title: str = Field(
        description="Título curto e descritivo do gráfico em PT-BR."
    )
    
    data: List[Dict[str, Any]] = Field(
        description="Lista de dados brutos."
    )
    
    x_axis: str = Field(
        description="Chave do JSON que representa a Categoria/Tempo (Eixo X)."
    )
    
    y_axis: List[str] = Field(
        description="Lista de chaves do JSON que representam os Valores (Eixo Y)."
    )
    
    y_axis_label: Optional[str] = Field(
        default=None, 
        description="Rótulo da unidade de medida."
    )

# --- Union Type para uso nos Parsers ---
AgentResponse = Union[ChartResponse, TextResponse]