# ==============================================================================
# ARQUIVO: app/services/llm_agent.py
#
# OBJETIVO:
#   Módulo responsável pela interação com a Inteligência Artificial Generativa (OpenAI/GPT).
#   Agora possui duas estratégias distintas: Análise Micro (Técnica) e Análise Macro (Executiva).
# ==============================================================================

import logging
import json

from openai import OpenAI, AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.OPENAI_API_KEY)
aclient = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def gerar_analise_micro_async(amostra_textos: list[str], top_servicos: dict = None) -> dict:
    """
    Versão ASSÍNCRONA de gerar_analise_micro.
    """
    # Formata os Top Serviços para o Prompt (Contexto Extra)
    contexto_servicos = ""
    if top_servicos:
        lista_servicos = ", ".join([f"{k} ({v})" for k, v in top_servicos.items()])
        contexto_servicos = f"SERVIÇOS MAIS AFETADOS: {lista_servicos}\n"

    # Preparação das amostras (texto completo)
    formatted_texts = []
    for i, t in enumerate(amostra_textos, 1):
        formatted_texts.append(f"--- CHAMADO {i} ---\n{t}")
    examples_block = "\n".join(formatted_texts)

    user_content = (
        f"{contexto_servicos}\n"
        f"AMOSTRAS DE CHAMADOS:\n{examples_block}"
    )

    # PROMPT MICRO (Mesmo do síncrono)
    system_prompt = (
        "Você é um Líder Técnico de Suporte (N3). Sua meta é triagem rápida.\n"
        "Analise as amostras de erros e gere um diagnóstico direto.\n\n"
        "### REGRAS PARA O TÍTULO:\n"
        "- Use linguagem natural e fluida (artigos aceitos).\n"
        "- Foco na CAUSA RAIZ ou SINTOMA PRINCIPAL.\n"
        "- Ex: 'Lentidão no Acesso ao Portal', 'Erro de Timeout na API'.\n"
        "- Máx 7 palavras. SEMPRE comece com letra maiúscula.\n\n"
        "### REGRAS PARA A DESCRIÇÃO:\n"
        "- SEJA BREVE. Máximo de 2 frases curtas.\n"
        "- Diga apenas O QUE está acontecendo e QUEM/ONDE está afetando.\n"
        "- Sem detalhes técnicos excessivos (IDs, Stacktraces longos).\n"
        "- Ex: 'Usuários relatam impossibilidade de emitir notas devido a timeout no serviço de integração. O problema afeta todas as filiais.'\n\n"
        "### TAGS (NOVO):\n"
        "- Liste 3 a 5 palavras-chave técnicas ou de negócio.\n"
        "- Ex: ['Timeout', 'NFe', 'Oracle', 'Lentidão']\n\n"
        "### FORMATO JSON (OBRIGATÓRIO):\n"
        "{\n"
        '  "titulo": "...",\n'
        '  "descricao": "...",\n'
        '  "tags": ["...", "..."]\n'
        "}"
    )

    return await _chamar_openai_async(system_prompt, user_content)

