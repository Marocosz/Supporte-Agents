"""
MÓDULO: app/core/rag_pipeline.py - SINGLETON DO PIPELINE DE RAG (Recuperação de Documentos)

FUNÇÃO:
Define a classe `RAGPipeline`, que implementa o padrão Singleton. Sua principal
responsabilidade é inicializar e carregar na memória principal (RAM) os
componentes pesados necessários para a Recuperação de Documentos Aumentada
(RAG), garantindo que os Agentes de IA tenham acesso rápido e compartilhado
ao conhecimento externo (documentos .docx de exemplo).

ARQUITETURA:
- **Singleton:** A classe é instanciada apenas uma vez (`rag_pipeline = RAGPipeline()`).
  Isso evita a recarga desnecessária do Modelo de Embedding e do Índice FAISS
  para cada nova requisição ou agente.
- **Componentes:** Carrega o Modelo de Embedding (vetorizador) e o Banco de
  Vetores (FAISS), que foram previamente criados no disco.
- **Output:** Fornece um objeto `BaseRetriever` que é usado pelos Agentes de IA
  (via LLM) para buscar contextos relevantes antes de gerar uma resposta.

DEPENDÊNCIAS CHAVE:
- `langchain_huggingface.HuggingFaceEmbeddings`: Modelo `BAAI/bge-m3` para
  converter texto em vetores de alta dimensionalidade.
- `langchain_community.vectorstores.FAISS`: O índice de busca vetorial que
  contém os embeddings dos documentos de suporte.

IMPACTO NO DESEMPENHO:
Ao ser um Singleton, garante que o consumo de ~2.3 GB de RAM para o modelo
de embedding e o índice FAISS ocorra apenas no startup do servidor.
"""
import logging
from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.retrievers import BaseRetriever

logger = logging.getLogger(__name__)

class RAGPipeline:
    """
    Esta classe implementa o padrão Singleton para carregar o modelo de embedding
    e o índice vetorial FAISS apenas uma vez, otimizando o RAG.
    """
    
    def __init__(self):
        logger.info("Inicializando Pipeline RAG Singleton...")
        # Variável que armazenará o objeto Retriever pronto para uso
        self.retriever: BaseRetriever | None = None
        self._load_pipeline()

    def _load_pipeline(self):
        """
        Carrega o modelo de embedding e o índice FAISS do disco para a memória.
        """
        try:
            # 1. Carregar Modelo de Embedding (O Custo Alto - Executado UMA VEZ)
            logger.info("Carregando modelo de embedding (bge-m3) para o Singleton. Isso pode demorar...")
            embeddings = HuggingFaceEmbeddings(
                # Modelo de embedding SOTA (State-of-the-Art) para embeddings
                model_name="BAAI/bge-m3",
                # Define o dispositivo de processamento (CPU é o padrão seguro)
                model_kwargs={'device': 'cpu'}, 
                encode_kwargs={'normalize_embeddings': True}
            )
            logger.info("Modelo de embedding do Singleton carregado.")

            # 2. Carregar Índice FAISS (O Banco de Vetores - Executado UMA VEZ)
            index_path = str(Path("app/core/faiss_index"))
            if not Path(index_path).exists():
                logger.error(f"Singleton RAG: Índice FAISS não encontrado em {index_path}! Verifique se 'index.faiss' e 'index.pkl' existem.")
                return

            logger.info("Carregando índice FAISS do Singleton...")
            vector_store = FAISS.load_local(
                index_path, 
                embeddings,
                # Permissão necessária para deserializar objetos do índice
                allow_dangerous_deserialization=True
            )
            
            # 3. Criar e armazenar o Retriever partilhado
            # Define o retriever, que é a interface de busca. "k: 4" significa
            # que ele retornará os 4 trechos de texto mais relevantes para a query.
            self.retriever = vector_store.as_retriever(search_kwargs={"k": 4})
            logger.info("Pipeline RAG Singleton carregado. O Retriever está pronto.")

        except Exception as e:
            # Em caso de falha, registra um erro crítico, mas permite que o servidor inicie
            # (os agentes que dependem do RAG falharão, mas os mocks podem funcionar)
            logger.error(f"Erro Crítico ao inicializar o RAG Singleton: {e}", exc_info=True)

# --- O PONTO CHAVE: Instância Única (Singleton) ---
# Instancia a classe UMA VEZ no momento da inicialização do módulo.
# Todos os outros módulos que importarem 'rag_pipeline' terão acesso à mesma
# instância com os modelos já carregados.
rag_pipeline = RAGPipeline()