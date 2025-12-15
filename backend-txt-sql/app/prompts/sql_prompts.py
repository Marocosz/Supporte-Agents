# =================================================================================================
# =================================================================================================
#
#                     PROMPT ENGINEERING HUB - O CÉREBRO DA APLICAÇÃO
#
# -------------------------------------------------------------------------------------------------
# Propósito do Arquivo:
# -------------------------------------------------------------------------------------------------
# Este arquivo é o centro de controle da inteligência artificial do sistema. Ele centraliza
# todas as instruções (prompts) que definem as "personalidades" e "habilidades" de cada
# componente de IA, garantindo que a lógica conversacional seja clara, manutenível e
# fácil de aprimorar.
#
# -------------------------------------------------------------------------------------------------
# Arquitetura e Princípio de Design:
# -------------------------------------------------------------------------------------------------
# A arquitetura segue o princípio de "Separação de Responsabilidades", onde cada tarefa
# complexa é dividida entre múltiplos "especialistas" de IA que operam em sequência,
# como uma linha de montagem:
#
# 1. O Porteiro (`ROUTER_PROMPT`):
#    - Responsabilidade: Classificar a intenção do usuário.
#    - Ação: Decide se a pergunta é uma conversa casual ou uma consulta ao banco,
#      direcionando-a para o caminho correto.
#
# 2. O Especialista em Contexto (`REPHRASER_PROMPT`):
#    - Responsabilidade: Resolver ambiguidades, contexto e correções.
#    - Ação: Analisa a pergunta e o histórico para realizar três ações chave:
#      - **Reescrever** perguntas de acompanhamento (ex: "e da filial matriz?") em perguntas completas.
#      - **Manter** perguntas que já são claras e autônomas, sem alterá-las.
#      - **Corrigir** a rota ao interpretar reclamações do usuário (ex: "você errou"), reformulando a pergunta anterior com base na nova informação.
#
# 3. O Engenheiro SQL (`SQL_PROMPT`):
#    - Responsabilidade: Traduzir linguagem natural para SQL.
#    - Ação: Recebe a pergunta já clara do Especialista em Contexto e a converte em
#      uma query PostgreSQL precisa, focado na tabela `tab_situacao_nota_logi`.
#
# 4. O Analista de Dados (`FINAL_ANSWER_PROMPT`):
#    - Responsabilidade: Formatar a resposta final para o usuário.
#    - Ação: Transforma o resultado bruto do banco de dados em uma resposta amigável,
#      seja em texto ou em um JSON estruturado para gráficos.
#
# Este design modular torna o sistema mais robusto, previsível e fácil de depurar.
#
# =================================================================================================
# =================================================================================================

# Importa as classes necessárias do LangChain para construir os templates de prompt.
# PromptTemplate é usado para prompts simples com variáveis.
# FewShotPromptTemplate é para prompts mais complexos que aprendem com exemplos.
from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate

# --- Bloco 1: O Engenheiro de Banco de Dados (SQL_PROMPT) ---

# Define uma lista de exemplos de alta qualidade (técnica de "Few-Shot Learning").
# Estes exemplos foram ATUALIZADOS para a nova estrutura de tabela única (`tab_situacao_nota_logi`).
# ATUALIZAÇÃO CRÍTICA: As queries agora usam ASPAS DUPLAS nas colunas e na tabela para
# respeitar o Case Sensitivity do PostgreSQL e o schema 'dw'.
FEW_SHOT_EXAMPLES = [
    {
        "input": "Quantas notas já foram expedidas?",
        "query": 'SELECT count(*) FROM "dw"."tab_situacao_nota_logi" WHERE "EXPEDIDO" IS NOT NULL;'
    },
    {
        "input": "Qual o valor total de pedidos da Filial 01?",
        "query": 'SELECT SUM("VALOR") FROM "dw"."tab_situacao_nota_logi" WHERE "FILIAL" = \'01\';'
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
        "input": "Qual a produtividade do separador JOAO SILVA? (Quantas notas ele separou)",
        "query": 'SELECT COUNT(*) FROM "dw"."tab_situacao_nota_logi" WHERE "NOME_SEPARADOR" = \'JOAO SILVA\';'
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
        "input": "Qual o tempo médio de separação (diferença entre fim e início)?",
        "query": 'SELECT AVG("FIM_SEPARACAO" - "INI_SEPARACAO") as tempo_medio_separacao FROM "dw"."tab_situacao_nota_logi" WHERE "FIM_SEPARACAO" IS NOT NULL AND "INI_SEPARACAO" IS NOT NULL;'
    }
]

# Cria um template para formatar cada um dos exemplos acima em um texto consistente.
EXAMPLE_PROMPT_TEMPLATE = PromptTemplate.from_template(
    "User question: {input}\nSQL query: {query}"
)

