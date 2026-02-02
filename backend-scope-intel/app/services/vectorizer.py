import uuid
from openai import OpenAI
from qdrant_client.http import models
from app.core.config import settings
from app.core.vector_store import vector_db
import logging

logger = logging.getLogger(__name__)

# Cliente OpenAI
client = OpenAI(api_key=settings.OPENAI_API_KEY)

def generate_uuid_from_string(val: str) -> str:
    """Gera um UUID determinístico baseado no ID do chamado."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, str(val)))

def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Chama a API da OpenAI para gerar vetores.
    Aceita lista para processar em batch (mais rápido).
    """
    try:
        # Remove quebras de linha que podem atrapalhar o modelo
        texts = [t.replace("\n", " ") for t in texts]
        
        response = client.embeddings.create(
            input=texts,
            model=settings.OPENAI_EMBEDDING_MODEL
        )
        # Extrai apenas os vetores da resposta
        return [data.embedding for data in response.data]
    except Exception as e:
        logger.error(f"Erro na OpenAI: {e}")
        raise e

def process_and_vectorize(records: list[dict]):
    """
    Recebe a lista de chamados (do data_fetcher), gera os vetores 
    e salva no Qdrant com Payload.
    """
    logger.info(f"Iniciando vetorização de {len(records)} registros...")
    
    # 1. Garantir que a coleção existe
    vector_db.ensure_collection_exists()
    
    points_to_upload = []
    texts_to_vectorize = []
    indexes_to_vectorize = []

    # 2. Verificar quais já existem no Qdrant (Lógica de Cache)
    # Para simplificar este MVP Batch, vamos assumir que processamos tudo,
    # mas em produção usaríamos vector_db.client.retrieve() para pular existentes.
    
    for i, record in enumerate(records):
        # Gera ID único para o Qdrant
        point_id = generate_uuid_from_string(record['id_chamado'])
        
        # Prepara metadados (Payload) - Removemos o texto longo para não duplicar peso
        payload = record.copy()
        
        # Adiciona na lista para processar
        texts_to_vectorize.append(record['texto_vetor'])
        indexes_to_vectorize.append((i, point_id, payload))

    # 3. Gerar Embeddings (Chamada à OpenAI)
    if texts_to_vectorize:
        logger.info(f"Gerando embeddings para {len(texts_to_vectorize)} novos itens via OpenAI...")
        
        # Processar em lotes de 100 para não estourar limite da API
        batch_size = 100
        total_vectors = []
        
        for i in range(0, len(texts_to_vectorize), batch_size):
            batch_texts = texts_to_vectorize[i : i + batch_size]
            vectors = get_embeddings(batch_texts)
            total_vectors.extend(vectors)
            logger.info(f"Progresso: {len(total_vectors)}/{len(texts_to_vectorize)} vetores gerados.")

        # 4. Montar Objetos do Qdrant
        for idx, vector in enumerate(total_vectors):
            original_index, point_id, payload = indexes_to_vectorize[idx]
            
            point = models.PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            )
            points_to_upload.append(point)

    # 5. Salvar no Qdrant
    if points_to_upload:
        vector_db.upload_vectors(points_to_upload)
        logger.info("Vetorização e upload concluídos com sucesso.")
    
    return True