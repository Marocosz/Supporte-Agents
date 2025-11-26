"""
MÓDULO: app/agents/agent_3_reviser.py - AGENTE DE REVISÃO E INJEÇÃO (REVISER)

FUNÇÃO:
O Agente 3 (Reviser) atua como um "Cirurgião de Texto". Ele é ativado em dois
momentos críticos do fluxo:
1. **Revisão Manual:** Aplica o feedback de texto livre do usuário ao rascunho.
2. **Injeção de Detalhes:** Incorpora as respostas coletadas durante a fase
   de QA (Agente 4) para enriquecer o texto.

Seu principal objetivo é realizar a mudança solicitada com precisão cirúrgica,
sem alterar o conteúdo das seções que não foram mencionadas no feedback,
mantendo assim a integridade do trabalho anterior.

ARQUITETURA:
- **Temperatura Baixa (0.3):** Essencial para promover o determinismo e evitar
  a criatividade desnecessária, focando estritamente na aplicação das mudanças.
- **Chain of Thought (Plano de Ação):** Força o LLM a declarar seu plano
  (quais seções serão afetadas e quais serão preservadas) antes de gerar o JSON.
- **Integrity Check (Pós-processamento):** A lógica mais crítica. Após receber
  o output do LLM, o Python verifica se alguma chave de seção foi
  acidentalmente deletada pelo modelo (Amêsnia). Se sim, restaura o conteúdo
  original da chave perdida.
- **Regras de Ouro:** O prompt reforça a regra de "Preservação Total" e
  "Injeção Orgânica de Dados".

RESPONSABILIDADES CHAVE:
1. **Aplicação Fiel de Feedback:** Modificar o texto exatamente onde solicitado.
2. **Preservação de Integridade:** Garantir que o dicionário de saída
   contenha TODAS as chaves de seção do dicionário de entrada.
3. **Telemetria:** Medir o "delta size" (porcentagem de mudança no documento)
   para rastrear a magnitude da revisão.
"""
import logging
import time
import json
from typing import Dict, List, Any
from pydantic import BaseModel, Field, ValidationError

# --- Importações do LangChain ---
from app.core.llm import get_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException

# --- IMPORTAÇÃO DO SINGLETON RAG ---
from app.core.rag_pipeline import rag_pipeline

# Logger específico com namespace claro
logger = logging.getLogger("ai_agent.reviser")

# --- 1. Schema de Saída (Contrato Pydantic) ---

class RevisionOutput(BaseModel):
    """Define o formato JSON de saída esperado, incluindo o CoT (plano de ação)."""
    plano_de_acao: str = Field(
        description="Um resumo passo-a-passo (bullet points) do que será alterado e do que será PRESERVADO."
    )
    rascunho_revisado: Dict[str, str] = Field(
        description="O dicionário completo do documento, contendo as seções alteradas e as seções mantidas intactas."
    )

# --- 2. PROMPT ENGINEERING (MODO CIRURGIÃO) ---

PROMPT_TEMPLATE = """
Você é o Editor Sênior.
Sua tarefa é refinar o rascunho com base no feedback.

### MODOS DE OPERAÇÃO:
1. **SE HOUVER FEEDBACK ESPECÍFICO:** Siga-o estritamente (ex: "Mude o prazo").
2. **SE O FEEDBACK FOR VAGO OU O TEXTO ESTIVER CURTO:**
    - Sua obrigação é **EXPANDIR E ENRIQUECER** o texto.
    - Transforme frases curtas em parágrafos explicativos.
    - Adicione detalhes técnicos plausíveis baseados no contexto logístico.
    - Torne o documento mais profissional e robusto.

### TAREFA
Aplique o [FEEDBACK DO USUÁRIO] ao [RASCUNHO ATUAL].

### REGRAS DE OURO (Segurança de Dados)
1.  **PRESERVAÇÃO TOTAL:** Se o feedback não menciona uma seção específica, você deve devolvê-la EXATAMENTE como ela estava. Não reescreva por capricho.
2.  **INJEÇÃO DE DADOS:** Se o feedback contém "INJETAR RESPOSTA", pegue o fato novo e integre-o organicamente ao texto da seção alvo. Não apenas cole no final; reescreva a frase para fluir bem.
3.  **ESTILO:** Mantenha o tom formal e técnico (ISO 9001).

### PLANO DE AÇÃO (Chain of Thought)
Antes de gerar o JSON, explique brevemente:
1.  Qual seção será afetada?
2.  Qual é a natureza da mudança (Correção, Adição, Remoção)?
3.  Confirme que as outras seções serão mantidas.

---
[CONTEXTO RAG (Para manter consistência de termos)]
{contexto_rag}
---
[RESUMO ORIGINAL (A Verdade Factual)]
{resumo_original}
---
[RASCUNHO ATUAL (Documento Vivo - JSON)]
{rascunho_atual_json}
---
[FEEDBACK / NOVOS DADOS (Sua Ordem de Serviço)]
{user_feedback}
---

Gere o JSON com o plano de ação e o rascunho revisado completo.
{format_instructions}
"""

