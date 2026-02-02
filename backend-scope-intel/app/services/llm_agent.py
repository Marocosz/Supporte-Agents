import logging
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def summarize_cluster(cluster_id: int, texts: list[str]) -> dict:
    """
    Usa a IA (GPT-4) para gerar um rótulo para um grupo de chamados.
    
    Entrada: Lista de 5 a 10 textos representativos do grupo.
    Saída: Dicionário com 'titulo' e 'descricao'.
    """
    
    # Se for o cluster -1, é Ruído (chamados que não se agrupam)
    if cluster_id == -1:
        return {
            "titulo": "Chamados Dispersos (Ruído)",
            "descricao": "Chamados únicos ou sem padrão definido identificados pelo algoritmo."
        }

    # Prompt Otimizado para Análise Técnica
    # Usamos "System Message" para definir a persona do bot.
    system_prompt = (
        "Você é um Analista de Suporte N3 Sênior. Sua tarefa é identificar padrões de erros.\n"
        "Regras:\n"
        "1. Seja extremamente conciso e técnico.\n"
        "2. O Título deve ter no máximo 6 palavras.\n"
        "3. Identifique o Sistema e o Erro Raiz.\n"
        "4. Retorne APENAS um JSON no formato: {\"titulo\": \"...\", \"descricao\": \"...\"}"
    )
    
    # Juntamos os exemplos para enviar no prompt
    # Limitamos o tamanho de cada texto para não estourar tokens se for muito grande
    examples_text = "\n---\n".join([t[:500] for t in texts])
    
    user_prompt = f"Analise estes chamados agrupados e defina o problema raiz:\n\n{examples_text}"

    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL, # Ex: gpt-4-turbo
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0, # Temperatura zero para ser o mais determinístico possível
            response_format={"type": "json_object"} # Garante que volta um JSON válido
        )
        
        # Parse do conteúdo retornado
        content = response.choices[0].message.content
        import json
        return json.loads(content)

    except Exception as e:
        logger.error(f"Erro ao resumir cluster {cluster_id}: {e}")
        # Fallback se a IA falhar
        return {
            "titulo": f"Cluster {cluster_id} (Erro na IA)",
            "descricao": "Não foi possível gerar a descrição automática."
        }