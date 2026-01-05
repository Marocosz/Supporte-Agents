# =================================================================================================
# =================================================================================================
#
#                       PROMPT ENGINEERING HUB - O CÉREBRO DA APLICAÇÃO
#
# -------------------------------------------------------------------------------------------------
# ATUALIZAÇÃO v6.3 (SMART RENDER LOGIC):
# 1. SQL Generator: Mantida a robustez v6.0.
# 2. Final Answer:
#    - Lógica refinada: GROUP BY de 1 linha agora vira TEXTO (ex: "Qual o maior?").
#    - Gráfico só é gerado se houver comparação (múltiplas linhas) ou pedido explícito.
#    - Mantidas as restrições estritas de JSON (sem markdown/explicação).
# 3. Rephraser: Mantido intacto.
# -------------------------------------------------------------------------------------------------

from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate

# =================================================================================================
# BLOCO 1: O ENGENHEIRO DE BANCO DE DADOS (SQL_PROMPT) - VERSÃO ROBUSTA (MANTIDA)
# =================================================================================================

# --- Exemplos Curados (Few-Shot) ---
FEW_SHOT_EXAMPLES = [
    {
        "input": "Quantas notas já foram expedidas?",
        "query": 'SELECT count(*) FROM "dw"."tab_situacao_nota_logi" WHERE "EXPEDIDO" IS NOT NULL;'
    },
    {
        "input": "Qual o valor total de pedidos da Filial Matriz?",
        "query": 'SELECT SUM("VALOR") FROM "dw"."tab_situacao_nota_logi" WHERE "NOME_FILIAL" ILIKE \'%MATRIZ%\';'
    },
    {
        "input": "Procure pela nota fiscal número 54321.",
        "query": 'SELECT * FROM "dw"."tab_situacao_nota_logi" WHERE "NOTA_FISCAL" = 54321;'
    },
    {
        "input": "Liste as 5 notas com maior valor líquido.",
        "query": 'SELECT "NOTA_FISCAL", "VALOR" FROM "dw"."tab_situacao_nota_logi" ORDER BY "VALOR" DESC LIMIT 5;'
    },
    {
        "input": "Qual a transportadora com mais notas pendentes de expedição?",
        "query": 'SELECT "TRANPORTADORA", COUNT(*) as total_pendente FROM "dw"."tab_situacao_nota_logi" WHERE "EXPEDIDO" IS NULL GROUP BY "TRANPORTADORA" ORDER BY total_pendente DESC LIMIT 1;'
    },
    {
        "input": "Qual a produtividade do separador JOAO SILVA?",
        "query": 'SELECT COUNT(*) FROM "dw"."tab_situacao_nota_logi" WHERE "NOME_SEPARADOR" ILIKE \'%JOAO SILVA%\';'
    },
    {
        "input": "Mostre o valor total e a quantidade de volumes agrupados por Filial.",
        "query": 'SELECT "NOME_FILIAL", SUM("VALOR") as valor_total, SUM("QTDE_VOLUME") as total_volumes FROM "dw"."tab_situacao_nota_logi" GROUP BY "NOME_FILIAL" ORDER BY valor_total DESC;'
    },
    {
        "input": "Quais notas tiveram divergência (estão marcadas como inconsistentes)?",
        "query": 'SELECT "NOTA_FISCAL", "INCONSISTENTE" FROM "dw"."tab_situacao_nota_logi" WHERE "INCONSISTENTE" IS NOT NULL;'
    },
    {
        "input": "Qual o tempo médio de separação?",
        "query": 'SELECT AVG("FIM_SEPARACAO" - "INI_SEPARACAO") as tempo_medio_separacao FROM "dw"."tab_situacao_nota_logi" WHERE "FIM_SEPARACAO" IS NOT NULL AND "INI_SEPARACAO" IS NOT NULL;'
    },
    {
        "input": "Quantas notas foram emitidas hoje?",
        "query": 'SELECT COUNT(*) FROM "dw"."tab_situacao_nota_logi" WHERE "EMISSAO"::date = CURRENT_DATE;'
    }
]

