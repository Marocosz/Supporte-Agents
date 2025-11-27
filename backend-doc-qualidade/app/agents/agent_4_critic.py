"""
MÓDULO: app/agents/agent_4_critic.py - AGENTE DE QA E DESIGN DE INFORMAÇÃO (CRITIC)

FUNÇÃO:
O Agente 4 (Critic) é responsável por elevar a qualidade final do documento
V1, agindo em duas frentes:
1. **Design Visual (Ativos):** Sugere elementos multimídia (diagramas Mermaid,
   tabelas, placeholders de imagem/gráfico) para substituir ou complementar
   blocos de texto densos.
2. **QA (Lacunas de Detalhe):** Formula perguntas específicas ao usuário para
   preencher informações críticas ausentes (ex: prazos, responsáveis) que
   não estavam claras no resumo inicial.

ARQUITETURA:
- **Temperatura Baixa (0.2):** Necessário para garantir a precisão sintática
  dos códigos de ativos (principalmente Mermaid, que é sensível a erros).
- **Sanitização Crítica:** Inclui funções de pós-processamento (`_sanitize_mermaid`)
  para limpar o código gerado pelo LLM de blocos Markdown (` ```mermaid `) ou
  espaços que quebram o renderizador do frontend.
- **Fail-Open (Fallback):** Em caso de falha total de *parsing* após as
  tentativas, o agente retorna listas vazias de ativos e perguntas, permitindo
  que o fluxo continue para a próxima etapa (Finalização) sem travar o usuário.

RESPONSABILIDADES CHAVE:
1. **Sugestão de Ativos:** Identificar onde o texto se beneficiaria de um visual.
2. **Formato Técnico de Ativos:** Gerar o conteúdo técnico dos ativos (código Mermaid,
   tabelas Markdown) de forma utilizável.
3. **Identificação de Lacunas:** Fazer perguntas focadas para enriquecimento.
4. **Resiliência:** Garantir a estabilidade do JSON de saída através de Sanitização
   e Retry.
"""
import logging
import time
import json
import re
from typing import List, Dict, Any
from pydantic import BaseModel, Field, ValidationError

# --- Importações do LangChain ---
from app.core.llm import get_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException

# Logger com namespace específico para rastreamento
logger = logging.getLogger("ai_agent.critic")

# --- 1. Schemas Expandidos (Contratos Pydantic) ---

class AtivoVisual(BaseModel):
    """Define a estrutura para um ativo multimídia sugerido."""
    id: str = Field(description="ID único para o ativo, ex: 'ATIVO_001'")
    secao_alvo: str = Field(
        description="O TÍTULO EXATO da seção onde este ativo deve ser inserido."
    )
    tipo_ativo: str = Field(
        description="O tipo específico: 'mermaid_graph', 'image_placeholder', 'table_data' ou 'chart_placeholder'."
    )
    conteudo: str = Field(
        description="O conteúdo técnico (código, dados CSV/Markdown, ou descrição de imagem)."
    )
    justificativa: str = Field(
        description="CoT: Uma frase curta explicando por que este visual melhora o documento nesta seção."
    )

class PerguntaEnriquecimento(BaseModel):
    """Define a estrutura para uma pergunta de QA para enriquecimento de detalhes."""
    id: str = Field(description="ID único, ex: 'PERG_001'")
    secao_alvo: str = Field(description="O TÍTULO EXATO da seção alvo.")
    pergunta: str = Field(description="A pergunta para o usuário.")
    justificativa: str = Field(description="Qual lacuna de informação esta pergunta visa preencher?")

class AnaliseQA(BaseModel):
    """O JSON de saída final do Agente 4."""
    resumo_analise: str = Field(
        description="Uma frase resumindo a qualidade geral do documento e a necessidade de visuais."
    )
    ativos: List[AtivoVisual] = Field(default=[])
    perguntas: List[PerguntaEnriquecimento] = Field(default=[])

# --- 2. PROMPT ENGINEERING (AUDITOR MULTIMÍDIA) ---

