# ==============================================================================
# ARQUIVO: app/services/llm_agent.py
#
# OBJETIVO:
#   Módulo responsável pela interação com a Inteligência Artificial Generativa (OpenAI/GPT).
#   Realiza a análise semântica dos clusters (Micro e Macro) para gerar títulos e descrições humanas.
#
# PARTE DO SISTEMA:
#   Backend / IA Generativa
#
# RESPONSABILIDADES:
#   - Dialogar com a API da OpenAI (GPT-4o/Mini)
#   - Gerar análises "Micro" (Técnicas) olhando para chamados individuais
#   - Gerar análises "Macro" (Executivas) olhando para sub-grupos já analisados
#   - Implementar estratégias de Prompt Engineering (Chain-of-Thought, Evidence Based)
#
# COMUNICAÇÃO:
#   Recebe dados de: run_pipeline.py (textos ou metadados dos clusters)
#   Envia dados para: run_pipeline.py (JSON com Título, Descrição, Tags)
# ==============================================================================

import logging
import json

from openai import OpenAI, AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.OPENAI_API_KEY)
aclient = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def gerar_analise_micro_async(amostra_textos: list[str], top_servicos: dict = None, top_keywords: list[str] = None) -> dict:
    """
    Versão ASSÍNCRONA de gerar_analise_micro.
    Agora aceita top_keywords para ancorar a IA.
    """
    # Contexto Extra: Serviços
    contexto_extra = []
    if top_servicos:
        lista_servicos = ", ".join([f"{k} ({v})" for k, v in top_servicos.items()])
        contexto_extra.append(f"SERVIÇOS FREQUENTES: {lista_servicos}")
    
    # Contexto Extra: Palavras-chave Estatísticas (A âncora contra alucinação)
    if top_keywords:
        lista_keywords = ", ".join(top_keywords[:10])
        contexto_extra.append(f"TERMOS MAIS RECORRENTES NO CLUSTER (EVIDÊNCIA ESTATÍSTICA): {lista_keywords}")
        
    str_contexto = "\n".join(contexto_extra)

    # Preparação das amostras
    formatted_texts = []
    for i, t in enumerate(amostra_textos, 1):
        formatted_texts.append(f"--- AMOSTRA {i} ---\n{t}")
    examples_block = "\n".join(formatted_texts)

    user_content = (
        f"{str_contexto}\n\n"
        f"AMOSTRAS DE CHAMADOS:\n{examples_block}"
    )

    # PROMPT MICRO (Engenharia Avançada: Chain-of-Thought + Evidence Based)
    system_prompt = (
        "Você é um Especialista Sênior em Classificação de Incidentes de TI.\n"
        "Sua missão é analisar um cluster de chamados e gerar um título e descrição que representem o PADRÃO DOMINANTE.\n\n"
        "### INSTRUÇÃO DE RACIOCÍNIO (Chain-of-Thought):\n"
        "1. Analise os 'TERMOS RECORRENTES' e 'SERVIÇOS'. Eles são a verdade estatística do cluster.\n"
        "2. Se as amostras de texto parecerem confusas ou variadas, confie nos Termos Recorrentes para desempatar.\n"
        "3. Ignore outliers (ex: 4 chamados sobre 'Senha' e 1 sobre 'Impressora' -> O tema é Senha).\n\n"
        "### REGRAS PARA O TÍTULO:\n"
        "- Seja ESPECÍFICO mas PROFISSIONAL.\n"
        "- EVITE IDs/Logs Crus: Não ponha 'Error 0x8004' no título. Use 'Logs de Erro de Sistema' ou 'Falha Crítica de Aplicação'.\n"
        "- EVITE GENÉRICOS: 'Erro no Sistema' é ruim. 'Erro de Login no Protheus' é bom.\n"
        "- Máx 8 palavras. Init Caps.\n\n"
        "### REGRAS PARA A DESCRIÇÃO:\n"
        "- Explique o impacto funcional para o usuário.\n"
        "- Ex: 'Usuários reportam lentidão e timeout ao tentar acessar o módulo financeiro.'\n\n"
        "### FORMATO JSON (Obrigatório):\n"
        "{\n"
        '  "analise_racional": "Breve explicação de como você chegou à conclusão (será descartado, use para pensar).",\n'
        '  "titulo": "...",\n'
        '  "descricao": "...",\n'
        '  "tags": ["...", "..."]\n'
        "}"
    )

    result = await _chamar_openai_async(system_prompt, user_content)
    
    # Limpeza: Remove o campo de raciocínio interno para não sujar o frontend
    # Mantemos a analise_racional para debug e transparencia no frontend
    # if 'analise_racional' in result:
    #     del result['analise_racional']
        
    return result

