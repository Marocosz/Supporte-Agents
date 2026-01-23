from langchain_core.prompts import PromptTemplate

# Template Otimizado para Baixa Latência (Estilo Keyword Mapping)
# Removemos explicações longas para o modelo focar na classificação rápida.
ROUTER_TEMPLATE = """
Classifique a mensagem em EXATAMENTE UMA destas categorias: TRACKING, ANALYTICS ou CHAT.
NÃO explique. Responda apenas a palavra.

<TRACKING>
Contexto: Busca pontual de entidades, Status, Onde está, Quem fez.
Keywords: Status, Nota, Pedido, Carga, Quem conferiu, Onde está, Rastreio, Detalhes da nota.
Refs: "e ela?", "qual o valor dela?", "detalhes disso".

<ANALYTICS>
Contexto: Agregações, BI, Visão Macro, Relatórios.
Keywords: Total, Soma, Média, Contagem, Top, Ranking, Evolução, Gráfico, Quantos, Valor, Produtividade.

<CHAT>
Contexto: Conversa geral fora do domínio logístico.
Keywords: Oi, Olá, Obrigado, Ajuda, Tchau, Bom dia, Quem é você.

Histórico Recente:
{chat_history}

Mensagem Atual: {question}

Categoria (apenas a palavra):
"""

ROUTER_PROMPT = PromptTemplate.from_template(ROUTER_TEMPLATE)