# CORREÇÃO AQUI: Escapamos as chaves em {{Decisão}} para o LangChain não confundir com variável.
PROMPT_TEMPLATE = """
Você é o **Auditor de Qualidade (QA) e Designer de Informação** da Supporte Logística.
Sua tarefa é transformar um documento de texto denso em um material rico e visual.

### 1. IDENTIFICAÇÃO DE ATIVOS VISUAIS (Seja Criativo e Preciso)
Analise cada seção e sugira ativos visuais onde o texto for complexo demais.

**TIPOS DE ATIVOS ACEITOS:**
1.  **`mermaid_graph`**: Para fluxos de processo, tomadas de decisão ou ciclos.
    * *Regra de Sintaxe:* Use `graph TD;`. (Obrigatório ponto e vírgula após TD)
    * *CRÍTICO (Formatação):* **OBRIGATÓRIO usar quebras de linha** para cada conexão. **NUNCA** coloque o gráfico todo em uma linha só. Use ENTER (\n) entre cada definição.
    * *Exemplo Correto:*
      graph TD;
      A[Início] --> B{{Decisão}}
      B -->|Sim| C[Ação 1]
      B -->|Não| D[Ação 2]
    * *Regra de IDs:* IDs dos nós (A, B, Node1) SEM espaços e SEM caracteres especiais. Rótulos visíveis devem estar entre aspas ou colchetes `["Texto"]`.
2.  **`image_placeholder`**: Para telas de sistema (software), fotos de equipamentos, EPIs ou locais físicos.
    * *Conteúdo:* Descrição exata da imagem (ex: "Captura de tela do menu 'Configurações' no sistema SAP").
3.  **`table_data`**: Quando o texto apresentar listas comparativas, de para, ou muitos números.
    * *Conteúdo:* Formate os dados em Markdown Table simples.
4.  **`chart_placeholder`**: Quando o texto citar estatísticas ou proporções (ex: "30% dos erros são no recebimento").
    * *Conteúdo:* Descrição do gráfico (ex: "Gráfico de Pizza mostrando a distribuição de erros").

### 2. IDENTIFICAÇÃO DE LACUNAS (Perguntas ao Usuário)
Faça perguntas APENAS se houver ambiguidade crítica (ex: "O texto diz 'enviar para o responsável', mas não diz quem é o responsável").
* **NÃO** pergunte sobre formatação.

### RASCUNHO PARA ANÁLISE
{rascunho_formatado}

---
Gere o JSON contendo a análise, a lista de ativos (com justificativas) e perguntas.
{format_instructions}
"""

