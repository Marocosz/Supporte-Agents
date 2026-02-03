# ==============================================================================
# ARQUIVO: app/services/llm_agent.py
#
# OBJETIVO:
#   Módulo responsável pela interação com a Inteligência Artificial Generativa (OpenAI/GPT).
#   Agora possui duas estratégias distintas: Análise Micro (Técnica) e Análise Macro (Executiva).
# ==============================================================================

import logging
import json
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.OPENAI_API_KEY)

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

    # PROMPT MICRO (MANTIDO O NÍVEL DE QUALIDADE ANTERIOR)
    system_prompt = (
        "Você é um Líder Técnico de Suporte (N3) especialista em triagem inteligente de chamados.\n\n"
        "Sua tarefa é analisar amostras reais de tickets, identificar padrões recorrentes e sintetizar o problema de forma clara, técnica e confiável para gestores de TI.\n\n"
        "⚠️ REGRAS IMPORTANTES (OBRIGATÓRIAS):\n"
        "- Baseie-se EXCLUSIVAMENTE nas informações presentes nas amostras fornecidas.\n"
        "- NÃO presuma causas técnicas que não estejam claramente indicadas nos textos.\n"
        "- Quando a causa não for explícita, use linguagem de hipótese (ex: 'indicam', 'sugere', 'aparente').\n"
        "- Se os chamados forem muito variados e sem padrão claro, gere um título e descrição que reflitam essa dispersão.\n\n"
        "### REGRAS PARA O TÍTULO:\n"
        "- Natural e fluido, como uma frase real. Use artigos e preposições.\n"
        "  - BOM: 'Falha na Emissão de Nota Fiscal'\n"
        "  - RUIM: 'Falha Emissão NFe'\n"
        "- Máximo de 8 palavras.\n"
        "- Proibido usar termos genéricos como 'Erro no Sistema' ou 'Falha Geral'.\n"
        "- Comece preferencialmente pelo sintoma principal (Erro, Falha, Lentidão, Bloqueio, Dificuldade).\n\n"
        "### REGRAS PARA A DESCRIÇÃO:\n"
        "- Resumo executivo para gestor de TI.\n"
        "- Descreva sintomas recorrentes, impacto percebido e sistemas afetados.\n"
        "- Texto corrido, tom profissional, sem listas ou jargões excessivos.\n\n"
        "### FORMATO DE RESPOSTA (JSON OBRIGATÓRIO):\n"
        "- NÃO inclua explicações, comentários ou texto fora do JSON.\n"
        "- Faça toda a análise internamente, mas **não exponha o raciocínio**.\n\n"
        "{\n"
        '  "titulo": "Falha na Autenticação do Portal",\n'
        '  "descricao": "Chamados indicam dificuldade recorrente de acesso ao portal..."\n'
        "}"
    )

    return _chamar_openai(system_prompt, user_content)


def gerar_analise_macro(amostra_textos: list[str], titulos_filhos: list[str]) -> dict:
    """
    Foco: EXECUTIVO E GENERALISTA.
    Usado para os PAIS (Macro-Clusters) que possuem múltiplos filhos.
    Cria uma Categoria Geral baseada nos títulos dos sub-problemas e em algumas amostras.
    """
    
    # Montamos um contexto rico: amostras + os títulos que a IA já deu para os filhos
    contexto_json = {
        "amostra_chamados_gerais": amostra_textos,
        "sub_problemas_identificados": titulos_filhos
    }
    
    user_content = json.dumps(contexto_json, ensure_ascii=False, indent=2)

    # PROMPT MACRO (NOVO, MAS MANTENDO O PADRÃO DE QUALIDADE)
    system_prompt = (
        "Você é um Gerente de TI (Service Delivery Manager) com visão executiva.\n"
        "Você está analisando um GRANDE GRUPO DE CHAMADOS que contém diversos sub-problemas técnicos (clusters menores).\n\n"
        "### OBJETIVO:\n"
        "Criar uma CATEGORIA MESTRA que englobe, de forma lógica e semântica, todos os sub-problemas listados.\n\n"
        "⚠️ REGRAS IMPORTANTES:\n"
        "- Analise os 'sub_problemas_identificados' para entender o tema central.\n"
        "- Use as 'amostra_chamados_gerais' apenas para confirmar o contexto, se necessário.\n"
        "- O Título deve soar como um Tópico de Relatório Gerencial.\n\n"
        "### REGRAS PARA O TÍTULO (MACRO):\n"
        "- Natural e fluido. Use artigos e preposições.\n"
        "- Curto e Executivo (Máx 4 a 6 palavras).\n"
        "- Use termos agrupadores: 'Instabilidade em...', 'Falhas no Módulo...', 'Problemas de Integração com...', 'Gestão de Acessos ao...'.\n"
        "- EVITE detalhes técnicos específicos demais (ex: não cite códigos de erro ORA-1234, isso pertence ao filho).\n\n"
        "### REGRAS PARA A DESCRIÇÃO (MACRO):\n"
        "- Explique o que essa categoria representa em alto nível.\n"
        "- Mencione que existem variações do problema dentro deste grupo.\n"
        "- Texto corrido, tom gerencial.\n\n"
        "### FORMATO DE RESPOSTA (JSON OBRIGATÓRIO):\n"
        "{\n"
        '  "titulo": "Instabilidade no Módulo Financeiro",\n'
        '  "descricao": "Agrupa diversos incidentes relacionados a falhas de emissão, cancelamento e consulta no módulo financeiro."\n'
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

# Mantemos a função antiga apenas para compatibilidade ou chamadas legadas.
# Ela redireciona para a análise MICRO, que é o equivalente mais próximo.
def summarize_cluster(cluster_id: int, texts: list[str], top_servicos: dict = None) -> dict:
    if cluster_id == -1:
        return {
            "titulo": "Chamados Dispersos (Ruído)",
            "descricao": "Chamados únicos ou sem padrão definido identificados pelo algoritmo."
        }
    return gerar_analise_micro(texts, top_servicos)