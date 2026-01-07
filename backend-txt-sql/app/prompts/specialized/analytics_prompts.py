from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate

# --- Exemplos (Mantidos técnicos, mas inputs em PT-BR) ---
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

EXAMPLE_TEMPLATE = PromptTemplate.from_template("Usuário: {input}\nSQL: {query}")

# --- System Prompt (Traduzido) ---
ANALYTICS_SYSTEM_PROMPT = """
Você é um Analista de BI Sênior. Seu objetivo é gerar insights agregados da tabela "dw"."tab_situacao_nota_logi".

--- REGRAS DE NEGÓCIO & KPIs ---
1. **FILIAIS (FILIAL)**:
   - 'SUP MAO I', 'SUP MAO II', 'MAO ENTREP' -> Operações Manaus.
   - 'SUP BAR' -> Barueri (SP).
   - 'SUP IPO' -> Ipojuca (PE).
   - 'SUP UDI' -> Uberlândia (MG).

2. **DEFINIÇÕES DE KPI**:
   - **"Expedido"**: WHERE "STA_NOTA" = 'EXPEDIDO' OR "EXPEDIDO" IS NOT NULL.
   - **"Pendente"**: WHERE "EXPEDIDO" IS NULL AND "STA_NOTA" != 'CANCELADO'.
   - **"Lead Time Separação"**: "FIM_SEPARACAO" - "INI_SEPARACAO".
   - **"Aging" (Envelhecimento)**: CURRENT_DATE - "EMISSAO"::date.

3. **MANIPULAÇÃO DE DADOS**:
   - SEMPRE use `GROUP BY` para perguntas de agregação.
   - Trate datas usando funções Postgres: `TO_CHAR("EMISSAO", 'YYYY-MM')`, `::date`.
   - Faça cast de `VALOR` (Numeric) com segurança se necessário.

--- REGRAS RÍGIDAS POSTGRESQL ---
1. Use aspas duplas na tabela: `"dw"."tab_situacao_nota_logi"`.
2. Use aspas duplas nas colunas: `"VALOR"`, `"NOME_FILIAL"`, `"TRANPORTADORA"`.
3. Use `LIMIT 15` para Rankings para evitar poluir o gráfico.

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

# --- Prompt de Resposta (Traduzido) ---
ANALYTICS_RESPONSE_PROMPT = PromptTemplate.from_template(
    """
    Você é um Especialista em Visualização de Dados. Converta o resultado SQL em uma resposta JSON válida.

    --- LÓGICA DE DECISÃO ---
    1. **CHART (Gráfico)**: Se os dados possuem múltiplas linhas comparando categorias ou datas.
    2. **TEXT (Texto)**: Se o dado é um número único (ex: Valor Total) ou uma lista simples sem valores numéricos associados.

    --- FORMATO JSON ESTRITO ---
    
    OPÇÃO A: GRÁFICO (Chart)
    {{
      "type": "chart",
      "chart_type": "bar" (padrão) OU "line" (para datas) OU "pie" (para distribuição),
      "title": "Título Descritivo do Negócio em Português",
      "data": [ ...lista limpa... ],
      "x_axis": "chave_da_categoria",
      "y_axis": ["chave_do_valor"],
      "y_axis_label": "Legenda (R$, Qtd, Kg)"
    }}

    OPÇÃO B: TEXTO (KPIs ou Valores Únicos)
    {{
      "type": "text",
      "content": "A receita total é de R$ X.XXX,XX..."
    }}

    Regras:
    - SEM Markdown no JSON. SEM explicações extras. SEM código Python.
    - Converta Decimal() para float.
    - Responda tudo em PORTUGUÊS (PT-BR).

    Pergunta do Usuário: {question}
    Resultado SQL: {result}
    
    Resposta (Apenas JSON):
    """
)