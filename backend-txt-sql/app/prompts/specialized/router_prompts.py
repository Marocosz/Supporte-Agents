from langchain_core.prompts import PromptTemplate

# Template Otimizado para Baixa Latência (Estilo Keyword Mapping)
# Removemos textos explicativos longos para o Router decidir em < 0.5s
ROUTER_TEMPLATE = """
Classifique a mensagem em: TRACKING, ANALYTICS ou CHAT.

<TRACKING>
Contexto: Busca pontual de entidades, Status, Onde está, Quem fez.
Keywords: Status, Nota, Pedido, Carga, Quem conferiu, Onde está, Rastreio, Detalhes da nota.

<ANALYTICS>
Contexto: Agregações, BI, Visão Macro, Relatórios.
Keywords: Total, Soma, Média, Contagem, Top, Ranking, Evolução, Gráfico, Quantos, Valor, Produtividade.

<CHAT>
Contexto: Conversa geral.
Keywords: Oi, Olá, Obrigado, Ajuda, Tchau, Bom dia.

Histórico:
{chat_history}

Mensagem: {question}

Categoria (apenas a palavra):
"""

ROUTER_PROMPT = PromptTemplate.from_template(ROUTER_TEMPLATE)