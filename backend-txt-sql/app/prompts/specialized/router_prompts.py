from langchain_core.prompts import PromptTemplate

# Template Otimizado para Baixa Latência (Instruções em PT-BR)
ROUTER_TEMPLATE = """
Classifique a intenção do usuário em exatamente uma destas categorias:

1. TRACKING:
   - Buscas por entidades específicas (Nota Fiscal, Pedido, Carga).
   - Verificação de status, datas, locais, responsáveis (quem conferiu/separou).
   - Ex: "Status da nota 123", "Onde está o pedido X?", "Quem conferiu isso?".

2. ANALYTICS:
   - Agregações sobre múltiplos registros.
   - Totais, Médias, Contagens, Rankings, Evolução temporal.
   - Solicitações de gráficos ou relatórios.
   - Ex: "Valor total por filial", "Quantas notas hoje?", "Top 5 transportadoras".

3. CHAT:
   - Saudações, agradecimentos, ajuda geral, perguntas sobre a identidade do bot.
   - Ex: "Oi", "Obrigado", "O que você faz?".

Histórico: {chat_history}
Mensagem Atual: {question}

Retorne APENAS o nome da categoria (tracking, analytics ou chat).
"""

ROUTER_PROMPT = PromptTemplate.from_template(ROUTER_TEMPLATE)