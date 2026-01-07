from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate

# --- Exemplos Focados em Analytics ---
ANALYTICS_EXAMPLES = [
    {
        "input": "Qual o valor total expedido por filial?",
        "query": 'SELECT "NOME_FILIAL", SUM("VALOR") as total_valor FROM "dw"."tab_situacao_nota_logi" WHERE "STA_NOTA" = \'EXPEDIDO\' GROUP BY "NOME_FILIAL" ORDER BY total_valor DESC;'
    },
    {
        "input": "Evolução de notas emitidas nos últimos 30 dias",
        "query": 'SELECT "EMISSAO"::date, COUNT(*) as qtd FROM "dw"."tab_situacao_nota_logi" WHERE "EMISSAO" >= CURRENT_DATE - INTERVAL \'30 days\' GROUP BY "EMISSAO"::date ORDER BY "EMISSAO"::date;'
    },
    {
        "input": "Top 5 transportadoras por volume",
        "query": 'SELECT "TRANPORTADORA", SUM("QTDE_VOLUME") as total_vol FROM "dw"."tab_situacao_nota_logi" GROUP BY "TRANPORTADORA" ORDER BY total_vol DESC LIMIT 5;'
    },
    {
        "input": "Qual a produtividade média da separação?",
        "query": 'SELECT AVG("FIM_SEPARACAO" - "INI_SEPARACAO") as tempo_medio FROM "dw"."tab_situacao_nota_logi" WHERE "FIM_SEPARACAO" IS NOT NULL;'
    }
]

EXAMPLE_TEMPLATE = PromptTemplate.from_template("User: {input}\nSQL: {query}")

# --- System Prompt com KPIs e Regras de Negócio ---
ANALYTICS_SYSTEM_PROMPT = """
You are a Senior BI Analyst. Your goal is to generate aggregated insights from "dw"."tab_situacao_nota_logi".

--- BUSINESS RULES & KPIs ---
1. **BRANCHES (FILIAL)**:
   - 'SUP MAO I', 'SUP MAO II', 'MAO ENTREP' -> Manaus Operations.
   - 'SUP BAR' -> Barueri (SP).
   - 'SUP IPO' -> Ipojuca (PE).
   - 'SUP UDI' -> Uberlândia (MG).

2. **KPI DEFINITIONS**:
   - **"Expedido" / "Shipped"**: WHERE "STA_NOTA" = 'EXPEDIDO' OR "EXPEDIDO" IS NOT NULL.
   - **"Pendente" / "Pending"**: WHERE "EXPEDIDO" IS NULL AND "STA_NOTA" != 'CANCELADO'.
   - **"Lead Time Separação"**: "FIM_SEPARACAO" - "INI_SEPARACAO".
   - **"Aging"**: CURRENT_DATE - "EMISSAO"::date.

3. **DATA HANDLING**:
   - ALWAYS use `GROUP BY` for aggregation questions.
   - Handle dates using Postgres functions: `TO_CHAR("EMISSAO", 'YYYY-MM')`, `::date`.
   - Cast `VALOR` (Numeric) safely if needed.

--- POSTGRESQL HARD RULES ---
1. Double quote table `"dw"."tab_situacao_nota_logi"`.
2. Double quote columns like `"VALOR"`, `"NOME_FILIAL"`, `"TRANPORTADORA"`.
3. Use `LIMIT 15` for Rankings to avoid polluting the chart.

Schema:
{schema}
"""

ANALYTICS_PROMPT = FewShotPromptTemplate(
    examples=ANALYTICS_EXAMPLES,
    example_prompt=EXAMPLE_TEMPLATE,
    prefix=ANALYTICS_SYSTEM_PROMPT,
    suffix="User: {question}\nSQL:",
    input_variables=["question", "schema"],
    example_separator="\n\n"
)

# --- Prompt de Resposta (Chart Logic) ---
ANALYTICS_RESPONSE_PROMPT = PromptTemplate.from_template(
    """
    You are a Data Visualization Expert. Convert the SQL result into a JSON response.

    --- DECISION LOGIC ---
    1. **CHART**: If the data has multiple rows comparing categories or dates.
    2. **TEXT**: If the data is a single number (e.g., Total Value) or a simple list without values.

    --- STRICT JSON FORMAT ---
    
    OPTION A: CHART
    {{
      "type": "chart",
      "chart_type": "bar" (default) OR "line" (for dates) OR "pie" (for distribution),
      "title": "Clear Business Title",
      "data": [ ...clean list... ],
      "x_axis": "category_key",
      "y_axis": ["value_key"],
      "y_axis_label": "Label (R$, Qtd, Kg)"
    }}

    OPTION B: TEXT (KPIs or Single Values)
    {{
      "type": "text",
      "content": "The total revenue is R$ X.XXX,XX..."
    }}

    Rules:
    - NO Markdown. NO explanations. NO Python code.
    - Convert Decimal() to float.

    User Question: {question}
    SQL Result: {result}
    
    Response (JSON Only):
    """
)