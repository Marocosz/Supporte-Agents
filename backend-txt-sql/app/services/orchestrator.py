# app/services/orchestrator.py
import logging
import time
from typing import Dict, Any

from app.services.context import ContextManager
from app.services.sql_guard import SQLGuard, SecurityError
from app.core.database import get_db_connection

# Agentes
from app.agents.router import classify_intent
from app.agents.tracking import generate_tracking_sql
from app.agents.analytics import generate_analytics_sql # <--- NOVO
from app.agents.fixer import fix_sql_query
from app.agents.librarian import consult_librarian # <--- NOVO

logger = logging.getLogger(__name__)

class Orchestrator:
    """
    O Cérebro da Aplicação (Enterprise Final).
    Gerencia: Routing -> SQL Generation/RAG -> Guard -> Execution -> Self-Healing -> Formatting.
    """

    SHORT_CIRCUIT_KEYWORDS = ["oi", "olá", "ola", "bom dia", "boa tarde", "start", "inicio"]
    WELCOME_MESSAGE = "Olá! Sou seu assistente de BI Logístico. Posso rastrear notas, analisar métricas ou tirar dúvidas."

    @staticmethod
    def run_pipeline(session_id: str, question: str) -> Dict[str, Any]:
        start_time = time.time()
        logger.info(f"\n🎬 [ORCHESTRATOR] Sessão: {session_id[:8]} | Input: '{question}'")

        # 1. SHORT-CIRCUIT
        if question.strip().lower() in Orchestrator.SHORT_CIRCUIT_KEYWORDS:
            return {"type": "text", "content": Orchestrator.WELCOME_MESSAGE, "execution_time": 0.0}

        # 2. CONTEXT & ROUTING
        final_question = question # (Placeholder para resolução de pronomes futura)
        category = classify_intent(final_question)
        ContextManager.update_context(session_id, "last_intent", category)

        result = {}

        # 3. DISPATCH FLOW
        if category == "TRACKING":
            result = Orchestrator._handle_sql_flow(final_question, "TRACKING")
            
        elif category == "ANALYTICS":
            result = Orchestrator._handle_sql_flow(final_question, "ANALYTICS")
            
        elif category == "KNOWLEDGE":
            # Fluxo sem SQL (Texto puro)
            answer = consult_librarian(final_question)
            result = {"type": "text", "content": answer}
            
        else: # CHAT
            result = {"type": "text", "content": "Sou um assistente focado em logística. Tente perguntar sobre notas, pedidos ou métricas."}

        # 4. FINALIZAÇÃO
        result["execution_time"] = round(time.time() - start_time, 4)
        result["category"] = category
        return result

    @staticmethod
    def _handle_sql_flow(question: str, mode: str) -> Dict[str, Any]:
        """Gerencia ciclo de vida SQL (Tracking e Analytics)."""
        db = get_db_connection()
        generated_data = {}

        # 1. Geração (Generation)
        try:
            if mode == "TRACKING":
                generated_data = generate_tracking_sql(question)
            else:
                generated_data = generate_analytics_sql(question)
                
            candidate_sql = generated_data.get("sql", "")
            
            if not candidate_sql:
                return {"type": "text", "content": "Não consegui gerar uma consulta para sua pergunta."}
                
        except Exception as e:
            logger.error(f"Erro na geração de SQL ({mode}): {e}")
            return {"type": "text", "content": "Erro interno ao processar sua pergunta."}

        # --- EXECUTION LOOP & SELF-HEALING ---
        current_sql = candidate_sql
        max_retries = 1 
        
        for attempt in range(max_retries + 1):
            try:
                # 2. Segurança
                logger.info(f"🛡️ [GUARD] Validando SQL...")
                secure_sql = SQLGuard.validate_query(current_sql)
                
                # 3. Execução
                logger.info(f"▶️ [DB] Executando: {secure_sql}")
                db_result = db.run(secure_sql) # Retorna string ou lista de tuplas
                
                # 4. Formatação (Presenter Simplificado)
                return Orchestrator._format_success_response(
                    mode=mode,
                    data=db_result,
                    sql=secure_sql,
                    meta=generated_data
                )

            except SecurityError as se:
                logger.critical(f"⛔ Bloqueio: {se}")
                return {"type": "error", "content": f"Bloqueio de Segurança: {se}"}
                
            except Exception as db_error:
                logger.warning(f"⚠️ [DB ERROR] {db_error}")
                if attempt < max_retries:
                    logger.info("🔧 [FIXER] Corrigindo SQL...")
                    current_sql = fix_sql_query(current_sql, str(db_error))
                else:
                    return {"type": "error", "content": "Erro técnico no banco de dados após tentativas de correção."}

        return {"type": "error", "content": "Erro desconhecido."}

    @staticmethod
    def _format_success_response(mode: str, data: Any, sql: str, meta: dict) -> dict:
        """Transforma dados crus em formato que o Frontend entende."""
        
        # Se veio vazio ou string vazia
        if not data or data == "[]" or data == "":
            return {"type": "text", "content": "❌ Não encontrei nenhum registro correspondente."}

        # Formatação para ANALYTICS (Geralmente Gráficos ou Texto Resumido)
        if mode == "ANALYTICS":
            return {
                "type": "chart_data", # Frontend deve interpretar isso
                "content": "Aqui está a análise solicitada:",
                "data": data, # Dados crus para o front montar o gráfico
                "sql": sql,
                "chart_suggestion": meta.get("chart_suggestion", "bar")
            }
            
        # Formatação para TRACKING (Cards ou Texto Detalhado)
        # Como o db.run retorna string crua de lista Python, retornamos como text/data
        # O Frontend (BiChatMessage) pode fazer parse se necessário, ou mandamos formatado aqui.
        return {
            "type": "data_result",
            "content": f"Encontrei os seguintes dados:\n{data}",
            "sql": sql,
            "data": data
        }