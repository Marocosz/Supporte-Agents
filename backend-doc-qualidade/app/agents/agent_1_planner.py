"""
MÓDULO: app/agents/agent_1_planner.py - AGENTE DE PLANEJAMENTO (PLANNER)

FUNÇÃO:
O Agente 1 (Planner) é o primeiro passo no fluxo de trabalho. Sua missão é
traduzir o resumo inicial do usuário em uma estrutura de documento (Sumário/TOC)
coerente, padronizada e otimizada para o contexto da empresa (PGP). Ele utiliza
o padrão RAG (Retrieval-Augmented Generation) para buscar exemplos de documentos
existentes (contexto) e garantir a consistência estrutural.

ARQUITETURA:
- **Chain of Thought (CoT):** O Prompt é estruturado para forçar o LLM a
  "raciocinar" (Classificar, Padronizar, Adaptar) antes de produzir o JSON,
  melhorando a qualidade do resultado.
- **RAG Integration:** Utiliza o `rag_pipeline` (Singleton) para enriquecer
  o Prompt com contexto de documentos históricos.
- **Robustez:** Implementa uma lógica de **Retry** (tentativas) em caso de
  falha de *parsing* (quando o LLM não consegue gerar um JSON válido) e
  Telemetria para medir a latência e registrar falhas/sucessos de forma
  estruturada (JSON Log).

RESPONSABILIDADES CHAVE:
1. **Recuperação de Contexto:** Busca chunks relevantes no índice FAISS com base
   no resumo do usuário.
2. **Engenharia de Prompt:** Monta o prompt com instruções detalhadas, contexto RAG
   e regras de formato (JSON).
3. **Validação de Saída:** Garante que o output seja um objeto `DocumentTOC`
   válido.
4. **Tratamento de Erros:** Tenta refazer a chamada ao LLM se o formato JSON
   estiver incorreto.
"""
import logging
import time
import json
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from operator import itemgetter

# --- Importações do LangChain ---
from app.core.llm import get_llm # Usando a factory de LLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
from langchain_core.language_models.chat_models import BaseChatModel

# --- IMPORTAÇÃO DO SINGLETON RAG ---
from app.core.rag_pipeline import rag_pipeline

# Configuração de Logger com um nome específico para rastreamento (Telemetria)
logger = logging.getLogger("ai_agent.planner")

# --- 1. Schema de Saída (Contrato Pydantic) ---

class DocumentTOC(BaseModel):
    """Define o formato JSON de saída esperado do Agente 1."""
    raciocinio: str = Field(
        description="Uma breve explicação (1 frase) do porquê esta estrutura foi escolhida."
    )
    secoes: List[str] = Field(
        description="A lista ordenada e limpa dos títulos das seções principais."
    )

# --- 2. PROMPT ENGINEERING AVANÇADO ---

PROMPT_TEMPLATE = """
Você é o **Arquiteto de Documentação Sênior** da Supporte Logística.
Sua especialidade é criar estruturas de documentos (Sumários) alinhados à ISO 9001 e aos processos internos (PGP).

### TAREFA
Analise o [RESUMO DO USUÁRIO] e crie um Sumário (Tabela de Conteúdo) estruturado.
Utilize o [CONTEXTO RAG] apenas como referência de padrão/nomenclatura.

### FONTES DE INFORMAÇÃO
1. **[RESUMO DO USUÁRIO]** (Prioridade Máxima): O que o documento DEVE conter.
2. **[CONTEXTO RAG]** (Prioridade Secundária): Exemplos de PGPs anteriores para manter consistência.

Importante: Todo o sumário deve ser produzido exclusivamente com base no resumo fornecido pelo usuário. O material do RAG é apenas referência de estilo e estrutura, e nunca deve introduzir conteúdo factual que não esteja no resumo.

### DIRETRIZES DE RACIOCÍNIO (Chain of Thought - CoT)
1. **Classifique:** Identifique o tipo de documento (Procedimento, Manual, Política, Fluxo).
2. **Padronize:** Se for um PGP, inclua obrigatoriamente: 'Objetivo', 'Aplicação', 'Definições'.
3. **Adapte:** Se o usuário pediu algo específico (ex: "focar em segurança"), crie seções específicas para isso.
4. **Limpe:** Remova numerações (1., 2.) e balas (-).

### REGRAS DE EXCLUSÃO (Negative Constraints)
- NÃO invente siglas que não estejam no texto.
- NÃO inclua "Bibliografia" ou "Anexos" a menos que seja estritamente necessário.
- NÃO copie seções do RAG que não façam sentido para o Resumo do Usuário.

---
[CONTEXTO RAG (Histórico da Empresa)]
{contexto_rag}
---
[RESUMO DO USUÁRIO (Solicitação Atual)]
{user_summary}
---

Gere a saída estritamente em JSON.
{format_instructions}
"""

