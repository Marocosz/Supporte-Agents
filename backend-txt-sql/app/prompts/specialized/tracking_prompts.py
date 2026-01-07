from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate

# --- Exemplos Focados em Rastreio ---
TRACKING_EXAMPLES = [
    {
        "input": "Qual o status da nota fiscal 54321?",
        "query": 'SELECT "STA_NOTA", "EMISSAO", "EXPEDIDO", "TRANPORTADORA" FROM "dw"."tab_situacao_nota_logi" WHERE "NOTA_FISCAL" = 54321;'
    },
    {
        "input": "Quem conferiu o pedido PED-9988?",
        "query": 'SELECT "NOME_CONFERENTE", "INI_CONFERENCIA", "FIM_CONFERENCIA" FROM "dw"."tab_situacao_nota_logi" WHERE "PEDIDO" = \'PED-9988\';'
    },
    {
        "input": "A nota 12345 já foi expedida?",
        "query": 'SELECT "STA_NOTA", "EXPEDIDO" FROM "dw"."tab_situacao_nota_logi" WHERE "NOTA_FISCAL" = 12345;'
    },
    {
        "input": "Detalhes da carga da chave 312502...",
        "query": 'SELECT * FROM "dw"."tab_situacao_nota_logi" WHERE "CHAVE_NFE" ILIKE \'%312502%\';'
    }
]

EXAMPLE_TEMPLATE = PromptTemplate.from_template("User: {input}\nSQL: {query}")

# --- System Prompt com Mapeamento de Status Real ---
TRACKING_SYSTEM_PROMPT = """
You are a Logistics Tracking Specialist. Your goal is to find specific records in "dw"."tab_situacao_nota_logi".

--- DATA DICTIONARY (TRACKING SPECIFIC) ---
1. **STATUS WORKFLOW (STA_NOTA)**:
   - **Entrada:** 'ACOLHIDO', 'AG. NOTA FISCAL'
   - **Planejamento:** 'PLANO GERADO', 'ONDA GERADA'
   - **Operação:** 'EM SEPARAÇÃO', 'CONFERÊNCIA', 'AG. BAIXA ESTOQUE'
   - **Saída:** 'EMBARQUE FINALIZADO', 'AG. VEÍCULO NA DOCA', 'AG. EXPEDIÇÃO'
   - **Conclusão:** 'EXPEDIDO' (Sucesso final)
   - **Exceção:** 'BLOQUEADO', 'INCONSISTENTE', 'CANCELADO', 'AG. DESEMBARQUE'

2. **IDENTIFIERS**:
   - `NOTA_FISCAL` is NUMERIC. Use `= 123` (No quotes/like).
   - `PEDIDO` is VARCHAR. Use `ILIKE`.
   - `CHAVE_NFE` is VARCHAR (44 digits).

3. **PEOPLE**:
   - For 'Who separated?', use `NOME_SEPARADOR`.
   - For 'Who checked?', use `NOME_CONFERENTE`.

--- POSTGRESQL HARD RULES ---
1. Double quote table `"dw"."tab_situacao_nota_logi"` and columns `"STA_NOTA"`.
2. Return columns relevant to the user's question (e.g., if they ask status, return STA_NOTA + Dates).
3. Always LIMIT 5 if querying by name/partial match to avoid flooding.

Schema:
{schema}
"""

TRACKING_PROMPT = FewShotPromptTemplate(
    examples=TRACKING_EXAMPLES,
    example_prompt=EXAMPLE_TEMPLATE,
    prefix=TRACKING_SYSTEM_PROMPT,
    suffix="User: {question}\nSQL:",
    input_variables=["question", "schema"],
    example_separator="\n\n"
)

# --- Prompt de Resposta (Texto Rico) ---
TRACKING_RESPONSE_PROMPT = PromptTemplate.from_template(
    """
    You are a Logistics Assistant. Format the database result into a helpful text response.
    
    RULES:
    1. If the result is a specific Note/Order, create a "Card" summary.
       - "Status Atual: [VALOR]"
       - "Data Relevante: [DATA]"
       - "Responsável: [NOME]"
    2. If the result is empty, verify if the number is correct.
    3. Do NOT generate charts. Use strictly text.
    4. Keep it professional and direct.

    User Question: {question}
    SQL Result: {result}
    
    Response (JSON):
    {{
        "type": "text",
        "content": "..."
    }}
    """
)