def gerar_analise_micro(amostra_textos: list[str], top_servicos: dict = None) -> dict:
    """
    Foco: TÉCNICO E ESPECÍFICO.
    Usado para os FILHOS (Micro-Clusters).
    Analisa os logs brutos para identificar a falha técnica raiz.
    """
    # Formata os Top Serviços para o Prompt (Contexto Extra)
    contexto_servicos = ""
    if top_servicos:
        lista_servicos = ", ".join([f"{k} ({v})" for k, v in top_servicos.items()])
        contexto_servicos = f"SERVIÇOS MAIS AFETADOS: {lista_servicos}\n"

    # Preparação das amostras (texto completo)
    formatted_texts = []
    for i, t in enumerate(amostra_textos, 1):
        formatted_texts.append(f"--- CHAMADO {i} ---\n{t}")
    examples_block = "\n".join(formatted_texts)

    user_content = (
        f"{contexto_servicos}\n"
        f"AMOSTRAS DE CHAMADOS:\n{examples_block}"
    )

    # PROMPT MICRO (OTIMIZADO PARA CONCISÃO)
    system_prompt = (
        "Você é um Líder Técnico de Suporte (N3). Sua meta é triagem rápida.\n"
        "Analise as amostras de erros e gere um diagnóstico direto.\n\n"
        "### REGRAS PARA O TÍTULO:\n"
        "- Use linguagem natural e fluida (artigos aceitos).\n"
        "- Foco na CAUSA RAIZ ou SINTOMA PRINCIPAL.\n"
        "- Ex: 'Lentidão no Acesso ao Portal', 'Erro de Timeout na API'.\n"
        "- Máx 7 palavras. SEMPRE comece com letra maiúscula.\n\n"
        "### REGRAS PARA A DESCRIÇÃO:\n"
        "- SEJA BREVE. Máximo de 2 frases curtas.\n"
        "- Diga apenas O QUE está acontecendo e QUEM/ONDE está afetando.\n"
        "- Sem detalhes técnicos excessivos (IDs, Stacktraces longos).\n"
        "- Ex: 'Usuários relatam impossibilidade de emitir notas devido a timeout no serviço de integração. O problema afeta todas as filiais.'\n\n"
        "### TAGS (NOVO):\n"
        "- Liste 3 a 5 palavras-chave técnicas ou de negócio.\n"
        "- Ex: ['Timeout', 'NFe', 'Oracle', 'Lentidão']\n\n"
        "### FORMATO JSON (OBRIGATÓRIO):\n"
        "{\n"
        '  "titulo": "...",\n'
        '  "descricao": "...",\n'
        '  "tags": ["...", "..."]\n'
        "}"
    )

    return _chamar_openai(system_prompt, user_content)


async def gerar_analise_macro_async(dados_filhos: list[dict]) -> dict:
    """
    Versão ASSÍNCRONA de gerar_analise_macro.
    """
    # Montamos o contexto com Título + Descrição de cada filho
    contexto_filhos = []
    for f in dados_filhos:
        contexto_filhos.append(f"Sub-Grupo '{f['titulo']}': {f['descricao']}")
    
    # Montamos a string final para o user_content
    user_content = "SUB-PROBLEMAS IDENTIFICADOS:\n" + "\n".join(contexto_filhos)

    # PROMPT MACRO (Mesmo do síncrono)
    system_prompt = (
        "Você é um Executivo de TI. Você recebeu uma lista de 'Sub-Problemas' que já foram analisados tecnicamente.\n"
        "Sua tarefa é criar uma CATEGORIA MESTRA que agrupe logicamente esses sub-problemas.\n\n"
        "### REGRAS PARA O TÍTULO (MACRO):\n"
        "- Não invente. Olhe para os títulos e descrições dos filhos e encontre o denominador comum.\n"
        "- Se todos os filhos falam de 'Lentidão', o Pai deve ser 'Instabilidades de Performance'.\n"
        "- Se os filhos são variados (ex: Login + Sessão + Senha), o Pai deve ser 'Problemas de Acesso e Autenticação'.\n"
        "- Use linguagem corporativa fluida. (Máx 6 palavras).\n\n"
        "### REGRAS PARA A DESCRIÇÃO (MACRO):\n"
        "- Resuma o impacto geral acumulado.\n"
        "- Não liste todos os filhos. Diga a natureza do grupo.\n"
        "- Curto e direto (Máx 2 frases).\n\n"
        "### TAGS (MACRO):\n"
        "- Gere 3 a 5 tags de escopo geral (Módulos afetados, Tipo de falha).\n"
        "- Ex: ['Financeiro', 'Acesso', 'Crítico']\n\n"
        "### FORMATO JSON:\n"
        "{\n"
        '  "titulo": "...",\n'
        '  "descricao": "...",\n'
        '  "tags": ["...", "..."]\n'
        "}"
    )
    
    return await _chamar_openai_async(system_prompt, user_content)


