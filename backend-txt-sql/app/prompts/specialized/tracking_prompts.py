from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate

# --- Exemplos (Atualizados com DISTINCT ON para multi-série) ---
TRACKING_EXAMPLES = [
    {
        "input": "Qual o status da nota fiscal 54321?", 
        # Query inteligente: Traz uma linha por série, sempre a mais recente
        "query": 'SELECT DISTINCT ON ("SERIE") "STA_NOTA", "EMISSAO", "EXPEDIDO", "TRANPORTADORA", "SERIE" FROM "dw"."tab_situacao_nota_logi" WHERE "NOTA_FISCAL" = 54321 ORDER BY "SERIE", "last_updated" DESC;'
    },
    {
        "input": "Quem conferiu o pedido PED-9988?", 
        "query": 'SELECT DISTINCT ON ("SERIE") "NOME_CONFERENTE", "INI_CONFERENCIA" FROM "dw"."tab_situacao_nota_logi" WHERE "PEDIDO" = \'PED-9988\' ORDER BY "SERIE", "last_updated" DESC;'
    },
    {
        "input": "Qual o valor da nota 40908?",
        "query": 'SELECT DISTINCT ON ("SERIE") "VALOR", "SERIE" FROM "dw"."tab_situacao_nota_logi" WHERE "NOTA_FISCAL" = 40908 ORDER BY "SERIE", "last_updated" DESC;'
    }
]

EXAMPLE_TEMPLATE = PromptTemplate.from_template("Usuário: {input}\nSQL: {query}")

# --- System Prompt ---
TRACKING_SYSTEM_PROMPT = """
Você é um Especialista em Rastreamento Logístico. Gere SQL para "dw"."tab_situacao_nota_logi".
Gere APENAS o código SQL. NÃO EXPLIQUE.

--- REGRA DE OURO (MÚLTIPLAS SÉRIES E VERSÕES) ---
Uma nota pode ter várias séries e várias atualizações.
Para pegar a versão mais recente de CADA série, use **SEMPRE**:
`SELECT DISTINCT ON ("SERIE") ... ORDER BY "SERIE", "last_updated" DESC`

--- ATENÇÃO AOS NOMES (CRÍTICO) ---
1. A coluna de transportadora é **"TRANPORTADORA"** (sem o 'S').
2. A coluna de data de atualização é **"last_updated"** (com 'd').

--- DICIONÁRIO DE DADOS ---
1. STATUS: 'ACOLHIDO', 'EM SEPARAÇÃO', 'EXPEDIDO', 'BLOQUEADO'.
2. IDs: "NOTA_FISCAL" (Numeric), "PEDIDO" (ILIKE).
3. VALORES: "VALOR" (Numeric).
4. SÉRIE: "SERIE" (Varchar).

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

# --- Response Prompt (Adaptado para lista de resultados) ---
TRACKING_RESPONSE_PROMPT = PromptTemplate.from_template(
    """
    Dados do banco: {result}
    Pergunta Original: {question}

    Gere APENAS um JSON (sem markdown). NÃO use código Python.
    
    LÓGICA DE RESPOSTA:
    1. Se vieram múltiplos registros (várias séries), liste todos eles.
    2. Se veio apenas um, mostre o card padrão.
    3. Se perguntou algo específico (valor), responda direto.

    CASO 1: "REGISTRO_NAO_ENCONTRADO":
    {{
        "type": "text",
        "content": "❌ Não encontrei nenhum registro para essa nota/pedido."
    }}

    CASO 2: Resultado Único ou Múltiplo (Card Inteligente):
    {{
        "type": "text",
        "content": "📦 **Status Atual:** [STATUS]\\n🔢 **Série:** [SERIE]\\n🚚 **Transportadora:** [TRANSP]\\n📅 **Data:** [DATA]\\n\\n(Repita se houver mais séries...)"
    }}
    
    CASO 3: Dado Específico (Valor/Chave):
    {{
        "type": "text",
        "content": "✅ **Valor (Série [SERIE]):** R$ [VALOR]"
    }}
    """
)