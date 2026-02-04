# ==============================================================================
# ARQUIVO: app/core/vector_store.py
#
# OBJETIVO:
#   Abstração para comunicação com o Banco de Dados Vetorial (Qdrant).
#   Centraliza todas as operações de busca semântica, inserção e configuração.
#
# RESPONSABILIDADES:
#   - Conectar ao cluster Qdrant (local ou nuvem)
#   - Garantir que a coleção (tabela) existe com a configuração correta (Distância do Cosseno)
#   - Fazer upload de vetores em massa (Batch Upsert)
#   - Recuperar vetores via Scroll ou Busca por Similaridade
# ==============================================================================

from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.core.config import settings
import logging

# Configuração de Logs
logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self):
        """
        Inicializa o cliente do Qdrant.
        """
        self.client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            api_key=None, # Ajuste se usar Qdrant Cloud
        )
        self.collection_name = settings.QDRANT_COLLECTION_PREFIX
        
        # Dimensão do modelo 'text-embedding-3-small' da OpenAI
        # Se mudar o modelo na OpenAI, OBRIGATORIAMENTE deve mudar aqui.
        # Ex: Ada-002 = 1536 dim
        # Ex: embedding-3-large = 3072 dim (padrão)
        self.vector_size = 3072 

    def ensure_collection_exists(self):
        """
        Verifica se a coleção existe. Se não, cria com a configuração correta de distância.
        
        IMPORTANTE: 
        A OpenAI usa "Cosine Distance" como métrica de similaridade.
        Se criarmos a coleção com Euclidean ou DotProduct, a busca semântica ficará imprecisa.
        """
        collections = self.client.get_collections()
        exists = any(c.name == self.collection_name for c in collections.collections)

        if not exists:
            logger.info(f"Criando coleção '{self.collection_name}' no Qdrant...")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.vector_size,
                    distance=models.Distance.COSINE # Cosseno é o padrão para NLP/OpenAI
                )
            )
            logger.info("Coleção criada com sucesso.")
        else:
            logger.info(f"Coleção '{self.collection_name}' já existe.")

    def upload_vectors(self, points: list[models.PointStruct]):
        """
        Salva um lote (batch) de vetores + payload no banco.
        
        A operação é 'upsert': Se o ID já existir, atualiza. Se não, cria.
        'wait=True' garante consistência imediata (bom para scripts, ruim para APIs de alta vazão).
        """
        if not points:
            return
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
            wait=True 
        )
        logger.info(f"Salvos {len(points)} vetores no Qdrant.")

    def search_similar(self, vector: list[float], limit: int = 5):
        """
        Busca vetores parecidos (Usado para deduplicar ou RAG futuro).
        """
        return self.client.search(
            collection_name=self.collection_name,
            query_vector=vector,
            limit=limit
        )

    def get_all_vectors(self):
        """
        Recupera TODOS os vetores para enviar para o algortimo de Clustering (HDBSCAN).
        
        ESTRATÉGIA DE SCROLL:
        Bancos vetoriais não são feitos para retornar "tudo", então usamos a API de Scroll (paginação)
        para puxar os dados em chunks (ex: 1000 por vez) até esgotar.
        """
        all_points = []
        offset = None
        
        while True:
            # Pega de 1000 em 1000
            records, offset = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=None,
                limit=1000,
                with_payload=True,
                with_vectors=True,
                offset=offset
            )
            all_points.extend(records)
            
            if offset is None: # Acabou a paginação
                break
                
        return all_points

# Instância Singleton
# Permite importar 'vector_db' diretamente em qualquer arquivo sem re-instanciar a classe
vector_db = VectorStore()