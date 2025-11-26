import requests
import websockets
import asyncio
import json
import logging
import os # Necessário para o pip install

# Configura o logging para ver os detalhes
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CHAT_CLIENT")

# --- Configurações ---
API_URL_HTTP = "http://127.0.0.1:8000"
API_URL_WS = "ws://127.0.0.1:8000"

# --- Dados Iniciais para o Teste (Novo Cenário) ---
TEST_SESSION_DATA = {
  "tipo_documento": "Formulário",
  "codificacao": "FO-FIN-001",
  "titulo_documento": "Requisição de Reembolso de Despesas de Viagem"
}

# --- NOVO RESUMO (MAIS RICO) ---
USER_SUMMARY = """
Preciso de um novo formulário para o financeiro.
O objetivo é que os colaboradores possam pedir reembolso de despesas de viagem.
Eles precisam anexar as notas fiscais obrigatoriamente.
O documento deve detalhar o que pode ser reembolsado (hospedagem, alimentação, transporte/km)
e o que não pode (bebidas alcoólicas, multas, entretenimento).
Ele se aplica a todos os colaboradores em regime CLT que façam viagens nacionais pela empresa.
"""
# --- FIM DO NOVO RESUMO ---

async def run_chat_test():
    """
    Simula o fluxo completo do chat de ponta a ponta.
    """
    logger.info("--- 1. INICIANDO SESSÃO (HTTP POST) ---")
    
    # --- PASSO 1: Iniciar a Sessão (HTTP) ---
    try:
        response = requests.post(
            f"{API_URL_HTTP}/v1/session/start",
            json=TEST_SESSION_DATA
        )
        response.raise_for_status() # Lança erro se a resposta for 4xx ou 5xx
        
        session_data = response.json()
        session_id = session_data.get("session_id")
        
        if not session_id:
            logger.error("Erro: Não foi possível obter um session_id.")
            return
            
        logger.info(f"Sessão iniciada com sucesso. ID: {session_id}\n")

    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao iniciar sessão HTTP: {e}")
        return

    # --- PASSO 2: Conectar ao Chat (WebSocket) ---
    uri = f"{API_URL_WS}/v1/session/chat/{session_id}"
    logger.info(f"--- 2. CONECTANDO AO WEBSOCKET ---\n{uri}\n")
    
    try:
        async with websockets.connect(uri) as websocket:
            
            # --- PASSO 3: AGENTE 1 (Escritor) ---
            logger.info("--- 3. FLUXO AGENTE 1 (ESCRITOR) ---")
            
            # 1. Recebe a 1ª mensagem ("Olá! Me dê um resumo...")
            msg_agent_1_hello = await websocket.recv()
            logger.info(f"[AGENTE 1]: {json.loads(msg_agent_1_hello)['content']}")
            
            # 2. Envia o resumo do usuário
            logger.info(f"[USUÁRIO (Enviando)]: {USER_SUMMARY}")
            await websocket.send(USER_SUMMARY)
            
            # 3. Recebe a 2ª mensagem ("Entendido. Processando...")
            msg_agent_1_processing = await websocket.recv()
            logger.info(f"[ORQUESTRADOR]: {json.loads(msg_agent_1_processing)['content']}")

            # 4. Recebe a 3ª mensagem (Validação do Rascunho)
            msg_agent_1_validation = await websocket.recv()
            validation_data = json.loads(msg_agent_1_validation)
            logger.info(f"[AGENTE 1 (Validação)]: {validation_data['content']}")
            logger.info(f"[Ações]: {validation_data['actions']}")
            
            # 5. Envia a aprovação
            logger.info("[USUÁRIO (Clicando)]: Aprovar e Continuar")
            await websocket.send("approve") # O valor do botão
            
            # 6. Recebe a confirmação ("Ótimo. Rascunho aprovado.")
            msg_agent_1_approved = await websocket.recv()
            logger.info(f"[ORQUESTRADOR]: {json.loads(msg_agent_1_approved)['content']}")

            # --- PASSO 4: AGENTE 2 (Crítico) ---
            logger.info("\n--- 4. FLUXO AGENTE 2 (CRÍTICO) ---")
            
            # 1. Recebe a msg de "Analisando..."
            msg_agent_2_start = await websocket.recv()
            logger.info(f"[ORQUESTRADOR]: {json.loads(msg_agent_2_start)['content']}")
            
            # Loop para aceitar/recusar sugestões
            while True:
                response_str = await websocket.recv()
                response = json.loads(response_str)
                
                if response['type'] == 'suggestion':
                    logger.info(f"[AGENTE 2 (Sugestão)]: {response['content']}")
                    suggestion_id = response['suggestion_id']
                    
                    # --- Lógica de Decisão: Aceita TUDO ---
                    action = f"accept:{suggestion_id}"
                    logger.info(f"[USUÁRIO (Clicando)]: Aceitar ({action})")
                    await websocket.send(action)

                elif "Todas as sugestões foram processadas" in response['content'] or "não encontrou sugestões" in response['content']:
                    logger.info(f"[ORQUESTRADOR]: {response['content']}")
                    break # Sai do loop de sugestões
                
                elif response['type'] == 'error':
                    logger.error(f"[ERRO DO SERVIDOR]: {response['content']}")
                    break
                
                else:
                    logger.warning(f"[??]: Resposta inesperada: {response['content']}")
            
            # --- PASSO 5: AGENTE 3 (Finalizador) ---
            logger.info("\n--- 5. FLUXO AGENTE 3 (FINALIZADOR) ---")

            # 1. Recebe a msg de "Compilando..."
            msg_agent_3_start = await websocket.recv()
            logger.info(f"[ORQUESTRADOR]: {json.loads(msg_agent_3_start)['content']}")

            # 2. Recebe a msg de "Revisão final concluída..."
            msg_agent_4_start = await websocket.recv()
            logger.info(f"[ORQUESTRADOR]: {json.loads(msg_agent_4_start)['content']}")

            # --- PASSO 6: MONTADOR (Resultado Final) ---
            logger.info("\n--- 6. FLUXO FINAL (MONTADOR) ---")
            
            # 1. Recebe a msg final com o caminho do arquivo
            msg_final = await websocket.recv()
            final_data = json.loads(msg_final)
            
            if final_data['type'] == 'final':
                logger.info(f"[ORQUESTRADOR]: {final_data['content']}")
                logger.info(f"🎉 SUCESSO! 🎉 Arquivo salvo em: {final_data['file_path']}")
            else:
                logger.error(f"[ERRO?]: Resposta inesperada: {final_data}")

            # O servidor deve fechar a conexão agora
            try:
                await websocket.recv()
            except websockets.exceptions.ConnectionClosed:
                logger.info("\nSessão encerrada pelo servidor. Teste concluído.")

    except websockets.exceptions.ConnectionClosed as e:
        logger.warning(f"Conexão fechada: {e}")
    except Exception as e:
        logger.error(f"Um erro ocorreu durante o chat: {e}", exc_info=True)

if __name__ == "__main__":
    # Garante que as bibliotecas de cliente estão instaladas
    try:
        import requests
    except ImportError:
        print("Instalando 'requests'...")
        os.system("pip install requests")
        
    try:
        import websockets
    except ImportError:
        print("Instalando 'websockets'...")
        os.system("pip install websockets")

    asyncio.run(run_chat_test())