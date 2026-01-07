from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate

# --- Exemplos ---
ANALYTICS_EXAMPLES = [
    {"input": "Qual o valor total expedido por filial?", "query": 'SELECT "NOME_FILIAL", SUM("VALOR") as total_valor FROM "dw"."tab_situacao_nota_logi" WHERE "STA_NOTA" = \'EXPEDIDO\' GROUP BY "NOME_FILIAL" ORDER BY total_valor DESC;'},
    {"input": "Evolução de notas emitidas nos últimos 30 dias", "query": 'SELECT "EMISSAO"::date, COUNT(*) as qtd FROM "dw"."tab_situacao_nota_logi" WHERE "EMISSAO" >= CURRENT_DATE - INTERVAL \'30 days\' GROUP BY "EMISSAO"::date ORDER BY "EMISSAO"::date;'},
    {"input": "Top 5 transportadoras por volume", "query": 'SELECT "TRANPORTADORA", SUM("QTDE_VOLUME") as total_vol FROM "dw"."tab_situacao_nota_logi" GROUP BY "TRANPORTADORA" ORDER BY total_vol DESC LIMIT 5;'}
]

EXAMPLE_TEMPLATE = PromptTemplate.from_template("Usuário: {input}\nSQL: {query}")

# --- System Prompt ---
ANALYTICS_SYSTEM_PROMPT = """
Você é um Analista de BI Sênior. Gere SQL para "dw"."tab_situacao_nota_logi".
Gere APENAS o código SQL. NÃO EXPLIQUE.

--- ATENÇÃO AOS NOMES DE COLUNAS (CRÍTICO) ---
1. A coluna de transportadora chama-se **"TRANPORTADORA"** (sic). 
   - Está escrito errado no banco (sem o 'S'). 
   - JAMAIS escreva "TRANSPORTADORA". Use sempre **"TRANPORTADORA"**.

--- REGRAS DE KPI ---
1. **FILIAIS**: 'SUP MAO I/II' -> Manaus, 'SUP BAR' -> Barueri.
2. **DEFINIÇÕES**: 'EXPEDIDO' (Status), 'PENDENTE' (Sem data de expedição).
3. **SQL**: 
   - Aspas duplas em "TABELAS" e "COLUNAS".
   - GROUP BY obrigatório em agregações.

Schema:
{schema}
"""

ANALYTICS_PROMPT = FewShotPromptTemplate(
    examples=ANALYTICS_EXAMPLES,
    example_prompt=EXAMPLE_TEMPLATE,
    prefix=ANALYTICS_SYSTEM_PROMPT,
    suffix="Usuário: {question}\nSQL:",
    input_variables=["question", "schema"],
    example_separator="\n\n"
)

# --- Response Prompt ---
ANALYTICS_RESPONSE_PROMPT = PromptTemplate.from_template(
    """
    Dados SQL: {result}
    Pergunta: {question}

    Gere APENAS JSON válido (sem markdown).
    
    CRÍTICO: 
    1. O campo "data" DEVE conter a lista real de valores literais.
    2. NÃO use código Python.
    3. Se o SQL retornou vazio, use o formato de TEXTO.

    OPÇÃO A - GRÁFICO:
    {{
      "type": "chart",
      "chart_type": "bar" (ou "line", "pie"),
      "title": "Título em PT-BR",
      "data": [ ... DADOS LITERAIS ... ],
      "x_axis": "nome_coluna_categ",
      "y_axis": ["nome_coluna_valor"],
      "y_axis_label": "Unidade"
    }}

    OPÇÃO B - TEXTO:
    {{
      "type": "text",
      "content": "Resumo em PT-BR..."
    }}
    """
)