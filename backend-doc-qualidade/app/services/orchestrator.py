"""
MÓDULO: app/services/orchestrator.py - FLUXO DE TRABALHO DE AGENTES DE IA (Qualidade-SUPP)

FUNÇÃO:
Define a classe principal `ChatOrchestrator`, responsável por gerenciar e
orquestrar o fluxo sequencial de 5 agentes de Inteligência Artificial para a
criação automatizada de documentos de Qualidade (Project Management Office).
Ele atua como o 'Chefe' da conversa, controlando o estado da sessão (status)
e a transição entre os agentes e as etapas de validação do usuário através
de WebSockets (FastAPI).

ARQUITETURA:
O fluxo é uma Máquina de Estados sequencial, onde a transição é acionada
por mensagens/ações do usuário no chat (via WebSocket).
A lógica suporta a alternância entre Agentes de Produção (com LLMs reais)
e Agentes de Mock (para testes).

1. **Agente 1 (Planner):**
   - **Ação:** Recebe o resumo inicial do usuário e gera o Sumário (TOC)
     baseado em documentos similares (RAG).
   - **Transição:** Vai para a validação do Sumário.

2. **Agente 2 (Writer):**
   - **Ação:** Recebe o Sumário Aprovado e o Resumo Original para gerar
     o **Rascunho V1** completo do documento.
   - **Transição:** Vai para a validação do Rascunho.

3. **Agente 3 (Reviser/Injector):**
   - **Ação:** **(a) Revisão Manual:** Aplica feedback de texto do usuário ao
     rascunho. **(b) Injeção de Detalhes:** Injeta as respostas coletadas
     durante a etapa de QA.
   - **Transição:** Volta para a validação do Rascunho ou avança para
     Revisão Final.

4. **Agente 4 (Critic/QA):**
   - **Ação:** Analisa o Rascunho V1 e gera sugestões de **Ativos Visuais**
     (Diagramas Mermaid, RACI) e **Perguntas de Lacuna** (detalhes faltantes).
   - **Transição:** Inicia os loops interativos de Votação de Ativos e Resposta
     a Perguntas.

5. **Agente 5 (Finalizer):**
   - **Ação:** Monta o JSON final hierárquico, combinando Metadados, Texto
     Enriquecido e Ativos Aceitos.
   - **Transição:** Vai para o gerador DOCX.

FLUXO DE DADOS E ESTADO:
- **`session_manager`:** Armazena o estado completo (`DocumentoEmSessao`)
  para cada ID de sessão. O status (`session.status`) é a variável de controle
  que define qual lógica de transição será executada pelo `handle_chat_message`.
- **Bypass de QA:** Se o usuário entrar no loop de revisão (`AGUARDANDO_FEEDBACK_REVISAO`)
  após a fase de QA, a aprovação do rascunho (`approve_draft`) é modificada
  para pular o Agente 4 e ir direto para o Agente 5 (Lógica `session.qa_foi_concluido`).
"""
import logging
from typing import List, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
from pathlib import Path
import json


from app.core.config import settings


# Bloco de importação condicional de agentes
# Isto permite alternar facilmente entre agentes de produção (com IA)
# e agentes de mock (para testes rápidos e estáveis)
if settings.USE_MOCK_AGENTS:
    from app.agents_mocks.agent_1_planner import agent_1_planner
    from app.agents_mocks.agent_2_writer import agent_2_writer
    from app.agents_mocks.agent_3_reviser import agent_3_reviser
    from app.agents_mocks.agent_4_critic import agent_4_critic
    from app.agents_mocks.agent_5_finalizer import agent_5_finalizer
else:
    # Importa os agentes de produção (com IA)
    from app.agents.agent_1_planner import agent_1_planner
    from app.agents.agent_2_writer import agent_2_writer
    from app.agents.agent_3_reviser import agent_3_reviser
    from app.agents.agent_4_critic import agent_4_critic
    from app.agents.agent_5_finalizer import agent_5_finalizer


