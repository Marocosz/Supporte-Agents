"""
MÓDULO: app/core/schemas.py - DEFINIÇÕES DE ESQUEMAS (CONTRATOS DE DADOS)

FUNÇÃO:
Define todos os modelos de dados Pydantic (`BaseModel`) utilizados na aplicação.
Estes modelos atuam como contratos de dados para:
1. Comunicação WebSocket (entrada/saída de mensagens e ações do chat).
2. Comunicação HTTP (início de sessão).
3. Estrutura Hierárquica Final do Documento (`DocumentoFinalJSON`).
4. O Objeto de Estado Completo da Sessão (`DocumentoEmSessao`), que é a
   fonte única de verdade (Single Source of Truth) para o Orquestrador e o
   Gerenciador de Sessão.

ARQUITETURA:
O uso de Pydantic garante validação de tipo, clareza e imutabilidade (quando
apropriado) na manipulação de dados entre os diferentes agentes, serviços e a API.

FLUXO DE ESTADO PRINCIPAL:
O objeto `DocumentoEmSessao` é central, pois armazena o progresso de todos
os agentes em uma única estrutura, permitindo a transição suave pelos
diferentes estágios de criação do documento.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union


# --- Schemas para o Chat (Websocket) ---


class WsAction(BaseModel):
    """Define a estrutura de um botão de Ação interativo (Aceitar/Recusar/Pular)."""
    label: str  # O texto visível no botão (ex: "Aprovar e Continuar")
    value: str  # O comando enviado de volta ao backend (ex: "approve_toc")


class WsMessageOut(BaseModel):
    """Define a estrutura de CADA mensagem enviada do Backend para o Frontend (Cliente WebSocket)."""
    type: str  # O tipo de mensagem: "text", "suggestion", "final", "error", "processing"
    content: str
    actions: Optional[List[WsAction]] = None  # Botões de ação interativos
    # Usado para rastrear qual sugestão (ativo ou pergunta) está sendo votada ou respondida
    suggestion_id: Optional[str] = None
    # Usado apenas na mensagem final para fornecer o nome do arquivo gerado
    file_path: Optional[str] = None

# --- Schemas para o Início da Sessão (HTTP) ---


class SessionStartRequest(BaseModel):
    """Contrato de dados que o Frontend envia via HTTP para iniciar uma sessão de chat."""
    tipo_documento: str
    codificacao: str
    titulo_documento: str


class SessionStartResponse(BaseModel):
    """Contrato de dados que a API responde via HTTP após iniciar a sessão com sucesso."""
    session_id: str  # ID único para rastrear o chat (UUID)
    message: str

# --- Schemas do Documento (A Estrutura Hierárquica) ---


class SubSecao(BaseModel):
    """Define a estrutura de conteúdo de Nível 2 (ex: 5.1 Fluxograma)."""
    titulo: str
    conteudo: str


class Secao(BaseModel):
    """Define a estrutura de conteúdo de Nível 1 (ex: 2. Objetivo)."""
    titulo: str
    conteudo: str
    subsecoes: List[SubSecao] = []  # Lista de Níveis 2 aninhados


class DocumentoFinalJSON(BaseModel):
    """
    O JSON HIERÁRQUICO FINAL do documento.
    Esta é a saída processada do Agente 5 (Finalizador) e a
    entrada estruturada do DocxGenerator (Montador).
    """
    # Metadados do Cabeçalho
    logo_path: str = "supporte_logo.png"
    tipo_documento: str
    codificacao: str
    data_revisao: str
    numero_revisao: str
    titulo_documento: str

    # Corpo do Documento (Lista de Seções de Nível 1)
    corpo_documento: List[Secao]


class DocumentoEmSessao(BaseModel):
    """
    O "Estado" completo do documento. É o objeto persistido pelo SessionManager
    e manipulado pelo ChatOrchestrator ao longo de todo o fluxo.
    """
    session_id: str
    # O estado atual do fluxo (e.g., AGUARDANDO_RESUMO_AGENTE_1, AGUARDANDO_VALIDACAO_SUMARIO, etc.)
    status: str

    # --- DADOS BASE ---
    resumo_original: str = ""

    # --- FLUXO DE PLANEAMENTO E ESCRITA ---
    sumario_proposto: List[str] = []  # Sumário inicial gerado pelo Agente 1 (antes da validação)
    sumario_aprovado: List[str] = []  # O sumário que será usado para a escrita
    # Dicionário do rascunho (Chave: Título da Seção, Valor: Conteúdo de Texto)
    rascunho_completo: Dict[str, str] = {}

    # --- FLUXO DE QA E ATIVOS (AGENTE 4) ---
    # Lista de sugestões de ativos (diagramas, tabelas, etc.) a serem votadas pelo usuário
    ativos_pendentes: List[Dict[str, Any]] = []
    # Lista final de ativos que o usuário aprovou
    ativos_aceitos: List[Dict[str, Any]] = []
    # O ativo que está em exibição e aguardando Aceitar/Recusar
    ativo_em_votacao: Optional[Dict[str, Any]] = None

    # --- FLUXO DE ENRIQUECIMENTO (AGENTE 4/3) ---
    # Lista de perguntas de lacuna geradas pelo Agente 4 para enriquecer o texto
    perguntas_pendentes: List[Dict[str, Any]] = []
    # A pergunta atual aguardando a resposta de texto do usuário
    pergunta_em_andamento: Optional[Dict[str, Any]] = None
    # Lista de respostas coletadas que serão injetadas pelo Agente 3
    respostas_coletadas: List[Dict[str, Any]] = []
    
    # --- CAMPO DE CONTROLO DE FLUXO ---
    # Flag para indicar que a fase de QA (Agente 4) já foi executada (usado para bypass)
    qa_foi_concluido: bool = False 

    # --- DADOS FINAIS ---
    # O objeto DocumentoFinalJSON (saída do Agente 5). Inicializado com metadados.
    json_final: Optional[DocumentoFinalJSON] = None