class Agent4Critic:
    """
    Controla o fluxo do Agente 4: Geração de Ativos e Perguntas, e Sanitização.
    """
    def __init__(self):
        logger.info("Inicializando Agente 4 (Critic/QA) com Suporte Multimídia e Sanitização...")
        
        # Temperatura 0.2: Alta precisão necessária para sintaxe Mermaid e formato JSON
        self.llm = get_llm(temperature=0.2)
        
        # Configura o Parser de saída
        self.output_parser = JsonOutputParser(pydantic_object=AnaliseQA)
        
        # Montagem do Prompt
        self.prompt = ChatPromptTemplate.from_template(
            PROMPT_TEMPLATE,
            partial_variables={
                "format_instructions": self.output_parser.get_format_instructions()
            }
        )
        
        # Chain de execução
        self.chain = self.prompt | self.llm | self.output_parser

    def _sanitize_mermaid(self, code: str) -> str:
        """
        Remove wrappers de código Markdown (```mermaid...```) e espaços
        extras que frequentemente são gerados pelo LLM e quebram renderizadores.
        """
        # Remove blocos ```[linguagem] ... ```
        clean = re.sub(r"```\w*\n", "", code)
        clean = clean.replace("```", "")
        clean = clean.strip()
        
        # --- ALTERAÇÃO DE SEGURANÇA EXTRA ---
        # Se o código vier todo em uma linha (sem \n), tentamos forçar a quebra.
        # Isso ajuda caso o LLM ignore o prompt, mas o ideal é o prompt resolver.
        if "\n" not in clean and ";" in clean:
             # Se vier achatado com ponto e vírgula (graph TD; A-->B;), trocamos por quebra de linha
             clean = clean.replace(";", ";\n")
        
        return clean

    def _sanitize_table(self, content: str) -> str:
        """Garante que tabelas Markdown não tenham caracteres de escape estranhos."""
        return content.strip()

    async def get_qa_analysis(self, rascunho_aprovado: Dict[str, str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Executa a análise de QA e design, com Retry e Sanitização.
        
        Args:
            rascunho_aprovado: O dicionário de seções (Chave: Título, Valor: Conteúdo de Texto).
            
        Returns:
            Dict: Um dicionário contendo as listas de "ativos" e "perguntas" geradas.
        """
        start_time = time.perf_counter()
        
        # 1. Formata o rascunho para ser lido pelo LLM (Adiciona cabeçalhos de seção)
        rascunho_formatado = []
        for secao, conteudo in rascunho_aprovado.items():
            rascunho_formatado.append(f"### SEÇÃO: '{secao}'\n{conteudo}\n")
        
        rascunho_str = "\n".join(rascunho_formatado)

        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                logger.info(f"[QA] Tentativa {attempt + 1}/{max_retries}. Buscando oportunidades visuais...")
                
                # 2. Execução da Chain
                response_obj = await self.chain.ainvoke({"rascunho_formatado": rascunho_str})
                
                # Validação Pydantic
                validated_output = AnaliseQA.model_validate(response_obj)
                
                # --- 3. PÓS-PROCESSAMENTO E SANITIZAÇÃO ---
                ativos_list = []
                counts = {"mermaid": 0, "image": 0, "table": 0, "chart": 0}

                for ativo in validated_output.ativos:
                    # Aplica a sanitização baseada no tipo de ativo
                    if ativo.tipo_ativo == 'mermaid_graph':
                        ativo.conteudo = self._sanitize_mermaid(ativo.conteudo)
                        counts["mermaid"] += 1
                    elif ativo.tipo_ativo == 'table_data':
                        ativo.conteudo = self._sanitize_table(ativo.conteudo)
                        counts["table"] += 1
                    elif "image" in ativo.tipo_ativo:
                        counts["image"] += 1
                    elif "chart" in ativo.tipo_ativo:
                        counts["chart"] += 1
                        
                    # Converte o objeto Pydantic para um dicionário padrão antes de retornar
                    ativos_list.append(ativo.model_dump())

                perguntas_list = [p.model_dump() for p in validated_output.perguntas]

                # 4. Telemetria Detalhada
                elapsed_time = (time.perf_counter() - start_time) * 1000
                
                # Log Estruturado de Sucesso
                logger.info(json.dumps({
                    "event": "agent_execution_success",
                    "agent": "agent_4_critic",
                    "latency_ms": round(elapsed_time, 2),
                    "total_assets": len(ativos_list),
                    "asset_breakdown": counts,
                    "questions_raised": len(perguntas_list),
                    "qa_summary": validated_output.resumo_analise
                }, ensure_ascii=False))

                # Retorna o resultado no formato esperado pelo Orquestrador
                return {
                    "ativos": ativos_list,
                    "perguntas": perguntas_list
                }

            except (OutputParserException, ValueError, json.JSONDecodeError, ValidationError) as e:
                # Trata erros de formato
                logger.warning(f"[QA] Erro de Parsing na tentativa {attempt + 1}: {e}")
                last_error = e
            except Exception as e:
                # Trata erros críticos (API, Conexão)
                logger.error(f"[QA] Erro crítico: {e}")
                raise e

        # --- FALLBACK SEGURO (FAIL-OPEN) ---
        # 5. Se todas as tentativas falharem, retorna listas vazias.
        # Isso permite que o documento de texto seja finalizado sem ativos.
        elapsed_time = (time.perf_counter() - start_time) * 1000
        logger.error(json.dumps({
            "event": "agent_execution_failed_fallback",
            "agent": "agent_4_critic",
            "latency_ms": round(elapsed_time, 2),
            "error": str(last_error) if last_error else "Max retries exceeded"
        }))
        
        return {"ativos": [], "perguntas": []}

# Cria a instância única do Agente 4
agent_4_critic = Agent4Critic()