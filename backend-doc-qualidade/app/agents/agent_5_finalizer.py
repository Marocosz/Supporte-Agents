"""
MÓDULO: app/agents/agent_5_finalizer.py - AGENTE DE MONTAGEM HIERÁRQUICA FINAL (FINALIZER)

FUNÇÃO:
O Agente 5 (Finalizer) é o último agente do pipeline e atua como o **Montador
Estrutural**. Sua missão é pegar todos os artefatos aprovados e consolidados
(texto enriquecido, ativos visuais) e reorganizá-los em uma estrutura hierárquica
limpa (`List[Secao]`) que corresponde ao schema `DocumentoFinalJSON`.

ARQUITETURA:
- **Determinismo (Temperatura 0.0):** Este é o agente mais determinístico,
  pois sua tarefa é de *montagem e organização*, não de criação. A temperatura
  zero garante máxima fidelidade às instruções de formato e minimiza a chance
  de alucinação ou erro de JSON.
- **Injeção Hierárquica:** O prompt o instrui a pegar os ativos aceitos (que
  são objetos planos) e transformá-los em objetos aninhados (`SubSecao`)
  dentro da `Secao` alvo.
- **Fallback Crítico:** Implementa a função `_manual_fallback_assembly` que
  entra em ação se o LLM falhar repetidamente em produzir o JSON válido. O
  fallback garante que o usuário sempre receba o documento (mesmo que sem o
  refinamento ideal de títulos e inserções do LLM).

RESPONSABILIDADES CHAVE:
1. **Consolidação:** Combinar texto e ativos aprovados.
2. **Estruturação:** Converter o dicionário plano de rascunho em uma lista
   hierárquica de objetos `Secao` e `SubSecao`.
3. **Robustez:** Garantir a taxa de sucesso final através do Determinismo e do
   mecanismo de Fallback.
4. **Injeção de Metadados:** Anexar a estrutura gerada (`corpo_documento`)
   aos metadados iniciais (`dados_iniciais`).
"""
import logging
import time
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ValidationError

# --- Importações do LangChain ---
from app.core.llm import get_llm
from app.core.schemas import DocumentoFinalJSON, Secao, SubSecao # Schemas de Contrato
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException

# Logger específico
logger = logging.getLogger("ai_agent.finalizer")

# --- 1. Schema de Saída (Contrato Pydantic para o LLM) ---

class MontagemFinal(BaseModel):
    """O formato JSON esperado para a saída do LLM antes da injeção de metadados."""
    resumo_montagem: str = Field(
        description="Breve log do que foi feito (ex: 'Inseri 3 ativos e formatei 5 seções')."
    )
    # Lista de Seções no formato hierárquico, pronto para DocumentoFinalJSON
    corpo_documento: List[Secao] = Field(
        description="A estrutura final e limpa do documento, com ativos inseridos como subseções."
    )

# --- 2. PROMPT DE MONTAGEM ESTRUTURAL ---

PROMPT_TEMPLATE = """
Você é o **Montador Final de Documentos ISO** da Supporte Logística.

Sua missão é:
1. Consolidar o texto aprovado.
2. Inserir os ativos (imagens, gráficos, mermaid) nos locais corretos.
3. Garantir uma estrutura final impecável, organizada e profissional.

======================================================================
📌 REGRAS DE MONTAGEM (OBRIGATÓRIO)
======================================================================

### 1. BASE TEXTUAL
Use o texto do [RASCUNHO DE TEXTO] como a espinha dorsal.
- Você pode ajustar transições e quebrar parágrafos longos para melhorar a leitura.
- **NÃO** altere os dados factuais (prazos, nomes, responsabilidades).

### 2. INSERÇÃO DE ATIVOS (Enriquecimento Hierárquico)
Para cada item em [ATIVOS VISUAIS]:
- Encontre a `secao_alvo`.
- Crie uma `SubSecao` (Subseção) dentro daquela Seção.
- **Título da SubSeção:** Use um nome técnico (ex: "Fluxograma do Processo", "Tabela de Registros").
- **Conteúdo da SubSeção:** Insira o conteúdo do ativo (`conteudo`).
- **Contexto:** Se necessário, adicione uma frase introdutória curta ANTES do ativo na seção principal (ex: "O diagrama abaixo ilustra o fluxo de decisão:").
- Se a seção alvo não existir, crie uma seção "Anexos" no final.

### 3. LIMPEZA FINAL
- Remova do texto principal qualquer referência residual como "::Diagrama aqui::" ou "[Inserir tabela]".
- O documento deve parecer ter sido feito por um humano especialista.

---
[RASCUNHO DE TEXTO (Dicionário de Seções)]
{rascunho_json}
---
[ATIVOS VISUAIS (Lista de Ativos Aceitos)]
{ativos_aceitos_json}
---

Gere o JSON final. Foco em organização visual e coerência.
{format_instructions}
"""

