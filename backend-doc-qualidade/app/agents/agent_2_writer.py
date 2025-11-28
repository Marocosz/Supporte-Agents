"""
MÓDULO: app/agents/agent_2_writer.py - AGENTE DE ESCRITA TÉCNICA (WRITER)

FUNÇÃO:
O Agente 2 (Writer) é responsável pela geração do Rascunho V1, transformando o
resumo do usuário e o sumário aprovado (Agente 1) em um conteúdo técnico,
detalhado e profissional. Ele é o coração da geração de texto, sendo forçado
a seguir regras de estilo rigorosas para garantir a qualidade operacional.

ARQUITETURA:
- **Temperatura Equilibrada (0.4):** Usa uma temperatura ligeiramente mais alta
  que o Planner para permitir criatividade na escrita, mas ainda mantendo o foco.
- **Prompt Rigoroso:** O Prompt exige aderência à "Regra das 3 Dimensões"
  (QUEM, ONDE, CRITÉRIO) e o formato de saída como **Markdown Plano** dentro
  de uma string JSON (a chave `rascunho`).
- **Safety Net (Auto-Correção):** Inclui uma lógica crítica de pós-processamento
  que corrige a falha mais comum de LLMs: gerar listas ou dicionários aninhados
  onde uma string simples era esperada. Isso aumenta drasticamente a taxa de
  sucesso do Parsing de Saída.
- **Retry com Backoff:** Em caso de erro de API (conexão, limite), usa *backoff
  exponencial* para tentar novamente. Em caso de erro de *Parsing* (JSON malformado),
  usa *backoff linear* (simples espera de 1s).

RESPONSABILIDADES CHAVE:
1. **Geração de Texto:** Produzir conteúdo detalhado para cada seção do sumário.
2. **Aderência ao Estilo:** Seguir as regras operacionais (3 Dimensões, Listas
   Numeradas Markdown).
3. **Pós-processamento:** Corrigir a estrutura interna do JSON para garantir
   a validação do Pydantic.
4. **Telemetria:** Medir latência e reportar falhas/sucessos.
"""
import logging
import time
import json
import asyncio
from typing import List, Dict, Optional
from pydantic import BaseModel, Field, ValidationError

# --- Importações do LangChain ---
from app.core.llm import get_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException

# --- IMPORTAÇÃO DO SINGLETON RAG ---
from app.core.rag_pipeline import rag_pipeline

# Logger específico com namespace claro
logger = logging.getLogger("ai_agent.writer")

# --- 1. Schema de Saída (Contrato Pydantic) ---

class DraftContent(BaseModel):
    """Define o formato JSON de saída esperado: uma reflexão e o dicionário de rascunhos."""
    reflexao_estilo: str = Field(
        description="Breve nota sobre o tom técnico adotado."
    )
    rascunho: Dict[str, str] = Field(
        description="O conteúdo das seções. O valor (conteúdo) deve ser uma STRING MARKDOWN única."
    )

