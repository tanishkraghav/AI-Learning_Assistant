import logging
import chromadb
from chromadb.utils import embedding_functions
from app.core.config import settings

logger = logging.getLogger("app.services.rag")

# Initialize persistent ChromaDB client
chroma_client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)

# Setup local SentenceTransformer embedding function
try:
    embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    logger.info("SentenceTransformerEmbeddingFunction initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize embedding function: {str(e)}")
    raise e

def clean_collection_name(roadmap_id: str) -> str:
    """
    Ensure collection name is safe (3-63 chars, no spaces, starts/ends alphanumeric,
    only contains alphanumeric, hyphens, underscores).
    UUID strings fit this perfectly, but replacing hyphens makes it ultra-safe.
    """
    clean_id = roadmap_id.replace("-", "_")
    return f"roadmap_{clean_id}"

def chunk_roadmap(roadmap_data: dict, goal_title: str) -> list[str]:
    """
    Chunking: Break the roadmap into chunks along natural task boundaries:
    - 1 chunk summarizing overall goal, skills, and total estimated hours.
    - 1 chunk per task containing the title, estimated hours, and its subtasks.
    """
    chunks = []
    
    # 1. Summary chunk
    skills = roadmap_data.get("skills", [])
    skills_str = ", ".join(skills) if skills else "None specified"
    total_hours = roadmap_data.get("estimated_hours", 0)
    summary_chunk = (
        f"Roadmap Summary for Goal: {goal_title}\n"
        f"Recommended Skills to learn: {skills_str}\n"
        f"Total Estimated Study Time: {total_hours} hours"
    )
    chunks.append(summary_chunk)
    
    # 2. Task chunks
    tasks = roadmap_data.get("tasks", [])
    for task in tasks:
        task_title = task.get("title", "")
        task_hours = task.get("estimated_hours", 0)
        subtasks = task.get("subtasks", [])
        subtasks_str = "; ".join([sub.get("title", "") for sub in subtasks]) if subtasks else "None"
        
        task_chunk = (
            f"Roadmap Task: {task_title}\n"
            f"Estimated study hours for this task: {task_hours} hours\n"
            f"Details and Subtasks: {subtasks_str}"
        )
        chunks.append(task_chunk)
        
    logger.info(f"Chunked roadmap into {len(chunks)} chunks.")
    return chunks

def store_roadmap_chunks(roadmap_id: str, chunks: list[str]):
    """
    Stores chunks + embeddings in a ChromaDB collection scoped per roadmap_id.
    """
    collection_name = clean_collection_name(roadmap_id)
    logger.info(f"Storing {len(chunks)} chunks in ChromaDB collection: '{collection_name}'")
    
    collection = chroma_client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_function
    )
    
    # Generate unique IDs for the chunks
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    
    # Add documents to collection
    collection.add(
        documents=chunks,
        ids=ids
    )
    logger.info(f"Successfully stored chunks in collection '{collection_name}'.")

def retrieve_context(roadmap_id: str, query: str, limit: int = 3) -> list[str]:
    """
    Retrieves the top `limit` most semantically similar chunks from the roadmap's collection.
    """
    collection_name = clean_collection_name(roadmap_id)
    logger.info(f"Retrieving context for query from collection '{collection_name}'")
    
    try:
        # Fetch the collection. If it doesn't exist, this will throw an error.
        collection = chroma_client.get_collection(
            name=collection_name,
            embedding_function=embedding_function
        )
    except Exception as e:
        logger.warning(f"Could not retrieve ChromaDB collection '{collection_name}': {str(e)}")
        return []
    
    # Query collection
    results = collection.query(
        query_texts=[query],
        n_results=min(limit, collection.count())
    )
    
    documents = results.get("documents", [])
    if documents and len(documents) > 0:
        retrieved_docs = documents[0]
        logger.info(f"Retrieved {len(retrieved_docs)} chunks from ChromaDB.")
        return retrieved_docs
        
    logger.info("No chunks retrieved.")
    return []