class Agent3Reviser:
    def __init__(self):
        logger.info("Inicializando Agente 3 (Reviser) com Integrity Checks...")
        
        # Temperatura 0.3: Preciso e confiável para tarefas de edição
        self.llm = get_llm(temperature=0.3)
        
        # Parser para o Pydantic Schema RevisionOutput
        self.output_parser = JsonOutputParser(pydantic_object=RevisionOutput)
        
        # Montagem do Prompt, incluindo as instruções de formato e o CoT
        self.prompt = ChatPromptTemplate.from_template(
            PROMPT_TEMPLATE,
            partial_variables={
                "format_instructions": self.output_parser.get_format_instructions()
            }
        )
        
        # Chain de execução
        self.chain = self.prompt | self.llm | self.output_parser

    def _get_rag_context(self, feedback: str, resumo: str) -> str:
        """
        Busca contexto RAG para ajudar a manter a terminologia consistente
        ao injetar novos detalhes ou expandir seções vagas.
        """
        if not rag_pipeline.retriever:
            return ""
        try:
            # Combina o resumo original e o feedback para uma busca mais precisa
            query = f"{feedback} {resumo}"[:200]
            docs = rag_pipeline.retriever.invoke(query)
            # Limita a 3000 caracteres para evitar poluição
            return "\n".join([d.page_content for d in docs])[:3000]
        except Exception as e:
            logger.warning(f"[Reviser] Erro no RAG: {e}")
            return ""

    async def revise_draft(self, resumo_original: str, rascunho_atual: Dict[str, str], user_feedback: str) -> Dict[str, str]:
        """
        Executa a revisão principal, aplicando o feedback e realizando o Integrity Check.

        Args:
            resumo_original: Resumo inicial para contexto.
            rascunho_atual: O estado atual do rascunho (dicionário de seções).
            user_feedback: O feedback de texto ou as respostas de injeção.

        Returns:
            Dict[str, str]: O rascunho revisado.
        """
        start_time = time.perf_counter()
        
        # 1. Prepara Inputs
        rag_context = self._get_rag_context(user_feedback, resumo_original)
        # Transforma o rascunho atual em uma string JSON para o LLM processar
        rascunho_json_str = json.dumps(rascunho_atual, ensure_ascii=False)
        
        logger.info(f"[Reviser] Processando feedback: '{user_feedback[:50]}...' sobre {len(rascunho_atual)} seções.")

        chain_input = {
            "contexto_rag": rag_context,
            "resumo_original": resumo_original,
            "rascunho_atual_json": rascunho_json_str,
            "user_feedback": user_feedback
        }

        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                # 2. Execução da Chain
                response_dict = await self.chain.ainvoke(chain_input)
                validated_output = RevisionOutput.model_validate(response_dict)
                new_draft = validated_output.rascunho_revisado

                # --- 3. ENGENHARIA DE SEGURANÇA: INTEGRITY CHECK ---
                # Garante que o LLM não tenha apagado nenhuma seção não mencionada
                original_keys = set(rascunho_atual.keys())
                new_keys = set(new_draft.keys())
                
                missing_keys = original_keys - new_keys # Chaves que estavam no original, mas não estão no novo
                
                if missing_keys:
                    logger.warning(f"[Reviser] ALERTA DE AMNÉSIA: O modelo esqueceu as seções {missing_keys}. Restaurando do original...")
                    # Auto-correção: Adiciona as seções perdidas de volta
                    for key in missing_keys:
                        new_draft[key] = rascunho_atual[key]

                # 4. Telemetria e Retorno
                len_original = len(str(rascunho_atual))
                len_new = len(str(new_draft))
                # Calcula a magnitude da mudança
                delta_percent = ((len_new - len_original) / len_original) * 100
                
                elapsed_time = (time.perf_counter() - start_time) * 1000

                # Log Estruturado de Sucesso
                logger.info(json.dumps({
                    "event": "agent_execution_success",
                    "agent": "agent_3_reviser",
                    "latency_ms": round(elapsed_time, 2),
                    "delta_size_percent": round(delta_percent, 2),
                    "action_plan": validated_output.plano_de_acao,
                    "restored_sections": list(missing_keys) if missing_keys else []
                }, ensure_ascii=False))

                return new_draft

            except (OutputParserException, ValueError, json.JSONDecodeError, ValidationError) as e:
                # Trata falhas de formato JSON
                logger.warning(f"[Reviser] Erro de Parsing na tentativa {attempt + 1}: {e}")
                last_error = e
                # O loop continua para a próxima tentativa
            except Exception as e:
                # Trata erros críticos (API, Conexão)
                logger.error(f"[Reviser] Erro crítico: {e}")
                raise e

        # --- FALLBACK DE FALHA ---
        # Se todas as tentativas falharem, retorna o rascunho original sem alterações
        logger.error(f"[Reviser] Falha total após retries. Retornando original. Erro: {last_error}")
        # Retorna o estado anterior para não perder o trabalho
        return rascunho_atual

# Instância Singleton
agent_3_reviser = Agent3Reviser()