def gerar_analise_micro(amostra_textos: list[str], top_servicos: dict = None, top_keywords: list[str] = None) -> dict:
    """
    Versão Síncrona. Mesma lógica da Async.
    """
    contexto_extra = []
    if top_servicos:
        lista_servicos = ", ".join([f"{k} ({v})" for k, v in top_servicos.items()])
        contexto_extra.append(f"SERVIÇOS FREQUENTES: {lista_servicos}")
    
    if top_keywords:
        lista_keywords = ", ".join(top_keywords[:10])
        contexto_extra.append(f"TERMOS MAIS RECORRENTES NO CLUSTER (EVIDÊNCIA ESTATÍSTICA): {lista_keywords}")
        
    str_contexto = "\n".join(contexto_extra)

    formatted_texts = []
    for i, t in enumerate(amostra_textos, 1):
        formatted_texts.append(f"--- AMOSTRA {i} ---\n{t}")
    examples_block = "\n".join(formatted_texts)

    user_content = (
        f"{str_contexto}\n\n"
        f"AMOSTRAS DE CHAMADOS:\n{examples_block}"
    )

    system_prompt = (
        "Você é um Especialista Sênior em Classificação de Incidentes de TI.\n"
        "Sua missão é analisar um cluster de chamados e gerar um título e descrição que representem o PADRÃO DOMINANTE.\n\n"
        "### INSTRUÇÃO DE RACIOCÍNIO (Chain-of-Thought):\n"
        "1. Analise os 'TERMOS RECORRENTES' e 'SERVIÇOS'. Eles são a verdade estatística do cluster.\n"
        "2. Se as amostras de texto parecerem confusas ou variadas, confie nos Termos Recorrentes para desempatar.\n"
        "3. Ignore outliers (ex: 4 chamados sobre 'Senha' e 1 sobre 'Impressora' -> O tema é Senha).\n\n"
        "### REGRAS PARA O TÍTULO:\n"
        "- Seja ESPECÍFICO mas PROFISSIONAL.\n"
        "- EVITE IDs/Logs Crus: Não ponha 'Error 0x8004' no título. Use 'Logs de Erro de Sistema' ou 'Falha Crítica de Aplicação'.\n"
        "- EVITE GENÉRICOS: 'Erro no Sistema' é ruim. 'Erro de Login no Protheus' é bom.\n"
        "- Máx 8 palavras. Init Caps.\n\n"
        "### REGRAS PARA A DESCRIÇÃO:\n"
        "- Explique o impacto funcional para o usuário.\n"
        "- Ex: 'Usuários reportam lentidão e timeout ao tentar acessar o módulo financeiro.'\n\n"
        "### FORMATO JSON (Obrigatório):\n"
        "{\n"
        '  "analise_racional": "Breve explicação de como você chegou à conclusão (será descartado, use para pensar).",\n'
        '  "titulo": "...",\n'
        '  "descricao": "...",\n'
        '  "tags": ["...", "..."]\n'
        "}"
    )

    result = _chamar_openai(system_prompt, user_content)
    
    # Mantemos a analise_racional para debug e transparencia no frontend
    # if 'analise_racional' in result:
    #     del result['analise_racional']
        
    return result


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
        '  "analise_racional": "Explique por que agrupou estes itens (raciocínio sintético).",\n'
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
        '  "analise_racional": "Explique por que agrupou estes itens (raciocínio sintético).",\n'
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
            "descricao": "Não foi possível gerar a descrição devido a uma falha na IA (Verifique Logs).",
            "analise_racional": "Falha Técnica: O modelo não retornou uma resposta válida ou ocorreu erro na chamada."
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
            "descricao": "Não foi possível gerar a descrição devido a uma falha na IA.",
            "analise_racional": "Falha Técnica: O modelo não retornou uma resposta válida ou ocorreu erro na chamada."
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