class Agent5Finalizer:
    """
    Controla o fluxo do Agente 5: Montagem determinística e Fallback de emergência.
    """
    def __init__(self):
        logger.info("Inicializando Agente 5 (Finalizer) com Montagem Hierárquica...")
        
        # Temperatura 0.0: Essencial para tarefas de formatação e montagem estrutural
        self.llm = get_llm(temperature=0.0)
        
        # Parser para o Pydantic Schema MontagemFinal
        self.output_parser = JsonOutputParser(pydantic_object=MontagemFinal)
        
        # Montagem do Prompt
        self.prompt = ChatPromptTemplate.from_template(
            PROMPT_TEMPLATE,
            partial_variables={
                "format_instructions": self.output_parser.get_format_instructions()
            }
        )
        
        # Chain de execução
        self.chain = self.prompt | self.llm | self.output_parser

    async def generate_final_json(
        self,
        dados_iniciais: DocumentoFinalJSON, # Metadados (Título, código, etc)
        rascunho_aprovado: Dict[str, str],
        ativos_aceitos: List[Dict[str, Any]],
        respostas_enriquecimento: List[Dict[str, Any]] # Apenas para log/contexto se necessário
    ) -> DocumentoFinalJSON:
        """
        Executa a montagem final, fundindo metadados, texto e ativos na estrutura hierárquica.
        """
        start_time = time.perf_counter()
        
        # 1. Preparação dos dados para o Prompt
        rascunho_str = json.dumps(rascunho_aprovado, ensure_ascii=False)
        ativos_str = json.dumps(ativos_aceitos, ensure_ascii=False)

        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                logger.info(f"[Finalizer] Tentativa {attempt + 1}. Montando documento com {len(ativos_aceitos)} ativos...")
                
                # 2. Execução da Chain
                response_obj = await self.chain.ainvoke({
                    "rascunho_json": rascunho_str,
                    "ativos_aceitos_json": ativos_str
                })
                
                # Validação Pydantic
                validated_output = MontagemFinal.model_validate(response_obj)
                
                # --- 3. MONTAGEM DO OBJETO FINAL ---
                # Cria uma cópia profunda dos metadados iniciais (DocumentoFinalJSON)
                documento_final = dados_iniciais.model_copy(deep=True)
                # Injeta o corpo hierárquico gerado pelo LLM na cópia
                documento_final.corpo_documento = validated_output.corpo_documento
                
                # 4. Telemetria
                elapsed_time = (time.perf_counter() - start_time) * 1000
                
                total_secoes = len(documento_final.corpo_documento)
                # Conta quantas subseções/ativos foram criados
                total_subsecoes = sum(len(s.subsecoes) for s in documento_final.corpo_documento)
                
                # Log Estruturado de Sucesso
                logger.info(json.dumps({
                    "event": "agent_execution_success",
                    "agent": "agent_5_finalizer",
                    "latency_ms": round(elapsed_time, 2),
                    "final_structure": {
                        "secoes": total_secoes,
                        "subsecoes_ativos": total_subsecoes
                    },
                    "assembly_log": validated_output.resumo_montagem
                }, ensure_ascii=False))

                return documento_final

            except (OutputParserException, ValueError, json.JSONDecodeError, ValidationError) as e:
                # Trata falhas de formato JSON
                logger.warning(f"[Finalizer] Erro de Parsing na tentativa {attempt + 1}: {e}")
                last_error = e
            except Exception as e:
                # Trata erros críticos (API, Conexão)
                logger.error(f"[Finalizer] Erro crítico: {e}")
                raise e

        # --- 5. FALLBACK DE EMERGÊNCIA ---
        # Se esgotar as tentativas, executa a montagem manual via Python
        logger.error(f"[Finalizer] Falha no LLM após {max_retries} retries. Iniciando Fallback Manual. Erro: {last_error}")
        return self._manual_fallback_assembly(dados_iniciais, rascunho_aprovado, ativos_aceitos)

    def _manual_fallback_assembly(
        self, 
        dados_iniciais: DocumentoFinalJSON, 
        rascunho: Dict[str, str], 
        ativos: List[Dict[str, Any]]
    ) -> DocumentoFinalJSON:
        """
        Monta o documento via código Python puro (montagem "burra") se o LLM falhar.
        Prioriza a entrega do conteúdo textual e dos ativos (sem o refinamento de transição do LLM).
        """
        corpo = []
        # Percorre o rascunho de texto
        for titulo, conteudo in rascunho.items():
            # Cria a Seção principal
            nova_secao = Secao(titulo=titulo, conteudo=conteudo, subsecoes=[])
            
            # Tenta encontrar e adicionar ativos para esta seção
            ativos_da_secao = [a for a in ativos if a['secao_alvo'] == titulo]
            for a in ativos_da_secao:
                # Cria o ativo como uma SubSecao
                nova_secao.subsecoes.append(SubSecao(
                    titulo=f"Visual: {a['tipo_ativo'].replace('_', ' ').title()}",
                    conteudo=a['conteudo']
                ))
            corpo.append(nova_secao)
            
        # Anexa o corpo montado à cópia dos metadados
        doc_final = dados_iniciais.model_copy(deep=True)
        doc_final.corpo_documento = corpo
        return doc_final

# Cria a instância Singleton do Agente 5
agent_5_finalizer = Agent5Finalizer()