from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# --- Schemas Internos (Partes do JSON) ---

class ClusterMetrics(BaseModel):
    volume: int
    top_servicos: Dict[str, int]
    top_solicitantes: Dict[str, int]

class ClusterResult(BaseModel):
    cluster_id: int
    titulo: str
    descricao: str
    metricas: ClusterMetrics
    # ids_chamados é opcional na visualização geral, mas existe no JSON
    ids_chamados: Optional[List[str]] = [] 

class AnalysisMetadata(BaseModel):
    sistema: str
    data_analise: str
    periodo_dias: int
    total_chamados: int
    total_grupos: int

# --- Schemas de Resposta da API ---

class AnalysisResponse(BaseModel):
    """Modelo do JSON completo de uma análise"""
    metadata: AnalysisMetadata
    clusters: List[ClusterResult]

class AnalysisFileSummary(BaseModel):
    """Modelo para a lista de arquivos disponíveis"""
    filename: str
    sistema: str
    data_criacao: str
    tamanho_bytes: int