# Importa os serviços essenciais
from app.services.docx_generator import docx_service
from app.services.session_manager import session_manager


# Importa os Schemas (modelos de dados Pydantic)
from app.core.schemas import DocumentoEmSessao, WsMessageOut, WsAction


logger = logging.getLogger(__name__)


class ChatOrchestrator:
    """
    O "Chefe" do fluxo de trabalho. Gerencia a Máquina de Estados de 5 agentes:
    Planeamento, Escrita, Revisão, QA/Ativos, e Finalização.

    A classe é responsável por:
    1. Gerenciar conexões WebSocket.
    2. Determinar o estado (`session.status`) atual da sessão.
    3. Chamar o agente apropriado com o payload correto.
    4. Enviar mensagens formatadas e botões de ação de volta ao cliente.
    5. Persistir o estado da sessão após cada transição.
    """

    # --- LÓGICA DE CONEXÃO (Não alterada) ---
    async def handle_new_connection(self, websocket: WebSocket, session_id: str):
        """
        Inicia uma nova conexão WebSocket. Verifica a sessão existente,
        fecha se for inválida e envia a primeira mensagem de boas-vindas
        para iniciar o fluxo.
        """
        session = session_manager.get_session(session_id)
        if not session:
            logger.error(
                f"Sessão {session_id} não encontrada. Fechando conexão.")
            await websocket.close(code=1008, reason="Sessão não encontrada")
            return

        logger.info(
            f"Orquestrador: Nova conexão para sessão {session_id}. Status inicial: {session.status}")

        titulo = session.json_final.titulo_documento
        cod = session.json_final.codificacao

        if session.status != "FINALIZADO":
            # Envia a mensagem de início e o prompt para o resumo do Agente 1
            msg_out = WsMessageOut(
                type="text",
                content=f"Olá! Vamos começar o seu documento: '{cod} - {titulo}'.\n\n"
                        f"Para começar, por favor, me dê um resumo do que este documento precisa conter. "
                        f"Qual é o seu objetivo principal?"
            )
            await websocket.send_json(msg_out.model_dump(exclude_none=True))
            # Define o status para aguardar a primeira entrada do usuário para o Agente 1
            session.status = "AGUARDANDO_RESUMO_AGENTE_1"
            session_manager.save_session(session)

    # --- FUNÇÃO PRINCIPAL DE MENSAGEM ---
    async def handle_chat_message(self, websocket: WebSocket, session_id: str, user_message: str):
        """
        Ponto de entrada para todas as mensagens do usuário (texto ou ações de botão).
        A lógica de roteamento depende do `current_status` da sessão.
        """
        session = session_manager.get_session(session_id)
        if not session:
            await self._send_error(websocket, "Sessão inválida. Por favor, reinicie.")
            return

        current_status = session.status
        logger.info(
            f"Orquestrador: Mensagem recebida. Status: {current_status}, Ação: {user_message[:30]}...")

        try:
            # Lógica da Máquina de Estados: Roteia a mensagem/ação
            if current_status == "AGUARDANDO_RESUMO_AGENTE_1":
                # Recebe o resumo inicial e chama o Agente 1
                await self._run_agent_1_planner(websocket, session, user_message)

            elif current_status == "AGUARDANDO_VALIDACAO_SUMARIO":
                # Lida com o clique de Aprovar/Rejeitar Sumário
                await self._handle_sumario_validation(websocket, session, user_message)

            elif current_status == "AGUARDANDO_VALIDACAO_RASCUNHO":
                # Lida com o clique de Aprovar/Rejeitar Rascunho (V1 ou Revisado)
                await self._handle_rascunho_validation(websocket, session, user_message)

            elif current_status == "AGUARDANDO_FEEDBACK_REVISAO":
                # Recebe feedback de texto para o Agente 3 (Reviser)
                await self._run_agent_3_reviser_loop(websocket, session, user_message)

            elif current_status == "AGUARDANDO_VOTACAO_ATIVOS":
                # Lida com o clique de Aceitar/Recusar Ativo (Agente 4)
                await self._handle_ativos_validation(websocket, session, user_message)

            elif current_status == "AGUARDANDO_RESPOSTA_PERGUNTA":
                # Lida com a resposta de texto à pergunta de enriquecimento (Agente 4)
                await self._handle_pergunta_answer(websocket, session, user_message)

            elif current_status == "AGUARDANDO_REVISAO_FINAL":
                # Lida com a decisão de Revisão Final (Sim/Não)
                await self._handle_revisao_final(websocket, session, user_message)

            else:
                logger.warning(
                    f"Status desconhecido ou fluxo inesperado: {current_status}")
                await self._send_error(websocket, "Fluxo inesperado. A sessão pode estar travada.")

        except Exception as e:
            logger.error(f"Erro no Orquestrador: {e}", exc_info=True)
            await self._send_error(websocket, f"Ocorreu um erro interno: {e}")

    # --- 1. ETAPA DE PLANEAMENTO (AGENTE 1) ---
    async def _run_agent_1_planner(self, websocket: WebSocket, session: DocumentoEmSessao, user_summary: str):
        """
        Chama o Agente 1 para gerar a Tabela de Conteúdo (Sumário) com base
        no resumo fornecido pelo usuário.
        """
        session.resumo_original = user_summary
        # Chama a função principal do Agente 1 (Planner)
        secoes = await agent_1_planner.generate_toc(user_summary)

        if not secoes or secoes[0].startswith("ERRO"):
            await self._send_error(websocket, f"Falha ao gerar sumário: {secoes[0]}")
            return

        session.sumario_proposto = secoes
        session.status = "AGUARDANDO_VALIDACAO_SUMARIO"  # Próximo estado
        session_manager.save_session(session)

        # Prepara e envia a mensagem de validação
        sumario_formatado = "\n".join([f"- {s}" for s in secoes])
        msg_content = (
            "Nosso planejador criou uma estrutura de documento baseada em documentos similares. "
            "Por favor, valide este Sumário (Tabela de Conteúdo):\n\n"
            f"**Estrutura Sugerida:**\n{sumario_formatado}\n\n"
            "Você aprova este sumário?"
        )
        msg_actions = [
            WsAction(label="Aprovar e Continuar", value="approve_toc"),
            WsAction(label="Modificar Sumário", value="reject_toc")
        ]
        await self._send_message(websocket, "validation", msg_content, actions=msg_actions)

    # --- 2. VALIDAÇÃO DO SUMÁRIO ---
    async def _handle_sumario_validation(self, websocket: WebSocket, session: DocumentoEmSessao, user_action: str):
        """
        Processa a ação de Aceitar ou Rejeitar o Sumário Proposto.
        - Aceitar: Avança para o Agente 2 (Writer).
        - Rejeitar: Volta ao Agente 1, pedindo novo input de texto.
        """
        if user_action == "approve_toc":
            session.sumario_aprovado = session.sumario_proposto
            session.status = "AGUARDANDO_VALIDACAO_RASCUNHO"
            session_manager.save_session(session)
            await self._run_agent_2_writer(websocket, session)
        elif user_action == "reject_toc":
            await self._send_message(websocket, "text", "Entendido. Por favor, envie a lista de seções desejadas (separadas por vírgula) ou descreva as alterações que gostaria de fazer.")
            # Volta ao estado inicial do Agente 1 para reprocessar o input do usuário
            session.status = "AGUARDANDO_RESUMO_AGENTE_1"
            session_manager.save_session(session)
        else:
            await self._send_error(websocket, "Ação desconhecida. Por favor, use os botões.")

    # --- 3. ETAPA DE ESCRITA (AGENTE 2) ---
    async def _run_agent_2_writer(self, websocket: WebSocket, session: DocumentoEmSessao):
        """
        Chama o Agente 2 para gerar o Rascunho V1 completo do conteúdo,
        usando o resumo original e o sumário aprovado.
        """
        await self._send_message(websocket, "processing", "Gerando o rascunho completo do conteúdo...")

        # Chama a função principal do Agente 2 (Writer)
        rascunho_dict = await agent_2_writer.generate_draft(
            session.resumo_original,
            session.sumario_aprovado
        )

        session.rascunho_completo = rascunho_dict
        session.status = "AGUARDANDO_VALIDACAO_RASCUNHO"  # Próximo estado
        session_manager.save_session(session)

        # Prepara e envia o rascunho para validação do usuário
        rascunho_formatado = "\n\n".join(
            [f"**{titulo}:**\n{conteudo}" for titulo, conteudo in rascunho_dict.items()])
        msg_content = (
            "Rascunho V1 gerado. Por favor, revise o conteúdo de todas as seções:\n\n"
            f"{rascunho_formatado}\n\n"
            "Você aprova este rascunho para análise de QA?"
        )
        msg_actions = [
            WsAction(label="Aprovar e Continuar para QA",
                     value="approve_draft"),
            WsAction(label="Revisar Rascunho (detalhar mudanças)",
                     value="reject_draft")
        ]
        await self._send_message(websocket, "validation", msg_content, actions=msg_actions)

    # --- 4. VALIDAÇÃO DO RASCUNHO V1 (COM BYPASS DE QA) ---
    async def _handle_rascunho_validation(self, websocket: WebSocket, session: DocumentoEmSessao, user_action: str):
        """
        Lida com a aprovação do rascunho.
        - Se for a primeira aprovação (qa_foi_concluido é False), avança para o Agente 4 (QA).
        - Se já houve QA (qa_foi_concluido é True), avança para o Agente 5 (Finalizer).
        - Rejeitar: Vai para o loop de revisão do Agente 3.
        """

        if user_action == "approve_draft":

            # --- INÍCIO DA MUDANÇA (LÓGICA DO BYPASS) ---
            if session.qa_foi_concluido:
                # O QA já foi feito. Estamos num loop de revisão final.
                # Aprovou a revisão? Então vá direto para o Finalizer.
                logger.info(
                    "Bypass de QA: Revisão final aprovada. Indo para o Agente 5 (Finalizer).")
                await self._run_agent_5_finalizer(websocket, session)
            else:
                # Esta é a primeira aprovação. Execute o QA.
                logger.info(
                    "Primeira aprovação do rascunho. Indo para o Agente 4 (QA).")
                await self._run_agent_4_qa(websocket, session)
            # --- FIM DA MUDANÇA ---

        elif user_action == "reject_draft":
            await self._send_message(websocket, "text", "Entendido. Por favor, descreva as mudanças (adição/remoção de seções, reescrita de parágrafos) que você gostaria de fazer.")
            session.status = "AGUARDANDO_FEEDBACK_REVISAO"  # Próximo estado para receber feedback
            session_manager.save_session(session)
        else:
            await self._send_error(websocket, "Ação desconhecida. Por favor, use os botões.")

    # --- 5. LOOP DE REVISÃO (AGENTE 3) ---
    async def _run_agent_3_reviser_loop(self, websocket: WebSocket, session: DocumentoEmSessao, user_feedback: str):
        """
        Chama o Agente 3 (Reviser) para aplicar o feedback manual do usuário
        no rascunho existente e retorna para a validação.
        """

        await self._send_message(websocket, "processing", "Aplicando suas revisões ao rascunho...")

        # Chama a função principal do Agente 3
        novo_rascunho = await agent_3_reviser.revise_draft(
            session.resumo_original,
            session.rascunho_completo,
            user_feedback
        )

        session.rascunho_completo = novo_rascunho
        session.status = "AGUARDANDO_VALIDACAO_RASCUNHO"  # Volta para a validação
        session_manager.save_session(session)

        # Re-exibe o rascunho atualizado para validação
        rascunho_formatado = "\n\n".join(
            [f"**{titulo}:**\n{conteudo}" for titulo, conteudo in novo_rascunho.items()])

        # --- MUDANÇA: O texto da pergunta muda se o QA já foi feito ---
        if session.qa_foi_concluido:
            # Se o QA já foi feito, a aprovação significa ir para o Finalizer
            question = "Você aprova esta revisão final?"
            approve_label = "Sim, Gerar Documento"
            approve_action = "approve_draft" # Mantém o mesmo valor para acionar a lógica de bypass
        else:
            # Se o QA NÃO foi feito, a aprovação significa ir para o Agente 4 (QA)
            question = "Você aprova este rascunho para análise de QA?"
            approve_label = "Aprovar e Continuar para QA"
            approve_action = "approve_draft"
        # --- FIM DA MUDANÇA ---

        msg_content = (
            "Rascunho revisado. Por favor, verifique se as alterações estão corretas:\n\n"
            f"{rascunho_formatado}\n\n"
            f"{question}"
        )
        msg_actions = [
            WsAction(label=approve_label, value=approve_action),
            WsAction(label="Revisar Novamente", value="reject_draft")
        ]
        await self._send_message(websocket, "validation", msg_content, actions=msg_actions)

    # --- 6. ETAPA DE QA E ENRIQUECIMENTO (AGENTE 4) ---
    async def _run_agent_4_qa(self, websocket: WebSocket, session: DocumentoEmSessao):
        """
        Chama o Agente 4 (Critic) para analisar o rascunho e gerar sugestões
        de ativos (diagramas/tabelas) e perguntas para preencher lacunas de detalhe.
        """

        await self._send_message(websocket, "processing", "Analisando o rascunho para identificar ativos visuais e lacunas de detalhe (QA)...")

        # Chama a função principal do Agente 4
        qa_analysis = await agent_4_critic.get_qa_analysis(session.rascunho_completo)

        # --- MUDANÇA: Carimba a sessão para marcar que o QA foi concluído ---
        # Essencial para o bypass no método _handle_rascunho_validation
        session.qa_foi_concluido = True
        # --- FIM DA MUDANÇA ---

        ativos = qa_analysis.get("ativos", [])
        perguntas = qa_analysis.get("perguntas", [])

        # Salva o resultado do QA na sessão
        session.ativos_pendentes = ativos
        session.perguntas_pendentes = perguntas
        session.respostas_coletadas = []  # Reseta para a nova fase
        session.status = "AGUARDANDO_VOTACAO_ATIVOS"
        session_manager.save_session(session)

        # Inicia o fluxo interativo: primeiro ativos, depois perguntas
        if ativos:
            await self._send_next_ativo(websocket, session)
        elif perguntas:
            await self._send_next_pergunta(websocket, session)
        else:
            # Se não houver ativos nem perguntas, pula para a revisão final
            await self._send_message(websocket, "text", "O Agente QA não encontrou ativos ou lacunas. Prosseguindo para a revisão final.")
            await self._ask_for_final_review(websocket, session)

    # --- 7A. LOOP DE VOTAÇÃO DE ATIVOS ---
    async def _send_next_ativo(self, websocket: WebSocket, session: DocumentoEmSessao):
        """Envia o próximo ativo sugerido para aprovação do usuário (Aceitar/Recusar)."""
        if session.ativos_pendentes:
            ativo_atual = session.ativos_pendentes.pop(0)  # Pega e remove o primeiro
            session.ativo_em_votacao = ativo_atual

            ativo_id = ativo_atual['id']
            ativo_content = ativo_atual['conteudo']

            msg_content = (
                f"**Ativo Sugerido (Tipo: {ativo_atual['tipo_ativo'].upper()}):**\n"
                f"Seção Alvo: **{ativo_atual['secao_alvo']}**\n\n"
                f"**Conteúdo:**\n`{ativo_content}`\n\n"
                "Deseja adicionar este ativo (Mermaid, RACI ou Placeholder) ao documento final?"
            )
            msg_actions = [
                WsAction(label="Aceitar Ativo",
                         value=f"accept_ativo:{ativo_id}"),
                WsAction(label="Recusar Ativo",
                         value=f"reject_ativo:{ativo_id}")
            ]

            await self._send_message(websocket, "suggestion", msg_content, actions=msg_actions, suggestion_id=ativo_id)
            session.status = "AGUARDANDO_VOTACAO_ATIVOS"
            session_manager.save_session(session)

        elif session.perguntas_pendentes:
            # Acabaram os ativos. Inicia o loop de perguntas.
            await self._send_message(websocket, "text", "Ótimo. Todos os ativos foram votados. Agora, vamos enriquecer o texto com detalhes.")
            await self._send_next_pergunta(websocket, session)

        else:
            # Acabaram os ativos E as perguntas. Vai para a revisão final.
            await self._send_message(websocket, "text", "Todos os ativos foram votados. Prosseguindo para a revisão final.")
            await self._ask_for_final_review(websocket, session)

    async def _handle_ativos_validation(self, websocket: WebSocket, session: DocumentoEmSessao, user_action: str):
        """Processa o clique de 'Aceitar/Recusar' para um ativo e envia o próximo."""
        ativo_votado = session.ativo_em_votacao
        if not ativo_votado:
            await self._send_error(websocket, "Erro: Nenhuma sugestão de ativo estava em votação.")
            return

        # Armazena apenas ativos aceitos para serem passados ao Finalizer (Agente 5)
        if user_action.startswith("accept_ativo:"):
            session.ativos_aceitos.append(ativo_votado)
            logger.info(f"Ativo {ativo_votado['id']} ACEITO")

        elif user_action.startswith("reject_ativo:"):
            logger.info(f"Ativo {ativo_votado['id']} RECUSADO")

        session.ativo_em_votacao = None  # Limpa o ativo em votação
        session_manager.save_session(session)
        await self._send_next_ativo(websocket, session)  # Próximo ativo ou avança o fluxo

    # --- 7B. LOOP DE PERGUNTAS DE ENRIQUECIMENTO ---
    async def _send_next_pergunta(self, websocket: WebSocket, session: DocumentoEmSessao):
        """Envia a próxima pergunta de enriquecimento de detalhe ao usuário."""
        if session.perguntas_pendentes:
            pergunta_atual = session.perguntas_pendentes.pop(0)  # Pega e remove a primeira
            session.pergunta_em_andamento = pergunta_atual

            msg_content = (
                f"**Detalhe Necessário para Enriquecimento:**\n"
                f"Seção: **{pergunta_atual['secao_alvo']}**\n\n"
                f"-> **{pergunta_atual['pergunta']}**\n\n"
                f"(Responda digitando no chat ou pule esta pergunta.)"
            )

            pergunta_id = pergunta_atual['id']
            msg_actions = [
                WsAction(label="Pular Pergunta",
                         value=f"skip_pergunta:{pergunta_id}")
            ]

            await self._send_message(
                websocket,
                "suggestion",  # Usa 'suggestion' para ter o botão de ação (Pular)
                msg_content,
                actions=msg_actions,
                suggestion_id=pergunta_id
            )

            session.status = "AGUARDANDO_RESPOSTA_PERGUNTA"  # Próximo estado
            session_manager.save_session(session)
        else:
            # Não há mais perguntas. Hora de injetar as respostas.
            await self._send_message(websocket, "text", "Obrigado por fornecer os detalhes. Agora, vou injetar essas informações no rascunho.")
            await self._run_agent_3_injector(websocket, session)

    async def _handle_pergunta_answer(self, websocket: WebSocket, session: DocumentoEmSessao, user_message: str):
        """Processa a resposta de texto do usuário OU o clique no botão "Pular"."""
        pergunta_feita = session.pergunta_em_andamento
        if not pergunta_feita:
            logger.warning(
                "Recebida resposta de texto, mas nenhuma pergunta estava em andamento.")
            return

        if user_message.startswith(f"skip_pergunta:{pergunta_feita['id']}"):
            # A ação de pular é tratada como uma mensagem de texto, mas com prefixo especial
            logger.info(f"Pergunta {pergunta_feita['id']} PULADA.")
        else:
            # Resposta de texto real
            logger.info(f"Pergunta {pergunta_feita['id']} RESPONDIDA.")
            session.respostas_coletadas.append({
                "pergunta": pergunta_feita['pergunta'],
                "resposta": user_message,
                "secao_alvo": pergunta_feita['secao_alvo']
            })

        session.pergunta_em_andamento = None  # Limpa a pergunta em andamento
        session_manager.save_session(session)
        await self._send_next_pergunta(websocket, session)  # Próxima pergunta ou avança o fluxo

    # --- 8. ETAPA DE INJEÇÃO DE DETALHES (REUTILIZA AGENTE 3) ---
    async def _run_agent_3_injector(self, websocket: WebSocket, session: DocumentoEmSessao):
        """
        Reutiliza o Agente 3 (Reviser) para injetar as respostas coletadas
        do usuário no rascunho. Isso é feito formatando as respostas como
        um grande feedback.
        """

        await self._send_message(websocket, "processing", "Injetando novos detalhes e enriquecendo o texto do rascunho (Etapa de Reescrita)...")

        # Se não houve respostas, pula a chamada do Agente 3
        if not session.respostas_coletadas:
            logger.info(
                "Nenhuma resposta coletada. Pulando injeção do Agente 3.")
            await self._ask_for_final_review(websocket, session)
            return

        # Converte a lista de respostas em um "super-feedback" formatado para o LLM
        feedback_list = []
        for r in session.respostas_coletadas:
            feedback_list.append(
                f"INJETAR na Seção '{r['secao_alvo']}' (Pergunta: {r['pergunta']}) -> RESPOSTA: {r['resposta']}")
        super_feedback = "APLICAR ENRIQUECIMENTO DE DETALHES. O novo texto deve ser conciso e usar os novos factos fornecidos:\n" + \
            "\n".join(feedback_list)

        # Chama o Agente 3 (Reviser) com o super-feedback
        rascunho_enriquecido = await agent_3_reviser.revise_draft(
            session.resumo_original,
            session.rascunho_completo,
            super_feedback
        )

        session.rascunho_completo = rascunho_enriquecido
        session_manager.save_session(session)

        # Vai para a revisão final
        await self._ask_for_final_review(websocket, session)

    # --- 9. ETAPA DE REVISÃO FINAL (NOVA) ---
    async def _ask_for_final_review(self, websocket: WebSocket, session: DocumentoEmSessao):
        """
        Pergunta ao usuário se ele quer fazer uma última revisão manual antes
        de gerar o documento final.
        """

        session.status = "AGUARDANDO_REVISAO_FINAL"
        session_manager.save_session(session)

        msg_content = (
            "O rascunho foi enriquecido com suas respostas.\n\n"
            "**Deseja fazer uma última revisão ou adicionar algo mais?**"
        )

        msg_actions = [
            WsAction(label="Não, Gerar Documento Final",
                     value="generate_final_doc"),
            WsAction(label="Sim, fazer uma última revisão",
                     value="final_review")
        ]
        await self._send_message(websocket, "validation", msg_content, actions=msg_actions)

    async def _handle_revisao_final(self, websocket: WebSocket, session: DocumentoEmSessao, user_action: str):
        """
        Lida com a decisão da revisão final.
        - Não, Gerar: Avança para o Agente 5 (Finalizer).
        - Sim, Revisar: Volta ao loop do Agente 3 para um último feedback.
        """

        if user_action == "generate_final_doc":
            logger.info(
                "Revisão Final: Usuário aprovou. Indo para o Agente 5 (Finalizer).")
            await self._run_agent_5_finalizer(websocket, session)

        elif user_action == "final_review":
            logger.info("Revisão Final: Usuário solicitou mais uma revisão.")
            await self._send_message(websocket, "text", "Entendido. Por favor, descreva as últimas alterações que gostaria de fazer.")
            session.status = "AGUARDANDO_FEEDBACK_REVISAO"  # Loop de volta para o Agente 3
            session_manager.save_session(session)

        else:
            await self._send_error(websocket, "Ação desconhecida. Por favor, use os botões.")

    # --- 10. ETAPA DE MONTAGEM FINAL (AGENTE 5) ---
    async def _run_agent_5_finalizer(self, websocket: WebSocket, session: DocumentoEmSessao):
        """
        Chama o Agente 5 (Finalizer) para estruturar o JSON hierárquico final
        (combinando rascunho enriquecido e ativos aceitos) e prepara para a
        geração do DOCX.
        """

        await self._send_message(websocket, "processing", "Montando o JSON hierárquico final (incorporando ativos e texto enriquecido)...")

        # Chama a função principal do Agente 5
        json_final = await agent_5_finalizer.generate_final_json(
            session.json_final,  # Metadados existentes (Título, Codificação, etc.)
            session.rascunho_completo,  # Rascunho enriquecido (V2)
            session.ativos_aceitos,  # Lista final de ativos aceitos
            # Respostas (passadas para o Finalizer para contexto no Prompt, se necessário)
            session.respostas_coletadas
        )

        session.json_final = json_final
        session.status = "FINALIZADO"
        session_manager.save_session(session)

        await self._run_docx_generator(websocket, session)  # Próxima etapa

    # --- 11. ETAPA DE GERAÇÃO DOCX (Não alterada) ---
    async def _run_docx_generator(self, websocket: WebSocket, session: DocumentoEmSessao):
        """
        Chama o serviço de geração DOCX, envia a mensagem final para o usuário
        com o link de download e fecha a sessão/conexão.
        """
        json_final = session.json_final

        try:
            # Gera o arquivo e recebe o caminho de volta
            file_path_str: str = docx_service.create_document(json_final)
            file_path_obj = Path(file_path_str)
            file_name = file_path_obj.name

            await self._send_message(
                websocket,
                "final",
                "Pronto! Seu documento foi gerado.",
                file_path=file_name  # Envia o nome do arquivo para o cliente
            )

            # Limpa a sessão e fecha a conexão
            session_manager.remove_session(session.session_id)
            await websocket.close(code=1000, reason="Geração concluída")

        except Exception as e:
            logger.error(f"Erro no Montador DOCX: {e}", exc_info=True)
            await self._send_error(websocket, f"Falha ao gerar o arquivo .docx: {e}")

    # --- Funções de Comunicação (WS) ---
    async def _send_message(self, websocket: WebSocket, msg_type: str, content: str,
                           actions: List[WsAction] = None,
                           suggestion_id: str = None,
                           file_path: str = None):
        """
        Função utilitária para enviar uma mensagem WsMessageOut formatada
        (texto, validação, processamento, final, erro) para o cliente.
        """
        msg_out = WsMessageOut(
            type=msg_type,
            content=content,
            actions=actions or [],
            suggestion_id=suggestion_id,
            file_path=file_path
        )
        await websocket.send_json(msg_out.model_dump(exclude_none=True))

    async def _send_error(self, websocket: WebSocket, error_message: str):
        """Envia uma mensagem de erro padronizada para o cliente."""
        msg_out = WsMessageOut(type="error", content=error_message, actions=[])
        await websocket.send_json(msg_out.model_dump(exclude_none=True))


# Cria uma instância única do orquestrador (Singleton)
# Esta instância é usada para gerenciar todas as conexões de chat.
chat_orchestrator = ChatOrchestrator()