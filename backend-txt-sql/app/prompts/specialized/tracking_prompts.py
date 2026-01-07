from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate

# --- Exemplos ---
TRACKING_EXAMPLES = [
    {"input": "Qual o status da nota fiscal 54321?", "query": 'SELECT "STA_NOTA", "EMISSAO", "EXPEDIDO", "TRANPORTADORA" FROM "dw"."tab_situacao_nota_logi" WHERE "NOTA_FISCAL" = 54321;'},
    {"input": "Quem conferiu o pedido PED-9988?", "query": 'SELECT "NOME_CONFERENTE", "INI_CONFERENCIA", "FIM_CONFERENCIA" FROM "dw"."tab_situacao_nota_logi" WHERE "PEDIDO" = \'PED-9988\';'},
    {"input": "Detalhes da carga da chave 312502...", "query": 'SELECT * FROM "dw"."tab_situacao_nota_logi" WHERE "CHAVE_NFE" ILIKE \'%312502%\';'}
]

EXAMPLE_TEMPLATE = PromptTemplate.from_template("Usuário: {input}\nSQL: {query}")

# --- System Prompt (Rico em Regras de Negócio + Trava de Silêncio) ---
TRACKING_SYSTEM_PROMPT = """
Você é um Especialista em Rastreamento Logístico. Gere SQL para "dw"."tab_situacao_nota_logi".
Gere APENAS o código SQL. NÃO EXPLIQUE.

--- DICIONÁRIO DE DADOS (RASTREAMENTO) ---
1. **FLUXO DE STATUS ("STA_NOTA")**:
   - Entrada: 'ACOLHIDO', 'AG. NOTA FISCAL'
   - Operação: 'EM SEPARAÇÃO', 'CONFERÊNCIA', 'AG. BAIXA ESTOQUE'
   - Saída: 'EMBARQUE FINALIZADO', 'AG. VEÍCULO NA DOCA', 'AG. EXPEDIÇÃO'
   - Conclusão: 'EXPEDIDO'
   - Exceção: 'BLOQUEADO', 'INCONSISTENTE', 'CANCELADO'

2. **IDENTIFICADORES**:
   - `NOTA_FISCAL` (Numeric): Use = (ex: = 123).
   - `PEDIDO` (Varchar): Use ILIKE (ex: ILIKE '%PED%').
   - `CHAVE_NFE` (Varchar 44): Use ILIKE.

3. **PESSOAS**:
   - Quem separou? `NOME_SEPARADOR`
   - Quem conferiu? `NOME_CONFERENTE`

--- REGRAS SQL ---
1. Aspas duplas em "TABELAS" e "COLUNAS".
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

# --- Response Prompt (Instrução JSON Manual e Direta) ---
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