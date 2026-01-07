import logging
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser

from app.core.llm import get_llm, get_answer_llm
from app.core.database import db_instance, get_compact_db_schema
from app.core.security import apply_security_filters
from app.core.schemas import AgentResponse # <--- Pode ser Texto ou Gráfico
from app.prompts.specialized.analytics_prompts import ANALYTICS_PROMPT, ANALYTICS_RESPONSE_PROMPT

logger = logging.getLogger(__name__)

def clean_sql_markdown(text: str) -> str:
    return text.replace("```sql", "").replace("```", "").strip()

def get_analytics_chain():
    """
    Cria a cadeia especialista em Analytics (BI).
    Foco: Agregações, KPIs, Gráficos.
    Saída: JSON Validado (Chart ou Text).
    """

    # Parser híbrido (O LLM decide se preenche como ChartResponse ou TextResponse)
    parser = PydanticOutputParser(pydantic_object=AgentResponse)

    # 1. Gerador de SQL
    sql_gen = (
        RunnablePassthrough.assign(schema=lambda _: get_compact_db_schema())
        | ANALYTICS_PROMPT
        | get_llm()
        | StrOutputParser()
        | RunnableLambda(clean_sql_markdown)
    )

    # 2. Executor Seguro com Proteção de Volume
    def execute_analytics_query(inputs):
        raw_sql = inputs["sql"]
        secure_sql = apply_security_filters(raw_sql)
        
        # Proteção visual
        sql_lower = secure_sql.lower()
        if "select" in sql_lower and "limit" not in sql_lower and "count(" not in sql_lower:
             secure_sql = secure_sql.rstrip(";") + " LIMIT 20;"
        
        logger.info(f"[ANALYTICS AGENT] Executing: {secure_sql}")
        
        try:
            result = db_instance.run(secure_sql)
            if not result or result == "[]" or result == "None":
                return "DADOS_INSUFICIENTES_PARA_ANALISE"
            return result
        except Exception as e:
            logger.error(f"Erro no Analytics Agent: {e}")
            return f"Erro ao calcular indicadores: {str(e)}"

    # 3. Formatador de Visualização Validado
    viz_gen = (
        ANALYTICS_RESPONSE_PROMPT.partial(format_instructions=parser.get_format_instructions())
        | get_answer_llm()
        | parser # <--- Garante a estrutura Pydantic
    )

    chain = (
        RunnablePassthrough.assign(sql=sql_gen)
        .assign(result=execute_analytics_query)
        .assign(final_response=viz_gen)
    )

    return chain