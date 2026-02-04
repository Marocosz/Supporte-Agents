from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# --- Schemas Internos (Partes do JSON) ---

class TimelineItem(BaseModel):
    mes: str
    qtd: int

class SazonalidadeItem(BaseModel):
    dia: str
    qtd: int

class ClusterMetrics(BaseModel):
    volume: int
    top_servicos: Dict[str, int]
    top_solicitantes: Dict[str, int]
    top_subareas: Dict[str, int] = {}
    top_status: Dict[str, int] = {}
    timeline: List[TimelineItem] = []
    sazonalidade: List[SazonalidadeItem] = []

class ClusterResult(BaseModel):
    cluster_id: int
    titulo: str
    descricao: str
    metricas: ClusterMetrics
    # ids_chamados é opcional na visualização geral, mas existe no JSON
    ids_chamados: Optional[List[str]] = []
    
    # --- NOVO: Suporte a Hierarquia (Árvore) ---
    # Permite que um cluster tenha "filhos". 
    # Usamos ForwardRef ('ClusterResult') pois a classe referencia a si mesma.
    sub_clusters: Optional[List['ClusterResult']] = [] 

class AnalysisMetadata(BaseModel):
    sistema: str
    data_analise: str
    periodo_dias: int
    total_chamados: int
    total_grupos: int
    taxa_ruido: float # Adicionado conforme seu output anterior

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

class BatchTicketRequest(BaseModel):
    """
    Payload para solicitar detalhes de múltiplos chamados.
    Frontend envia { "ids": ["1", "2"] }
    """
    ids: List[str]