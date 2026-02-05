# ==============================================================================
# ARQUIVO: app/services/vectorizer.py
#
# OBJETIVO:
#   Converter textos de negócios em vetores matemáticos (Embeddings) e armazená-los.
#   Este é o "cérebro" da indexação semântica, permitindo buscas por significado.
#
# PARTE DO SISTEMA:
#   Backend / Integração IA (Embeddings)
#
# RESPONSABILIDADES:
#   - Gerar IDs determinísticos para os chamados
#   - Chamar a API da OpenAI para calcular embeddings (text-embedding-3-small/large)
#   - Montar o payload (metadados) para o banco vetorial
#   - Salvar os dados no Qdrant de forma eficiente (Batch)
#
# COMUNICAÇÃO:
#   Chamado por: run_pipeline.py
#   Serviços Externos: OpenAI API (Embeddings), Qdrant (Vector DB)
# ==============================================================================

import uuid
from openai import OpenAI
from qdrant_client.http import models
from app.core.config import settings
from app.core.vector_store import vector_db
import logging

logger = logging.getLogger(__name__)

# Cliente OpenAI
client = OpenAI(api_key=settings.OPENAI_API_KEY)

def generate_uuid_from_string(val: str, system_name: str = "") -> str:
    """
    Gera um UUID determinístico baseado no ID do chamado e Opcionalmente no Sistema.
    
    CRÍTICO:
    Para evitar colisão de IDs entre sistemas diferentes (ex: ID 100 no Protheus e ID 100 no Logix),
    devemos usar o prefixo do sistema.
    string_base = "PROTHEUS_100" -> UUID X
    string_base = "LOGIX_100"    -> UUID Y
    """
    if system_name:
        val = f"{system_name}_{val}"
        
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, str(val)))

def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Chama a API da OpenAI para gerar vetores.
    Aceita lista para processar em batch (mais rápido).
    
    CUSTO:
    Geralmente usamos 'text-embedding-3-small' por ser muito barato e eficiente.
    """
    try:
        # Remove quebras de linha que podem atrapalhar o modelo
        texts = [t.replace("\n", " ") for t in texts]
        
        response = client.embeddings.create(
            input=texts,
            model=settings.OPENAI_EMBEDDING_MODEL,
            dimensions=3072
        )
        # Extrai apenas os vetores da resposta
        return [data.embedding for data in response.data]
    except Exception as e:
        logger.error(f"Erro na OpenAI: {e}")
        raise e

def process_and_vectorize(records: list[dict]):
    """
    Orquestra o processo de ETL semântico:
    Raw Data -> Texto Único -> Vetor -> Qdrant
    
    PARÂMETROS:
        - records: Lista de dicionários vindos do MySQL.
    
    FLUXO:
    1. Garante que a coleção Qdrant existe.
    2. Prepara os IDs e Payloads (Metadados que ficam salvos junto com o vetor).
    3. Envia os textos para OpenAI em lotes (Batches) para performance.
    4. Salva tudo no Qdrant.
    """
    logger.info(f"Iniciando vetorização de {len(records)} registros...")
    
    # 1. Garantir que a coleção existe (Idempotência)
    vector_db.ensure_collection_exists()
    
    points_to_upload = []
    texts_to_vectorize = []
    indexes_to_vectorize = []

    # 2. Preparar Lotes
    for i, record in enumerate(records):
        # Gera ID único para o Qdrant (Composito: Sistema + ID)
        point_id = generate_uuid_from_string(record['id_chamado'], record.get('sistema', ''))
        
        # Prepara metadados (Payload) - Removemos o texto longo para não duplicar peso no banco
        # Mantemos apenas campos filtro: sistema, data, serviço, etc.
        payload = record.copy()
        
        # Adiciona na lista para processar
        texts_to_vectorize.append(record['texto_vetor'])
        indexes_to_vectorize.append((i, point_id, payload))

    # 3. Gerar Embeddings (Chamada à OpenAI)
    if texts_to_vectorize:
        logger.info(f"Gerando embeddings para {len(texts_to_vectorize)} novos itens via OpenAI...")
        
        # Processar em lotes de 100 para não estourar limite da API (Rate Limit) e nem a RAM
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
            
            # PointStruct é o formato que o Qdrant espera
            point = models.PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            )
            points_to_upload.append(point)

    # 5. Salvar no Qdrant (Bulk Upload parcelado)
    if points_to_upload:
        # Divide em chunks de 100 para não estourar payload do Qdrant (limite 32MB)
        chunk_size = 100
        total_points = len(points_to_upload)
        
        for i in range(0, total_points, chunk_size):
            chunk = points_to_upload[i : i + chunk_size]
            vector_db.upload_vectors(chunk)
            logger.info(f"Upload parcial: {min(i + chunk_size, total_points)}/{total_points} vetores salvos.")
            
        logger.info("Vetorização e upload concluídos com sucesso.")
    
    return True