EXAMPLE_PROMPT_TEMPLATE = PromptTemplate.from_template(
    "User question: {input}\nSQL query: {query}"
)

# --- O Prompt do Sistema (A "Constituição" do Agente) ---
SQL_GENERATION_SYSTEM_PROMPT = """
You are a Senior PostgreSQL Database Expert specializing in Logistics. 
Your goal is to convert user questions into accurate, executable SQL queries for the table "dw"."tab_situacao_nota_logi".

--- DATA DICTIONARY & SEMANTICS ---
1. **NOTA_FISCAL**: This is a NUMERIC field. 
   - NEVER use `ILIKE` directly on it. 
   - Exact match: `WHERE "NOTA_FISCAL" = 123`
   - Partial match: `WHERE CAST("NOTA_FISCAL" AS TEXT) ILIKE '123%'`

2. **LOCATIONS & NAMES**:
   - Always prefer `NOME_FILIAL` over `FILIAL` (which is just a code).
   - Always prefer `NOME_SEPARADOR` over `USUARIO_SEP`.
   - Always prefer `NOME_CONFERENTE` over `USUARIO_CONF`.

3. **STATUS & DATES**:
   - "Expedida" / "Shipped" implies `"EXPEDIDO" IS NOT NULL`.
   - "Pendente" / "Pending" implies `"EXPEDIDO" IS NULL`.
   - "Inconsistente" implies `"INCONSISTENTE" IS NOT NULL`.

4. **COLUMN TYPOS**: 
   - The column for carrier is spelled `"TRANPORTADORA"` (missing the 'S'). Do not correct it to "TRANSPORTADORA".

--- CRITICAL POSTGRESQL RULES ---
1. **QUOTING**: 
   - Table name MUST be double-quoted: `"dw"."tab_situacao_nota_logi"`.
   - Column names MUST be double-quoted: `"VALOR"`, `"NOME_FILIAL"`.

2. **TEXT MATCHING**: 
   - ALWAYS use `ILIKE` with `%` for text searches to be case-insensitive.
   - Example: `WHERE "NOME_FILIAL" ILIKE '%SAO PAULO%'`

3. **DATE HANDLING**:
   - For "today": `WHERE "EMISSAO"::date = CURRENT_DATE`
   - For "this month": `WHERE EXTRACT(MONTH FROM "EMISSAO") = EXTRACT(MONTH FROM CURRENT_DATE)`
   - Never use MySQL functions like `YEAR()` or `NOW()`. Use `CURRENT_DATE` or `CURRENT_TIMESTAMP`.

4. **OUTPUT FORMAT**:
   - Return ONLY the SQL query. 
   - Do NOT start with "Here is the query".
   - Do NOT use Markdown blocks (```sql).

--- SCHEMA DEFINITION ---
{schema}

--- EXAMPLES ---
"""

SQL_PROMPT = FewShotPromptTemplate(
    examples=FEW_SHOT_EXAMPLES,
    example_prompt=EXAMPLE_PROMPT_TEMPLATE,
    prefix=SQL_GENERATION_SYSTEM_PROMPT,
    suffix="User question: {question}\nSQL query:",
    input_variables=["question", "schema"],
    example_separator="\n\n"
)


# =================================================================================================
# BLOCO 2: O ANALISTA DE DADOS (FINAL_ANSWER_PROMPT) - LÓGICA INTELIGENTE
# =================================================================================================