# --- 2. PROMPT CORRIGIDO (FORÇA MARKDOWN PLANO E FILTRO DE CONTEÚDO) ---
PROMPT_TEMPLATE = """
Você é o **Redator Técnico Sênior** da Supporte Logística.
Sua missão é escrever um documento PGP conforme normas ISO 9001, com TEXTO COMPLETO, DETALHADO, TÉCNICO, OPERACIONAL e SEM SUPERFICIALIDADE.

======================================================================
📌 FILTRO DE RELEVÂNCIA (ANTI-ALUCINAÇÃO) - LEIA COM ATENÇÃO
======================================================================
O [FONTE DE ESTILO - RAG] pode conter trechos de documentos variados (RH, Financeiro, Segurança).
**REGRA DE OURO:** Você deve ignorar COMPLETAMENTE qualquer texto do RAG que não pertença ao assunto do [RESUMO].
- Exemplo: Se o documento é sobre "Logística Reversa", **NÃO** escreva sobre "Benefícios Odontológicos", "Recrutamento" ou "Código de Ética", mesmo que o RAG mostre isso.
- Use o RAG apenas para ver o "tom de voz" e como as frases são construídas. O conteúdo factual vem EXCLUSIVAMENTE do [RESUMO].

======================================================================
📌 REGRAS DE ESTRUTURA E ESTILO
======================================================================
1. FORMATO DE SAÍDA:
   - O valor de cada chave do JSON deve ser **uma string única em Markdown**.
   - **PROIBIDO:** Criar objetos, listas JSON internas ou dicionários dentro do valor.
   - Use `\\n` para quebras de linha.

2. A REGRA DAS "3 DIMENSÕES" (Para cada etapa do processo):
   Ao descrever uma ação, cubra:
   A. **QUEM:** O cargo responsável (ex: Motorista, Conferente).
   B. **ONDE:** O sistema/ferramenta descrito no resumo (Se o usuário disse "E-mail", use "E-mail". Não invente "TOTVS" se não foi citado).
   C. **CRITÉRIO:** O que define o sucesso.

3. LISTAS NUMERADAS (OBRIGATÓRIO EM PROCESSOS):
   Nas seções de execução (Coleta, Recebimento, Triagem), use listas Markdown:
   * *Exemplo:* "1. **Conferência:** O conferente valida a nota.\\n2. **Registro:** Envia e-mail de confirmação."

IMPORTANTE: O documento deve ser escrito exclusivamente com base no RESUMO fornecido pelo usuário e no SUMÁRIO aprovado. Não adicione informações novas que não estejam no resumo.

---
[FONTE DE ESTILO - RAG (Use com cuidado!)]
{contexto_rag}
---
[FONTE DA VERDADE - RESUMO]
{resumo_original}
---
[ESTRUTURA A SEGUIR]
{lista_de_secoes}
---

Gere o JSON final. Seja um especialista técnico focado no tema.
{format_instructions}
"""