class Agent1Planner:
    """
    Controla o fluxo do Agente 1: Busca RAG, Montagem do Prompt, Execução e Retry.
    """
    def __init__(self):
        logger.info("Inicializando Agente 1 (Planner) com Telemetria e Retry...")
        
        # Inicializa LLM com temperatura baixa (0.2) para promover o determinismo
        # e a fidelidade ao formato JSON e às regras do Prompt.
        self.llm: BaseChatModel = get_llm(temperature=0.2) 
        
        # Configura o Parser de saída para validar o JSON contra o Pydantic Schema
        self.output_parser = JsonOutputParser(pydantic_object=DocumentTOC)
        
        # Configura o Prompt, injetando as instruções de formato que o Parser exige
        self.prompt = ChatPromptTemplate.from_template(
            PROMPT_TEMPLATE,
            partial_variables={
                "format_instructions": self.output_parser.get_format_instructions()
            }
        )
        
        # Define a Chain de execução (Prompt -> LLM -> Parser)
        # O retrieval é feito separadamente para adicionar a lógica de falha
        self.chain = self.prompt | self.llm | self.output_parser

    def _get_rag_context(self, query: str) -> str:
        """
        Recupera contexto do índice FAISS com tratamento de falha.
        Limita o tamanho do texto recuperado para otimizar tokens e reduzir ruído.
        """
        if not rag_pipeline.retriever:
            logger.warning("[Planner] Retriever não disponível. Usando apenas conhecimento do LLM.")
            return "Nenhum contexto histórico disponível no momento."
        
        try:
            # Invoca o Retriever com a query do usuário
            docs = rag_pipeline.retriever.invoke(query)
            # Log de quantos chunks vieram (para telemetria de RAG)
            logger.info(f"[RAG] Recuperados {len(docs)} chunks para o sumário.")
            
            # Concatena o conteúdo dos documentos e limita a 4000 caracteres
            # (Limite pragmático para manter o contexto relevante e não estourar o contexto do LLM)
            context_text = "\n\n".join([d.page_content for d in docs])
            return context_text[:4000] 
        except Exception as e:
            logger.error(f"[RAG] Erro ao buscar contexto: {e}")
            return "Erro ao recuperar contexto histórico."

    async def generate_toc(self, user_summary: str) -> List[str]:
        """
        Função principal que executa a Chain de Planejamento.
        Inclui lógica de Telemetria de Latência e Retry para falhas de Parsing.
        """
        start_time = time.perf_counter()
        
        # 1. Recupera o contexto RAG antes de montar o Prompt
        rag_context = self._get_rag_context(user_summary)
        
        # Inputs que serão passados para o Prompt Template
        chain_input = {
            "contexto_rag": rag_context,
            "user_summary": user_summary
        }

        # Lógica de Retry: tenta corrigir falhas de formato JSON
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                logger.info(f"[Planner] Tentativa {attempt + 1}/{max_retries} de geração...")
                
                # Execução assíncrona da Chain (Prompt -> LLM -> Parser)
                response_dict = await self.chain.ainvoke(chain_input)
                
                # Validação Pydantic (Garante que a estrutura final esteja correta)
                validated_output = DocumentTOC.model_validate(response_dict)
                
                # --- TELEMETRIA DE SUCESSO ---
                elapsed_time = (time.perf_counter() - start_time) * 1000 # Latência em milissegundos
                
                # Log Estruturado (JSON) de Sucesso: fácil de analisar em sistemas de monitoramento
                logger.info(json.dumps({
                    "event": "agent_execution_success",
                    "agent": "agent_1_planner",
                    "latency_ms": round(elapsed_time, 2),
                    "sections_count": len(validated_output.secoes),
                    "raciocinio_ai": validated_output.raciocinio
                }, ensure_ascii=False))

                # Retorna o resultado limpo
                return validated_output.secoes

            except (OutputParserException, ValueError, json.JSONDecodeError) as e:
                # Trata erros onde o LLM gerou um JSON malformado ou não-conforme
                logger.warning(f"[Planner] Erro de Parsing na tentativa {attempt + 1}: {e}")
                last_error = e
                # O loop continua para a próxima tentativa
            except Exception as e:
                # Trata erros não relacionados a parsing (ex: falha de API/conexão)
                logger.error(f"[Planner] Erro crítico: {e}")
                # Erros críticos são relançados imediatamente
                raise e

        # --- FALLBACK DE FALHA ---
        # Se todas as tentativas falharem
        elapsed_time = (time.perf_counter() - start_time) * 1000
        # Log Estruturado de Falha
        logger.error(json.dumps({
            "event": "agent_execution_failed",
            "agent": "agent_1_planner",
            "latency_ms": round(elapsed_time, 2),
            "error": str(last_error) if last_error else "Max retries exceeded"
        }))
        
        # Retorno de emergência para evitar que o fluxo do usuário trave
        return ["ERRO_GERACAO", "Objetivo", "Descrição do Problema", "Conclusão"]

# Cria a instância única do Agente 1
agent_1_planner = Agent1Planner()