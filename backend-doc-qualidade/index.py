import logging
from pathlib import Path
from langchain_community.document_loaders import DirectoryLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. Defina os caminhos
# Crie esta pasta e coloque seus .docx de exemplo nela
DOCS_PATH = Path("documentos_exemplo")
FAISS_INDEX_PATH = Path("app/core/faiss_index") # Onde o índice será salvo

def create_vector_store():
    """
    Lê todos os documentos .docx, divide-os, 
    cria embeddings e salva em um índice FAISS.
    """
    if not DOCS_PATH.exists():
        logger.error(f"O diretório de documentos não existe: {DOCS_PATH}")
        DOCS_PATH.mkdir(parents=True, exist_ok=True)
        logger.info(f"Criei o diretório. Adicione seus .docx de exemplo lá e rode novamente.")
        return

    logger.info(f"Iniciando a indexação de documentos em {DOCS_PATH}...")

    # 1. Carregar os Documentos
    # (Usando um glob para pegar .docx e .doc)
    loader = DirectoryLoader(
        str(DOCS_PATH),
        glob="**/*.docx",
        loader_cls=Docx2txtLoader,
        show_progress=True,
        use_multithreading=True
    )
    docs = loader.load()
    if not docs:
        logger.warning("Nenhum documento .docx encontrado.")
        return

    logger.info(f"{len(docs)} documentos carregados.")

    # 2. Dividir (Chunking)
    # Divide os documentos em pedaços menores para o RAG
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    splits = text_splitter.split_documents(docs)
    logger.info(f"Documentos divididos em {len(splits)} pedaços (chunks).")

    # 3. Criar Embeddings
    # (O modelo bge-m3 é pesado, mas muito bom. 
    #  Use 'BAAI/bge-base-en-v1.5' se for mais rápido)
    logger.info("Carregando modelo de embedding (bge-m3)... Isso pode demorar.")
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-m3",
        model_kwargs={'device': 'cpu'}, # Use 'cuda' se tiver GPU
        encode_kwargs={'normalize_embeddings': True}
    )

    # 4. Criar e Salvar o Índice FAISS
    logger.info("Criando o banco de dados vetorial FAISS...")
    vector_store = FAISS.from_documents(splits, embeddings)
    
    # Salva o índice localmente
    vector_store.save_local(str(FAISS_INDEX_PATH))
    logger.info(f"Índice FAISS salvo com sucesso em {FAISS_INDEX_PATH}!")

if __name__ == "__main__":
    create_vector_store()