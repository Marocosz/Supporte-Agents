from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate

# --- Exemplos ---
TRACKING_EXAMPLES = [
    {"input": "Qual o status da nota fiscal 54321?", "query": 'SELECT "STA_NOTA", "EMISSAO", "EXPEDIDO", "TRANPORTADORA" FROM "dw"."tab_situacao_nota_logi" WHERE "NOTA_FISCAL" = 54321;'},
    {"input": "Quem conferiu o pedido PED-9988?", "query": 'SELECT "NOME_CONFERENTE", "INI_CONFERENCIA", "FIM_CONFERENCIA" FROM "dw"."tab_situacao_nota_logi" WHERE "PEDIDO" = \'PED-9988\';'}
]

EXAMPLE_TEMPLATE = PromptTemplate.from_template("Usuário: {input}\nSQL: {query}")

# --- System Prompt ---
TRACKING_SYSTEM_PROMPT = """
Você é um Especialista em Rastreamento Logístico. Gere SQL para "dw"."tab_situacao_nota_logi".
Gere APENAS o código SQL. NÃO EXPLIQUE.

--- ATENÇÃO AOS NOMES (CRÍTICO) ---
1. A coluna é **"TRANPORTADORA"** (sem o 'S' antes do P). NÃO corrija para "TRANSPORTADORA".

--- DICIONÁRIO DE DADOS ---
1. STATUS: 'ACOLHIDO', 'EM SEPARAÇÃO', 'EXPEDIDO', 'BLOQUEADO'.
2. IDs: "NOTA_FISCAL" (Numeric), "PEDIDO" (ILIKE).
3. PESSOAS: "NOME_SEPARADOR", "NOME_CONFERENTE".

--- REGRAS SQL ---
1. Aspas duplas OBRIGATÓRIAS em "TABELAS" e "COLUNAS".
2. Use LIMIT 5 para buscas por nome/texto.

Schema:
{schema}
"""

TRACKING_PROMPT = FewShotPromptTemplate(
    examples=TRACKING_EXAMPLES,
    example_prompt=EXAMPLE_TEMPLATE,
    prefix=TRACKING_SYSTEM_PROMPT,
    suffix="Usuário: {question}\nSQL:",
    input_variables=["question", "schema"],
    example_separator="\n\n"
)

# --- Response Prompt ---
TRACKING_RESPONSE_PROMPT = PromptTemplate.from_template(
    """
    Dados do banco: {result}
    Pergunta Original: {question}

    Gere APENAS um JSON (sem markdown). NÃO use código Python.
    
    CASO 1: Se "REGISTRO_NAO_ENCONTRADO":
    {{
        "type": "text",
        "content": "Não encontrei o registro solicitado."
    }}

    CASO 2: Se houver dados:
    {{
        "type": "text",
        "content": "Resumo dos dados (Status, Datas, Responsáveis) em PT-BR."
    }}
    """
)