# Define as instruções principais para o LLM Gerador de SQL.
# Mantivemos a rigidez para garantir que ele não invente colunas e use aspas duplas.
SQL_GENERATION_SYSTEM_PROMPT = """
Você é um assistente especialista em PostgreSQL e Logística. Sua única tarefa é gerar uma query SQL com base na pergunta do usuário e no esquema do banco de dados.

REGRA DE OURO (CRÍTICA PARA ESTE BANCO):
1. USE ASPAS DUPLAS EM TODOS OS NOMES DE COLUNAS E TABELAS.
   - O banco é Case Sensitive. Se você escrever SELECT VALOR, vai dar erro.
   - ERRADO: SELECT VALOR FROM tab_situacao_nota_logi
   - CERTO:  SELECT "VALOR" FROM "dw"."tab_situacao_nota_logi"

2. O schema correto da tabela é 'dw'.
   - Sempre referencie a tabela como "dw"."tab_situacao_nota_logi".

3. NÃO INVENTE COLUNAS.
   - Use apenas as colunas listadas no 'Schema do Banco' abaixo.

4. SINTAXE:
   - A query deve ser sintaticamente correta para PostgreSQL.
   - Não inclua explicações ou ```sql``` na saída, apenas o código da query.

**Sua Resposta Final DEVE SER APENAS O CÓDIGO SQL.**
---
Aqui está o esquema do banco de dados: {schema}

Considere os seguintes exemplos de perguntas e queries bem-sucedidas (Note o uso de aspas):
"""

# Monta o prompt final para a geração de SQL.
# `prefix`: Contém as instruções principais e o esquema do banco.
# `examples`: A lista de exemplos que o LLM usará para aprender.
# `suffix`: Onde a pergunta final do usuário é inserida.
# `input_variables`: Declara quais variáveis este prompt espera receber.
SQL_PROMPT = FewShotPromptTemplate(
    examples=FEW_SHOT_EXAMPLES,
    example_prompt=EXAMPLE_PROMPT_TEMPLATE,
    prefix=SQL_GENERATION_SYSTEM_PROMPT,
    suffix="User question: {question}\nSQL query:",
    input_variables=["question", "schema"],
    example_separator="\n\n"
)

"""
--- Exemplo de Uso e Saída (SQL_PROMPT) ---

INPUT (O que a cadeia fornece a este prompt):
{
  "question": "Qual o número total de notas para o cliente 'Mercado X'?",
  "schema": "Tabela: tab_situacao_nota_logi\nColunas: DESTINATARIO (varchar), NOTA_FISCAL (numeric)..."
}

SAÍDA GERADA PELO LLM:
SELECT COUNT(*) FROM "dw"."tab_situacao_nota_logi" WHERE "DESTINATARIO" = 'Mercado X';
"""


# --- Bloco 2: O Analista de Dados e Comunicador (FINAL_ANSWER_PROMPT) ---

# Define as instruções para o LLM que formata a resposta final para o usuário.
# Ele recebe o resultado bruto do banco e a pergunta original (já reescrita).
FINAL_ANSWER_PROMPT = PromptTemplate.from_template(
    """
    Sua tarefa é atuar como analista de dados e assistente de comunicação.
    Dada a pergunta original do usuário e o resultado da consulta ao banco, formule a melhor resposta possível em português.

    **Regras de Formatação da Saída:**
    1. Se for apropriado para gráfico (dados agrupados, séries, comparações), responda em JSON de gráfico.
    2. Se for valor único, lista simples ou texto, responda em JSON de texto.
    3. Nunca responda em texto puro. Sempre JSON válido.
    4. Se o usuário pedir um tipo de gráfico, use-o. Senão, escolha o mais apropriado.
    5. Se o 'Resultado do Banco de Dados' for `RESULTADO_VAZIO: ...`, sua resposta deve ser um JSON de texto informando que os dados não foram encontrados. Nunca invente uma resposta.

    ---
    **Formato JSON para gráficos:**
    {{
      "type": "chart",
      "chart_type": "bar | line | pie",
      "title": "Título do gráfico",
      "data": [{{"campo1": "valor1", "campo2": 10}}, {{"campo1": "valor2", "campo2": 20}}],
      "x_axis": "campo eixo X",
      "y_axis": ["campo eixo Y"],
      "y_axis_label": "Descrição eixo Y"
    }}

    **Formato JSON para texto:**
    {{
      "type": "text",
      "content": "Resposta em texto claro aqui."
    }}
    ---

    Pergunta Original: {question}
    Resultado do Banco de Dados:
    {result}

    {format_instructions}

    **Sua Resposta (apenas JSON):**
    """
)

"""
--- Exemplo de Uso e Saída (FINAL_ANSWER_PROMPT) ---

INPUT (Exemplo 1 - Texto):
{
  "question": "Quantas notas foram expedidas?",
  "result": "[{'count': 450}]",
  "format_instructions": "The output must be a valid JSON. See above."
}

SAÍDA GERADA PELO LLM (Exemplo 1):
{
    "type": "text",
    "content": "Foram expedidas um total de 450 notas fiscais."
}

---

INPUT (Exemplo 2 - Gráfico):
{
  "question": "Qual o valor total de notas por filial?",
  "result": "[('MATRIZ', 500000.00), ('FILIAL SP', 300000.00)]",
  "format_instructions": "The output must be a valid JSON. See above."
}

SAÍDA GERADA PELO LLM (Exemplo 2):
{
    "type": "chart",
    "chart_type": "bar",
    "title": "Valor Total por Filial",
    "data": [{"filial": "MATRIZ", "valor": 500000.00}, {"filial": "FILIAL SP", "valor": 300000.00}],
    "x_axis": "filial",
    "y_axis": ["valor"],
    "y_axis_label": "Valor Total (R$)"
}
"""


