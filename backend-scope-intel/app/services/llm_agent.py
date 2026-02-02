# ==============================================================================
# ARQUIVO: app/services/llm_agent.py
#
# OBJETIVO:
#   Módulo responsável pela interação com a Inteligência Artificial Generativa (OpenAI/GPT).
#   Aqui é onde a "mágica" de dar nome e sentido aos clusters acontece.
#
# RESPONSABILIDADES:
#   - Montar o Prompt de Sistema e Usuário
#   - Enviar amostras de texto dos erros para o modelo GPT-4
#   - Receber e validar a resposta estruturada (JSON)
#   - Garantir que a IA não invente dados (Alucinação) restringindo o escopo
# ==============================================================================

import logging
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def summarize_cluster(cluster_id: int, texts: list[str]) -> dict:
    """
    Usa a IA (GPT-4) para gerar um rótulo curto e técnico para um grupo de chamados.
    
    ESTRATÉGIA DE PROMPT (Chain-of-Thought implícito):
    Damos ao modelo o papel de um Analista N3 e pedimos que ele analise os textos
    brutos para encontrar o padrão subjacente.
    
    ENTRADA:
        - cluster_id: Apenas para logs/rastreabilidade.
        - texts: Lista de 5 a 10 strings contendo 'Título' e 'Descrição' de chamados reais.
    
    SAÍDA ESPERADA (JSON):
        {
            "titulo": "Erro de Timeout no PDV",  (Curto, max 6 palavras)
            "descricao": "Ocorre falha de comunicação ao finalizar vendas..." (Explicação técnica)
        }
    """
    
    # Se for o cluster -1, é Ruído (chamados que não se agrupam)
    # Não gastamos tokens da OpenAI com ruído.
    if cluster_id == -1:
        return {
            "titulo": "Chamados Dispersos (Ruído)",
            "descricao": "Chamados únicos ou sem padrão definido identificados pelo algoritmo."
        }

    # PROMPT DE SISTEMA
    # Define a 'Persona' e as regras rígidas de formatação.
    # O uso de 'response_format={"type": "json_object"}' na chamada da API
    # exige que a palavra 'JSON' apareça no prompt.
    system_prompt = (
        "Você é um Analista de Suporte N3 Sênior. Sua tarefa é identificar padrões de erros.\n"
        "Regras:\n"
        "1. Seja extremamente conciso e técnico.\n"
        "2. O Título deve ter no máximo 6 palavras.\n"
        "3. Identifique o Sistema e o Erro Raiz.\n"
        "4. Retorne APENAS um JSON no formato: {\"titulo\": \"...\", \"descricao\": \"...\"}"
    )
    
    # PREPARAÇÃO DOS DADOS (Context Window)
    # Cortamos os textos em 500 caracteres para economizar tokens e focar no início (onde geralmente está o erro).
    # O delimitador '\n---\n' ajuda a IA a separar um chamado do outro.
    examples_text = "\n---\n".join([t[:500] for t in texts])
    
    user_prompt = f"Analise estes chamados agrupados e defina o problema raiz:\n\n{examples_text}"

    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL, # Ex: gpt-3.5-turbo ou gpt-4o
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],

            response_format={"type": "json_object"} # Garante que volta um JSON válido (Feature nova da OpenAI)
        )
        
        # Parse do conteúdo retornado
        content = response.choices[0].message.content
        import json
        return json.loads(content)

    except Exception as e:
        logger.error(f"Erro ao resumir cluster {cluster_id}: {e}")
        # Fallback gracioso: Se a IA falhar (timeout/erro), não quebra o pipeline,
        # apenas retorna um label genérico.
        return {
            "titulo": f"Cluster {cluster_id} (Erro na IA)",
            "descricao": "Não foi possível gerar a descrição automática."
        }