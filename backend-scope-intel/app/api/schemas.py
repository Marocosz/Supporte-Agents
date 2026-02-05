# ==============================================================================
# ARQUIVO: app/api/schemas.py
#
# OBJETIVO:
#   Definir os modelos de dados (Pydantic) para validação e tipagem da API.
#   Garante que as respostas JSON sigam um contrato estrito.
#
# PARTE DO SISTEMA:
#   Backend / Definição de Tipos
#
# RESPONSABILIDADES:
#   - Mapear a estrutura do JSON de Análise (ClusterResult, Metrics)
#   - Mapear Payloads de Requisição (BatchTicketRequest)
#   - Mapear Respostas de Listagem (AnalysisFileSummary)
#
# COMUNICAÇÃO:
#   Usado por: routes.py, frontend (como referência de contrato)
# ==============================================================================

from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# --- Schemas Internos (Partes do JSON) ---

class TimelineItem(BaseModel):
    mes: str
    qtd: int

class SazonalidadeItem(BaseModel):
    dia: str
    qtd: int

class TendenciaAnalise(BaseModel):
    tipo: str
    variacao_pct: float
    alerta: bool
    detalhe: Optional[str] = ""

class ConcentracaoAnalise(BaseModel):
    tipo: str
    ratio: float
    usuarios_unicos: Optional[int] = 0

class ClusterMetrics(BaseModel):
    volume: int
    top_servicos: Dict[str, int]
    top_solicitantes: Dict[str, int]
    top_subareas: Dict[str, int] = {}
    top_status: Dict[str, int] = {}
    timeline: List[TimelineItem] = []
    sazonalidade: List[SazonalidadeItem] = []
    tendencia: Optional[TendenciaAnalise] = None
    concentracao: Optional[ConcentracaoAnalise] = None

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
    analise_racional: Optional[str] = ""

# Necessário para resolver a referência circular (ClusterResult dentro de ClusterResult)
ClusterResult.model_rebuild() 

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