# --- Bloco 3: O Porteiro (ROUTER_PROMPT) ---

# Define as instruções para o LLM classificador de intenção.
# Sua única função é decidir se a pergunta do usuário é uma conversa casual
# ou se ela precisa ser enviada para a complexa cadeia de consulta ao banco de dados.

ROUTER_PROMPT = PromptTemplate.from_template(
    """
    Sua tarefa é classificar o texto do usuário em uma das duas categorias. Responda APENAS com o nome da categoria.

    ---
    Histórico da Conversa:
    {chat_history}
    ---

    Categorias:
    - `consulta_ao_banco_de_dados`: Solicitações de dados, relatórios, listas, informações específicas (inclui perguntas de acompanhamento).
    - `saudacao_ou_conversa_simples`: Saudações, despedidas, agradecimentos ou conversa sem dados.

    Texto do usuário:
    {question}

    Categoria:
    """
)

"""
--- Exemplo de Uso e Saída (ROUTER_PROMPT) ---

INPUT (Exemplo 1):
{
  "question": "Bom dia, tudo bem?",
  "chat_history": []
}

SAÍDA GERADA PELO LLM (Exemplo 1):
saudacao_ou_conversa_simples

---

INPUT (Exemplo 2):
{
  "question": "e quantas estão pendentes?",
  "chat_history": ["user: Quantas notas saíram hoje?", "assistant: Saíram 50 notas."]
}

SAÍDA GERADA PELO LLM (Exemplo 2):
consulta_ao_banco_de_dados
"""


# --- Bloco 4: O Especialista em Contexto (REPHRASER_PROMPT) ---

# Define as instruções para o LLM que reescreve a pergunta do usuário.
# Esta é a primeira etapa da cadeia de consulta ao banco. Ele pega uma pergunta
# potencialmente ambígua e o histórico do chat e a transforma em uma pergunta
# completa e autônoma, pronta para ser enviada ao Gerador de SQL.
# Define exemplos para ensinar o Rephraser a se comportar em diferentes situações (Contexto Logístico).
REPHRASER_EXAMPLES = [
    {
        "input": "e qual o valor total dela?",
        "chat_history": "Human: Qual a filial com mais notas emitidas?\nAI: A filial é 'MATRIZ'.",
        "output": "Qual o valor total das notas emitidas pela filial 'MATRIZ'?"
    },
    {
        "input": "Qual a quantidade de volumes para o Rio de Janeiro?",
        "chat_history": "Human: Olá\nAI: Olá, como posso ajudar?",
        "output": "Qual a quantidade de volumes para o Rio de Janeiro?"
    },
    {
        "input": "não, eu queria saber do conferente, não do separador.",
        "chat_history": "Human: Qual a produtividade do João?\nAI: O separador João processou 50 notas.",
        "output": "Qual a produtividade do conferente João?"
    }
]

# Formata os exemplos para o prompt.
example_prompt = PromptTemplate.from_template(
    "Histórico:\n{chat_history}\nPergunta do Usuário: {input}\nPergunta Reescrita: {output}"
)

# Define o novo prompt principal com instruções mais rígidas e o formato de exemplos.
REPHRASER_PROMPT = FewShotPromptTemplate(
    examples=REPHRASER_EXAMPLES,
    example_prompt=example_prompt,
    prefix="""Sua tarefa é reescrever a pergunta do usuário para que ela seja autônoma, usando o histórico da conversa.

Regras Importantes:
- Sua resposta DEVE SER APENAS a pergunta reescrita, sem nenhuma explicação, introdução ou frase extra.
- Se a pergunta do usuário já for completa, apenas a retorne exatamente como está.
- Se a pergunta for uma correção (ex: 'não era isso', 'você errou'), use o histórico para entender a pergunta anterior e tente reescrevê-la com a nova instrução do usuário.

Considere os seguintes exemplos:""",
    suffix="Histórico:\n{chat_history}\nPergunta do Usuário: {question}\nPergunta Reescrita:",
    input_variables=["question", "chat_history"],
    example_separator="\n\n"
)


"""
--- Exemplo de Uso e Saída (REPHRASER_PROMPT) ---

Este exemplo demonstra como o prompt lida com um usuário corrigindo uma resposta errada do bot.

INPUT (O que a cadeia fornece a este prompt):
{
  "question": "Não, eu quero saber as EXPEDIDAS.",
  "chat_history": [
      # O histórico contém a pergunta original e a resposta errada do bot
      "Human: Quantas notas estão pendentes?",
      "AI: Existem 500 notas pendentes."
  ]
}

SAÍDA GERADA PELO LLM:
Quantas notas foram expedidas?
"""