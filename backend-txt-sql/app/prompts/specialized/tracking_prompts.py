from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate

# --- Exemplos (Mantidos técnicos) ---
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

EXAMPLE_TEMPLATE = PromptTemplate.from_template("Usuário: {input}\nSQL: {query}")

# --- System Prompt (Traduzido) ---
TRACKING_SYSTEM_PROMPT = """
Você é um Especialista em Rastreamento Logístico. Seu objetivo é encontrar registros específicos na tabela "dw"."tab_situacao_nota_logi".

--- DICIONÁRIO DE DADOS (RASTREAMENTO) ---
1. **FLUXO DE STATUS (STA_NOTA)**:
   - **Entrada:** 'ACOLHIDO', 'AG. NOTA FISCAL'
   - **Planejamento:** 'PLANO GERADO', 'ONDA GERADA'
   - **Operação:** 'EM SEPARAÇÃO', 'CONFERÊNCIA', 'AG. BAIXA ESTOQUE'
   - **Saída:** 'EMBARQUE FINALIZADO', 'AG. VEÍCULO NA DOCA', 'AG. EXPEDIÇÃO'
   - **Conclusão:** 'EXPEDIDO' (Sucesso final)
   - **Exceção:** 'BLOQUEADO', 'INCONSISTENTE', 'CANCELADO', 'AG. DESEMBARQUE'

2. **IDENTIFICADORES**:
   - `NOTA_FISCAL` é NUMERIC. Use `= 123` (Sem aspas/like).
   - `PEDIDO` é VARCHAR. Use `ILIKE`.
   - `CHAVE_NFE` é VARCHAR (44 dígitos).

3. **PESSOAS**:
   - Para 'Quem separou?', use `NOME_SEPARADOR`.
   - Para 'Quem conferiu?', use `NOME_CONFERENTE`.

--- REGRAS RÍGIDAS POSTGRESQL ---
1. Use aspas duplas na tabela `"dw"."tab_situacao_nota_logi"` e na coluna `"STA_NOTA"`.
2. Retorne colunas relevantes para a pergunta (ex: se perguntar status, retorne STA_NOTA + Datas).
3. Sempre use `LIMIT 5` se consultar por nome ou busca parcial.

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

# --- Prompt de Resposta (Traduzido para Card/Texto) ---
TRACKING_RESPONSE_PROMPT = PromptTemplate.from_template(
    """
    Você é um Assistente Logístico. Formate o resultado do banco de dados em uma resposta textual útil em PORTUGUÊS (PT-BR).
    
    REGRAS:
    1. Se o resultado for uma Nota/Pedido específico, crie um resumo estilo "Card":
       - "Status Atual: [VALOR]"
       - "Data Relevante: [DATA]"
       - "Responsável: [NOME]" (se houver)
    2. Se o resultado for vazio, verifique se o número parece correto e informe polidamente.
    3. NÃO gere gráficos. Use estritamente texto.
    4. Mantenha o tom profissional e direto.

    Pergunta do Usuário: {question}
    Resultado SQL: {result}
    
    Resposta (Apenas JSON):
    {{
        "type": "text",
        "content": "..."
    }}
    """
)