def gerar_analise_macro(dados_filhos: list[dict]) -> dict:
    """
    Foco: EXECUTIVO E GENERALISTA.
    Usado para os PAIS (Macro-Clusters).
    
    CRÍTICO: Baseia-se nas DESCRIÇÕES já geradas pela IA para os filhos,
    e não mais nos textos brutos dos chamados. Isso garante consistência e melhor generalização.
    """
    
    # Montamos o contexto com Título + Descrição de cada filho
    contexto_filhos = []
    for f in dados_filhos:
        contexto_filhos.append(f"Sub-Grupo '{f['titulo']}': {f['descricao']}")
    
    # Montamos a string final para o user_content
    user_content = "SUB-PROBLEMAS IDENTIFICADOS:\n" + "\n".join(contexto_filhos)

    # PROMPT MACRO (EMBASADO NAS DESCRIÇÕES DOS FILHOS)
    system_prompt = (
        "Você é um Executivo de TI. Você recebeu uma lista de 'Sub-Problemas' que já foram analisados tecnicamente.\n"
        "Sua tarefa é criar uma CATEGORIA MESTRA que agrupe logicamente esses sub-problemas.\n\n"
        "### REGRAS PARA O TÍTULO (MACRO):\n"
        "- Não invente. Olhe para os títulos e descrições dos filhos e encontre o denominador comum.\n"
        "- Se todos os filhos falam de 'Lentidão', o Pai deve ser 'Instabilidades de Performance'.\n"
        "- Se os filhos são variados (ex: Login + Sessão + Senha), o Pai deve ser 'Problemas de Acesso e Autenticação'.\n"
        "- Use linguagem corporativa fluida. (Máx 6 palavras).\n\n"
        "### REGRAS PARA A DESCRIÇÃO (MACRO):\n"
        "- Resuma o impacto geral acumulado.\n"
        "- Não liste todos os filhos. Diga a natureza do grupo.\n"
        "- Curto e direto (Máx 2 frases).\n\n"
        "### TAGS (MACRO):\n"
        "- Gere 3 a 5 tags de escopo geral (Módulos afetados, Tipo de falha).\n"
        "- Ex: ['Financeiro', 'Acesso', 'Crítico']\n\n"
        "### FORMATO JSON:\n"
        "{\n"
        '  "titulo": "...",\n'
        '  "descricao": "...",\n'
        '  "tags": ["...", "..."]\n'
        "}"
    )
    
    return _chamar_openai(system_prompt, user_content)


def _chamar_openai(system_prompt: str, user_content: str) -> dict:
    """Função auxiliar genérica para chamadas OpenAI JSON com tratamento de erro."""
    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        return json.loads(content)

    except Exception as e:
        # Usa logger.exception para mostrar o stack trace completo no terminal
        logger.exception(f"Erro CRÍTICO na chamada OpenAI: {e}")
        # Fallback gracioso
        return {
            "titulo": "Erro na Análise Automática",
            "descricao": "Não foi possível gerar a descrição devido a uma falha na IA (Verifique Logs)."
        }

async def _chamar_openai_async(system_prompt: str, user_content: str) -> dict:
    """Versão Async da auxiliar genérica."""
    try:
        response = await aclient.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        return json.loads(content)

    except Exception as e:
        logger.exception(f"Erro CRÍTICO na chamada OpenAI (Async): {e}")
        return {
            "titulo": "Erro na Análise Automática",
            "descricao": "Não foi possível gerar a descrição devido a uma falha na IA."
        }


# Mantemos a função antiga apenas para compatibilidade ou chamadas legadas.
# Ela redireciona para a análise MICRO, que é o equivalente mais próximo.
def summarize_cluster(cluster_id: int, texts: list[str], top_servicos: dict = None) -> dict:
    if cluster_id == -1:
        return {
            "titulo": "Chamados Dispersos (Ruído)",
            "descricao": "Chamados únicos ou sem padrão definido identificados pelo algoritmo."
        }
    return gerar_analise_micro(texts, top_servicos)