FINAL_ANSWER_PROMPT = PromptTemplate.from_template(
    """
    Atue como um formatador de dados ESTRITO. Sua ÚNICA função é converter os dados brutos abaixo em um JSON válido.

    --- LÓGICA DE DECISÃO (IMPORTANTE) ---
    
    A. USE "chart" SE (E SOMENTE SE):
       1. O usuário PEDIU explicitamente (Ex: "gere um gráfico", "mostre em barras").
       2. OU se os dados representam uma comparação (Agregação com VÁRIAS linhas).
          - Ex: Total por Filial (5 filiais), Qtd por Status (3 status).
    
    B. USE "text" PARA TODO O RESTO:
       1. Resultado é uma ÚNICA linha (Ex: "Qual a filial com maior valor?").
       2. Resultado é uma lista de identificadores/detalhes (Ex: "Liste as notas fiscais").
       3. Buscas simples ou valores totais únicos.

    --- REGRAS CRÍTICAS DE SAÍDA ---
    1. NÃO explique nada.
    2. NÃO escreva código Python, SQL ou comentários.
    3. NÃO use Markdown (```json). Apenas comece com {{ e termine com }}.
    4. Converta objetos 'Decimal' para float ou int.

    --- ESTRUTURAS DE JSON ---

    Opção A: TEXTO (Listas, Detalhes, Valores Únicos ou Top 1)
    {{
      "type": "text",
      "content": "Resumo textual. Se for lista de notas, use quebras de linha."
    }}

    Opção B: GRÁFICO (Comparações com múltiplas linhas)
    {{
      "type": "chart",
      "chart_type": "bar" (ou "line" ou "pie"),
      "title": "Título Descritivo",
      "data": [ ...lista limpa dos dados... ],
      "x_axis": "chave_da_categoria",
      "y_axis": ["chave_do_valor"],
      "y_axis_label": "Legenda"
    }}

    --- CONTEXTO ---
    Pergunta: {question}
    
    Dados Brutos do SQL:
    {result}

    {format_instructions}

    SUA RESPOSTA JSON (SEM MARKDOWN):
    """
)


# =================================================================================================
# BLOCO 3: O PORTEIRO (ROUTER_PROMPT)
# =================================================================================================

ROUTER_PROMPT = PromptTemplate.from_template(
    """
    Você é um classificador de intenções.
    Analise a entrada do usuário e classifique em UMA das seguintes categorias:

    1. `consulta_ao_banco_de_dados`: 
       - O usuário está pedindo informações, números, relatórios, status de notas, busca de dados.
       - Ex: "Quantas notas?", "Status da nota X", "Mostre o gráfico de vendas".

    2. `saudacao_ou_conversa_simples`: 
       - Cumprimentos, agradecimentos ou conversas fora do contexto de dados.
       - Ex: "Oi", "Bom dia", "Obrigado", "Quem é você?".

    Histórico da Conversa: {chat_history}
    Mensagem Atual: {question}
    
    RESPOSTA (Apenas o nome da categoria):
    """
)


# =================================================================================================
# BLOCO 4: O ESPECIALISTA EM CONTEXTO (REPHRASER_PROMPT)
# =================================================================================================

REPHRASER_EXAMPLES = [
    {
        "input": "e qual o valor total dela?",
        "chat_history": "Human: Qual a filial com mais notas?\nAI: A filial é 'MATRIZ'.",
        "output": "Qual o valor total das notas da filial 'MATRIZ'?"
    },
    {
        "input": "Liste as notas de hoje",
        "chat_history": "Human: Bom dia\nAI: Olá!",
        "output": "Liste as notas com data de emissão igual a hoje"
    },
    {
        "input": "Qual o valor total de notas?",
        "chat_history": "",
        "output": "Qual o valor total de notas?"
    }
]

example_prompt = PromptTemplate.from_template(
    "Chat History:\n{chat_history}\nInput: {input}\nOutput: {output}"
)

REPHRASER_PROMPT = FewShotPromptTemplate(
    examples=REPHRASER_EXAMPLES,
    example_prompt=example_prompt,
    prefix="""SYSTEM ROLE: You are a query optimization engine.
YOUR GOAL: Rewrite the user input into a standalone, explicit question optimized for SQL generation.

RULES:
1. **RESOLVE PRONOUNS**: If user says "it", "she", "that", look at Chat History to find what they refer to.
2. **BE EXPLICIT**: If user says "delayed notes", rewrite to "notes where expedition date is null".
3. **STANDALONE**: If the input is already a good question, return it as is.
4. **NO CHIT-CHAT**: Do not answer the question. Just rewrite it.

Examples:""",
    suffix="""
--- CURRENT TASK ---
Chat History:
{chat_history}

Input: {question}
Output:""",
    input_variables=["question", "chat_history"],
    example_separator="\n\n"
)