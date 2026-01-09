from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate

# --- Exemplos ---
TRACKING_EXAMPLES = [
    {
        "input": "Qual o status da nota fiscal 54321?", 
        "query": 'SELECT "STA_NOTA", "EMISSAO", "EXPEDIDO", "TRANPORTADORA" FROM "dw"."tab_situacao_nota_logi" WHERE "NOTA_FISCAL" = 54321 ORDER BY "last_updated" DESC LIMIT 1;'
    },
    {
        "input": "Quem conferiu o pedido PED-9988?", 
        "query": 'SELECT "NOME_CONFERENTE", "INI_CONFERENCIA" FROM "dw"."tab_situacao_nota_logi" WHERE "PEDIDO" = \'PED-9988\' ORDER BY "last_updated" DESC LIMIT 1;'
    },
    {
        "input": "Qual o valor da nota 40908?",
        "query": 'SELECT "VALOR" FROM "dw"."tab_situacao_nota_logi" WHERE "NOTA_FISCAL" = 40908 ORDER BY "last_updated" DESC LIMIT 1;'
    }
]

EXAMPLE_TEMPLATE = PromptTemplate.from_template("Usuário: {input}\nSQL: {query}")

# --- System Prompt ---
TRACKING_SYSTEM_PROMPT = """
Você é um Especialista em Rastreamento Logístico. Gere SQL para "dw"."tab_situacao_nota_logi".
Gere APENAS o código SQL. NÃO EXPLIQUE.

--- REGRA DE OURO (DUPLICIDADE) ---
Para pegar o status atual, **SEMPRE** use:
`ORDER BY "last_updated" DESC LIMIT 1`

--- ATENÇÃO AOS NOMES (CRÍTICO) ---
1. A coluna é **"TRANPORTADORA"** (sem o 'S').
2. A coluna de data de atualização é **"last_updated"** (tudo minúsculo).

--- DICIONÁRIO DE DADOS ---
1. STATUS: 'ACOLHIDO', 'EM SEPARAÇÃO', 'EXPEDIDO', 'BLOQUEADO'.
2. IDs: "NOTA_FISCAL" (Numeric), "PEDIDO" (ILIKE).
3. VALORES: "VALOR" (Numeric).

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

# --- Response Prompt (FLEXÍVEL) ---
TRACKING_RESPONSE_PROMPT = PromptTemplate.from_template(
    """
    Dados do banco: {result}
    Pergunta Original: {question}

    Gere APENAS um JSON (sem markdown). NÃO use código Python.
    
    LÓGICA DE RESPOSTA:
    1. Analise as colunas que retornaram no "Dados do banco".
    2. Se retornou apenas um dado específico (ex: só VALOR, ou só QUEM CONFERIU), responda com uma frase direta e bonita.
    3. Se retornou o registro completo (Status, Datas, etc), monte o Card completo.

    CASO 1: "REGISTRO_NAO_ENCONTRADO":
    {{
        "type": "text",
        "content": "❌ Não encontrei nenhum registro para essa nota/pedido."
    }}

    CASO 2: Dado Específico (Ex: Perguntou só o valor):
    {{
        "type": "text",
        "content": "💰 **Valor da Nota:** R$ [VALOR_AQUI]"
    }}
    
    CASO 3: Registro Completo (Status):
    {{
        "type": "text",
        "content": "📦 **Status Atual:** [STATUS]\\n\\n🚚 **Transportadora:** [TRANSP]\\n📅 **Data:** [DATA]\\n👤 **Responsável:** [NOME]"
    }}
    """
)