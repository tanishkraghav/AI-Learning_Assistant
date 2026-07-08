import logging
import json
import uuid
from app.services.rag import chroma_client, embedding_function, clean_collection_name
from app.models.schemas import ChatResponse

logger = logging.getLogger("app.services.cache")

def get_cache_collection_name(roadmap_id: str) -> str:
    clean_id = roadmap_id.replace("-", "_")
    return f"cache_{clean_id}"

def check_semantic_cache(roadmap_id: str, question: str, similarity_threshold: float = 0.92) -> ChatResponse | None:
    """
    Checks the semantic cache for a similar question.
    Returns the ChatResponse if found and similarity is above the threshold, otherwise None.
    """
    collection_name = get_cache_collection_name(roadmap_id)
    
    try:
        # Check if collection exists
        collection = chroma_client.get_collection(
            name=collection_name,
            embedding_function=embedding_function
        )
    except Exception:
        # Collection doesn't exist yet, meaning cache is empty
        logger.info(f"Cache collection '{collection_name}' does not exist yet. Cache miss.")
        return None
        
    if collection.count() == 0:
        logger.info(f"Cache collection '{collection_name}' is empty. Cache miss.")
        return None

    # Query the closest match
    results = collection.query(
        query_texts=[question],
        n_results=1
    )
    
    distances = results.get("distances", [])
    metadatas = results.get("metadatas", [])
    documents = results.get("documents", [])
    
    if distances and len(distances) > 0 and len(distances[0]) > 0:
        distance = distances[0][0]
        # In Cosine space, distance = 1 - cosine_similarity
        # Hence similarity = 1 - distance
        similarity = 1.0 - distance
        
        logger.info(f"Nearest cached question: '{documents[0][0]}' with similarity: {similarity:.4f} (distance: {distance:.4f})")
        
        if similarity >= similarity_threshold:
            metadata = metadatas[0][0]
            answer = metadata.get("answer")
            follow_up_raw = metadata.get("follow_up_questions", "[]")
            
            try:
                follow_up_questions = json.loads(follow_up_raw)
            except Exception:
                follow_up_questions = []
                
            logger.info(">>> SEMANTIC CACHE HIT! Returning cached response instantly. <<<")
            return ChatResponse(
                response=answer,
                follow_up_questions=follow_up_questions
            )
            
    logger.info(">>> SEMANTIC CACHE MISS. Querying LLM. <<<")
    return None

def store_in_semantic_cache(roadmap_id: str, question: str, response: ChatResponse):
    """
    Stores a question-answer pair in the semantic cache.
    """
    collection_name = get_cache_collection_name(roadmap_id)
    
    # Cosine similarity is set by metadata={"hnsw:space": "cosine"}
    collection = chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
        embedding_function=embedding_function
    )
    
    doc_id = str(uuid.uuid4())
    metadata = {
        "answer": response.response,
        "follow_up_questions": json.dumps(response.follow_up_questions)
    }
    
    collection.add(
        documents=[question],
        metadatas=[metadata],
        ids=[doc_id]
    )
    logger.info(f"Stored question in semantic cache with ID {doc_id}.")
