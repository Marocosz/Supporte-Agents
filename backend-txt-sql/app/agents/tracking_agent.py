import logging
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser

from app.core.llm import get_llm, get_answer_llm
from app.core.database import db_instance, get_compact_db_schema
from app.core.security import apply_security_filters
from app.core.schemas import TextResponse # <--- Importar Schema
from app.prompts.specialized.tracking_prompts import TRACKING_PROMPT, TRACKING_RESPONSE_PROMPT

logger = logging.getLogger(__name__)

def get_tracking_chain():
    """
    Cria a cadeia especialista em Rastreamento (Tracking).
    Gera SQL específico para busca de entidades únicas e formata como Texto/Card.
    """

    # Parser que valida se a saída bate com o Schema TextResponse
    parser = PydanticOutputParser(pydantic_object=TextResponse)

    # 1. Gerador de SQL
    sql_gen = (
        RunnablePassthrough.assign(schema=lambda _: get_compact_db_schema())
        | TRACKING_PROMPT
        | get_llm()
        | StrOutputParser()
    )

    # 2. Executor Seguro (Interceptor -> Banco)
    def execute_tracking_query(inputs):
        raw_sql = inputs["sql"]
        clean_raw_sql = raw_sql.replace("```sql", "").replace("```", "").strip()
        secure_sql = apply_security_filters(clean_raw_sql)
        
        logger.info(f"[TRACKING AGENT] Executing: {secure_sql}")
        
        try:
            result = db_instance.run(secure_sql)
            if not result or result == "[]" or result == "None":
                return "REGISTRO_NAO_ENCONTRADO"
            return result
        except Exception as e:
            logger.error(f"Erro no Tracking Agent: {e}")
            return f"Erro técnico na busca: {str(e)}"

    # 3. Formatador de Resposta (Agora com Validação de Schema)
    response_gen = (
        TRACKING_RESPONSE_PROMPT
        | get_answer_llm()
        | parser 
    )

    # Montagem da Cadeia
    chain = (
        RunnablePassthrough.assign(sql=sql_gen)
        .assign(result=execute_tracking_query)
        .assign(final_response=response_gen)
    )
    
    return chain