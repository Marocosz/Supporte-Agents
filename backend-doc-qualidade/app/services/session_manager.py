"""
MÓDULO: app/services/session_manager.py - GERENCIAMENTO DO ESTADO DA SESSÃO

FUNÇÃO:
Define a classe `SessionManager`, um *Singleton* que serve como um repositório
em memória para armazenar o estado completo de cada conversa de criação de
documentos. Este gerenciador é essencial para que o `ChatOrchestrator` possa
persistir e recuperar o progresso do fluxo de trabalho de 5 agentes.

ARQUITETURA:
A classe atua como um cache de dados temporário, utilizando um dicionário
Python (`self.active_sessions: Dict[str, DocumentoEmSessao]`) para mapear
cada ID de sessão (UUID) ao seu objeto de estado correspondente
(`DocumentoEmSessao`).

RESPONSABILIDADES CHAVE:
1. **Criação de Sessão:** Gera um novo UUID e inicializa o objeto de estado
   (`DocumentoEmSessao`) com metadados e todas as listas/variáveis de controle
   vazias, definindo o status inicial.
2. **Persistência (Save/Get):** Permite que o Orquestrador recupere e atualize
   o objeto de estado da sessão após cada passo do fluxo de trabalho (e.g.,
   após um agente gerar um rascunho ou o usuário aprovar um sumário).
3. **Remoção:** Limpa a sessão do cache quando o documento é finalizado ou
   em caso de inatividade/timeout.

FLUXO DE DADOS:
- O objeto `DocumentoEmSessao` é o coração do estado, contendo:
    - O JSON de metadados (`DocumentoFinalJSON`).
    - O rascunho atual do conteúdo (`rascunho_completo`).
    - Listas de sugestões de QA (`ativos_pendentes`, `perguntas_pendentes`).
    - O estado atual da Máquina de Estados (`status`).
"""
import uuid
import logging
from datetime import datetime
# Importa Tuple para anotação de tipo do retorno
from typing import Dict, Optional, List, Any, Tuple

# Importa os "contratos" que definimos em schemas.py (Pydantic Models)
from app.core.schemas import (
    DocumentoEmSessao,
    SessionStartRequest,
    DocumentoFinalJSON,
    Secao,
    # Outras importações de schemas podem ser adicionadas aqui se necessário
)

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Gerencia o "estado" de todas as conversas ativas (cache em memória).
    Mantém o mapeamento entre o session_id (UUID) e o objeto de estado
    DocumentoEmSessao.
    """

    def __init__(self):
        # Dicionário que armazena todas as sessões ativas: {session_id: DocumentoEmSessao}
        self.active_sessions: Dict[str, DocumentoEmSessao] = {}

    def create_session(self, start_data: SessionStartRequest) -> Tuple[str, str]:
        """
        Cria uma nova sessão de chat, gerando um ID único (UUID) e inicializando
        o objeto de estado.

        Args:
            start_data: Dados iniciais (metadados) para o documento.

        Returns:
            Uma tupla contendo o session_id gerado e uma mensagem de sucesso.
        """
        session_id = str(uuid.uuid4())
        logger.info(f"Criando nova sessão: {session_id}")

        # 1. Cria o objeto JSON final (metadados iniciais)
        dados_iniciais = DocumentoFinalJSON(
            tipo_documento=start_data.tipo_documento,
            codificacao=start_data.codificacao,
            titulo_documento=start_data.titulo_documento,
            data_revisao=datetime.now().strftime("%d/%m/%Y"),
            numero_revisao="00",
            corpo_documento=[]  # Inicializa o corpo como vazio
        )

        # 2. Cria o objeto de "Estado" da Sessão (DocumentoEmSessao)
        # Este objeto carrega todo o progresso do chat.
        nova_sessao = DocumentoEmSessao(
            session_id=session_id,
            # Status inicial, aguardando o primeiro input do usuário
            status="AGUARDANDO_RESUMO_AGENTE_1",
            json_final=dados_iniciais,

            # Inicializa todas as variáveis de controle do Orquestrador
            rascunho_completo={},  # O rascunho gerado pelo Agente 2
            sumario_proposto=[],  # Sumário sugerido pelo Agente 1
            sumario_aprovado=[],  # Sumário após validação do usuário
            ativos_pendentes=[],  # Sugestões de ativos do Agente 4 (a votar)
            ativos_aceitos=[],  # Ativos aprovados para injeção no final
            ativo_em_votacao=None,  # O ativo que está sendo votado no momento
            perguntas_pendentes=[],  # Perguntas de detalhe do Agente 4
            pergunta_em_andamento=None,  # A pergunta que aguarda resposta
            respostas_coletadas=[],  # Respostas dadas pelo usuário
            resumo_original="",  # O resumo inicial fornecido pelo usuário (será preenchido pelo Orquestrador)
            
            qa_foi_concluido=False  # Flag de controle para o loop de revisão (bypass de QA)
        )

        # 3. Armazena no cache (o dicionário em memória)
        self.active_sessions[session_id] = nova_sessao
        logger.info(f"Sessão {session_id} criada e armazenada.")

        # Retorna a tupla (ID, Mensagem de Boas-vindas) para o endpoint da API
        return session_id, f"Sessão {session_id} criada com sucesso."

    def get_session(self, session_id: str) -> DocumentoEmSessao | None:
        """
        Busca uma sessão ativa pelo ID. Usado pelo Orquestrador antes
        de processar qualquer mensagem.

        Returns:
            O objeto DocumentoEmSessao ou None se não for encontrado.
        """
        return self.active_sessions.get(session_id)

    def save_session(self, session: DocumentoEmSessao):
        """
        Salva/Atualiza o objeto de sessão (estado) de volta no cache.
        Esta é a operação mais comum após cada transição de estado ou agente.
        """
        session_id = session.session_id
        if session_id in self.active_sessions:
            self.active_sessions[session_id] = session
            logger.debug(f"Sessão {session_id} salva.")
        else:
            logger.warning(
                f"Tentativa de salvar dados de sessão inexistente: {session_id}")

    def remove_session(self, session_id: str):
        """
        Remove uma sessão do cache. Deve ser chamada após a conclusão do
        documento (status FINALIZADO) ou por uma rotina de limpeza de
        sessões expiradas.
        """
        if session_id in self.active_sessions:
            logger.info(f"Removendo sessão: {session_id}")
            del self.active_sessions[session_id]


# Cria uma instância única (Singleton) do gerenciador
# Esta instância global será importada e usada por outros serviços, como o Orquestrador.
session_manager = SessionManager()