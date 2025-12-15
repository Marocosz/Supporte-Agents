# =================================================================================================
# =================================================================================================
#
#                       PROMPT ENGINEERING HUB - O CÉREBRO DA APLICAÇÃO
#
# -------------------------------------------------------------------------------------------------
# ATUALIZAÇÃO v5.0 (FINALMENTE A SOLUÇÃO):
# 1. Separador de Tarefa: Adicionado "--- CURRENT TASK ---" no Rephraser para impedir que
#    a IA copie os exemplos.
# 2. SQL: Mantidas as regras de aspas duplas e schema 'dw'.
# -------------------------------------------------------------------------------------------------

from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate

# --- Bloco 1: O Engenheiro de Banco de Dados (SQL_PROMPT) ---

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
        "input": "Mostre o valor total e a quantidade de volumes por estado de destino.",
        "query": 'SELECT "UF_DESTINO", SUM("VALOR") as valor_total, SUM("QTDE_VOLUME") as total_volumes FROM "dw"."tab_situacao_nota_logi" GROUP BY "UF_DESTINO" ORDER BY valor_total DESC;'
    },
    {
        "input": "Quais notas tiveram divergência (estão marcadas como inconsistentes)?",
        "query": 'SELECT "NOTA_FISCAL", "INCONSISTENTE" FROM "dw"."tab_situacao_nota_logi" WHERE "INCONSISTENTE" IS NOT NULL;'
    },
    {
        "input": "Qual o tempo médio de separação?",
        "query": 'SELECT AVG("FIM_SEPARACAO" - "INI_SEPARACAO") as tempo_medio_separacao FROM "dw"."tab_situacao_nota_logi" WHERE "FIM_SEPARACAO" IS NOT NULL AND "INI_SEPARACAO" IS NOT NULL;'
    }
]

EXAMPLE_PROMPT_TEMPLATE = PromptTemplate.from_template(
    "User question: {input}\nSQL query: {query}"
)

SQL_GENERATION_SYSTEM_PROMPT = """
You are a PostgreSQL Expert. Convert the user question into a SQL query.

CRITICAL RULES:
1. **DOUBLE QUOTES**: Always use double quotes for table and column names.
   - Correct: SELECT "VALOR" FROM "dw"."tab_situacao_nota_logi"
   - Incorrect: SELECT VALOR FROM tab_situacao_nota_logi

2. **SCHEMA**: The table is "dw"."tab_situacao_nota_logi".

3. **TEXT FILTERS**: Use ILIKE with % for names.
   - Correct: WHERE "NOME_FILIAL" ILIKE '%Matriz%'

4. **OUTPUT**: Return ONLY the SQL query. No Markdown. No explanation.

Schema:
{schema}

Examples:
"""

SQL_PROMPT = FewShotPromptTemplate(
    examples=FEW_SHOT_EXAMPLES,
    example_prompt=EXAMPLE_PROMPT_TEMPLATE,
    prefix=SQL_GENERATION_SYSTEM_PROMPT,
    suffix="User question: {question}\nSQL query:",
    input_variables=["question", "schema"],
    example_separator="\n\n"
)


# --- Bloco 2: O Analista de Dados (FINAL_ANSWER_PROMPT) ---

FINAL_ANSWER_PROMPT = PromptTemplate.from_template(
    """
    Atue como um Analista de BI Logístico. Analise os dados brutos e forneça insights.

    **Diretrizes de Resposta:**
    1. **Dados Agrupados?** -> Gere JSON de Gráfico (`"type": "chart"`).
    2. **Dado Único ou Lista Simples?** -> Gere JSON de Texto (`"type": "text"`).
    3. **Dado Vazio/Erro?** -> Explique educadamente que não encontrou registros.

    ---
    **Estrutura Obrigatória para Gráficos:**
    {{
      "type": "chart",
      "chart_type": "bar | line | pie",
      "title": "Título Descritivo",
      "data": [dict_com_os_dados],
      "x_axis": "nome_chave_categoria",
      "y_axis": ["nome_chave_valor"],
      "y_axis_label": "Rótulo do Eixo Y"
    }}

    **Estrutura Obrigatória para Texto:**
    {{
      "type": "text",
      "content": "Sua resposta formatada aqui."
    }}
    ---

    Pergunta Original: {question}
    Resultado SQL Bruto:
    {result}

    {format_instructions}

    **JSON de Resposta:**
    """
)


# --- Bloco 3: O Porteiro (ROUTER_PROMPT) ---

ROUTER_PROMPT = PromptTemplate.from_template(
    """
    Classifique a mensagem do usuário. Responda APENAS o nome da categoria.

    Categorias:
    1. `consulta_ao_banco_de_dados`: Pedidos de dados, relatórios, gráficos.
    2. `saudacao_ou_conversa_simples`: Oi, Olá, Obrigado.

    Histórico: {chat_history}
    Mensagem: {question}
    Categoria:
    """
)


# --- Bloco 4: O Especialista em Contexto (REPHRASER_PROMPT) ---

# Exemplos simplificados para não confundir o modelo
REPHRASER_EXAMPLES = [
    {
        "input": "e qual o valor total dela?",
        "chat_history": "Human: Qual a filial com mais notas?\nAI: A filial é 'MATRIZ'.",
        "output": "Qual o valor total das notas da filial 'MATRIZ'?"
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

# AQUI ESTÁ A CORREÇÃO: "--- CURRENT TASK ---"
REPHRASER_PROMPT = FewShotPromptTemplate(
    examples=REPHRASER_EXAMPLES,
    example_prompt=example_prompt,
    prefix="""SYSTEM ROLE: You are a standalone question generator.
YOUR GOAL: Return the user question optimized for database retrieval.

RULES:
1. **PRIORITY**: Focus on the 'Input'.
2. **STANDALONE**: If the 'Input' is a complete question (e.g. "List all notes"), IGNORE the 'Chat History' and return the 'Input' exactly as is.
3. **CONTEXT**: Only use 'Chat History' if the 'Input' contains pronouns (it, she, that).
4. **OUTPUT**: Return ONLY the rewritten text. No explanations.

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