class Agent2Writer:
    """
    Controla o fluxo do Agente 2 (Writer): focado em gerar conteúdo detalhado,
    corrigir o formato JSON e gerenciar a resiliência de API.
    """
    def __init__(self):
        logger.info("Inicializando Agente 2 (Writer) - Modo Equilibrado Markdown...")
        
        # Temperatura 0.4: Promove criatividade na escrita, mas com controle
        self.llm = get_llm(temperature=0.4)
        
        # Parser para o Pydantic Schema DraftContent
        self.output_parser = JsonOutputParser(pydantic_object=DraftContent)
        
        # Montagem do Prompt com as instruções de formato do Parser
        self.prompt = ChatPromptTemplate.from_template(
            PROMPT_TEMPLATE,
            partial_variables={
                "format_instructions": self.output_parser.get_format_instructions()
            }
        )
        
        # Chain de execução
        self.chain = self.prompt | self.llm | self.output_parser

    def _get_rag_context(self, query: str) -> str:
        """
        Traz contexto de RAG para inspiração de estilo e tom, minimizando o risco
        de copiar conteúdo factual (por isso a limitação de 4000 chars).
        """
        if not rag_pipeline.retriever:
            logger.warning("[Writer] Retriever indisponível. Usando estilo padrão.")
            return "Estilo: Formal, técnico, ISO 9001."
        try:
            # Busca documentos relevantes
            docs = rag_pipeline.retriever.invoke(query)
            logger.info(f"[RAG-Writer] Recuperados {len(docs)} docs para inspiração de estilo.")
            # Concatena e limita o tamanho para não poluir o prompt principal
            context_text = "\n\n".join([d.page_content for d in docs])
            return context_text[:4000]
        except Exception as e:
            logger.error(f"[RAG-Writer] Falha na busca: {e}")
            return ""

    async def generate_draft(self, resumo_original: str, sumario_aprovado: List[str]) -> Dict[str, str]:
        """
        Gera o rascunho completo, aplicando lógica de retry e auto-correção do JSON.
        """
        start_time = time.perf_counter()
        
        # 1. Prepara Inputs
        rag_context = self._get_rag_context(resumo_original)
        # Converte a lista de seções em uma string simples para o LLM processar
        sumario_str = ", ".join(sumario_aprovado)
        
        chain_input = {
            "contexto_rag": rag_context,
            "resumo_original": resumo_original,
            "lista_de_secoes": sumario_str
        }

        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                logger.info(f"[Writer] Tentativa {attempt + 1}/{max_retries}. Gerando rascunho equilibrado...")
                
                # Execução da Chain
                response_dict = await self.chain.ainvoke(chain_input)
                
                # --- INÍCIO DO "SAFETY NET" (PÓS-PROCESSAMENTO PARA CORREÇÃO) ---
                # Verifica se o LLM alucinou um JSON aninhado e o corrige para uma string plana
                if "rascunho" in response_dict and isinstance(response_dict["rascunho"], dict):
                    for k, v in response_dict["rascunho"].items():
                        if isinstance(v, dict):
                            # Se for um dicionário (ex: {"1": "Passo 1"}), converte para string numerada
                            logger.warning(f"[Writer] Safety Net: Corrigindo dict aninhado na seção: {k}")
                            response_dict["rascunho"][k] = "\n".join([f"{sk}. {sv}" for sk, sv in v.items()])
                        elif isinstance(v, list):
                            # Se for uma lista, converte para string de lista Markdown (bullets)
                            logger.warning(f"[Writer] Safety Net: Corrigindo list aninhada na seção: {k}")
                            response_dict["rascunho"][k] = "\n".join([f"- {item}" for item in v])
                # --- FIM DO SAFETY NET ---
                
                # 2. Validação Pydantic (Agora mais chances de sucesso após a correção)
                validated_output = DraftContent.model_validate(response_dict)
                
                # 3. Integrity Check: Garante que o LLM não esqueceu nenhuma seção
                missing_sections = [s for s in sumario_aprovado if s not in validated_output.rascunho]
                if missing_sections:
                    logger.warning(f"[Writer] Alerta: LLM esqueceu das seções: {missing_sections}")
                    # Adiciona um placeholder para não quebrar o fluxo
                    for s in missing_sections:
                        validated_output.rascunho[s] = "[Conteúdo pendente de geração]"

                # 4. Telemetria e Retorno
                total_len = sum(len(v) for v in validated_output.rascunho.values())
                elapsed_time = (time.perf_counter() - start_time) * 1000
                
                logger.info(json.dumps({
                    "event": "agent_execution_success",
                    "agent": "agent_2_writer",
                    "latency_ms": round(elapsed_time, 2),
                    "sections_generated": len(validated_output.rascunho),
                    "total_chars": total_len,
                    "style_reflection": validated_output.reflexao_estilo
                }, ensure_ascii=False))

                return validated_output.rascunho

            except (OutputParserException, ValueError, json.JSONDecodeError, ValidationError) as e:
                # Erro de JSON/Parsing: LLM gerou formato irreconhecível mesmo após o Safety Net
                logger.warning(f"[Writer] Erro de JSON/Parsing na tentativa {attempt + 1}: {e}")
                last_error = e
                # Backoff Linear (espera fixa) para erros de formato
                await asyncio.sleep(1) 
            except Exception as e:
                # Erro crítico (API connection, Rate Limit, etc.)
                logger.error(f"[Writer] Erro crítico de API: {e}")
                last_error = e
                # Backoff Exponencial para erros de API (2, 4, 8 segundos...)
                wait_time = 2 ** attempt
                logger.info(f"Aguardando {wait_time} segundos antes de tentar novamente...")
                await asyncio.sleep(wait_time)

        # Fallback em caso de falha total
        elapsed_time = (time.perf_counter() - start_time) * 1000
        logger.error(json.dumps({
            "event": "agent_execution_failed",
            "agent": "agent_2_writer",
            "latency_ms": round(elapsed_time, 2),
            "error": str(last_error) if last_error else "Max retries exceeded"
        }))
        
        # Gera uma exceção para notificar o Orquestrador que o fluxo falhou
        raise Exception(f"Falha ao gerar rascunho após {max_retries} tentativas. Erro: {last_error}")

# Cria a instância única do Agente 2
agent_2_writer = Agent2Writer()