import logging
from fastapi import APIRouter, HTTPException, Response
from app.models.schemas import ChatRequest, ChatResponse
from app.services.llm import generate_json_response
from app.services.storage import roadmaps_db
from app.services.rag import retrieve_context

logger = logging.getLogger("app.routers.chat")

router = APIRouter(prefix="/chat", tags=["chat"])

CHAT_SYSTEM_PROMPT = """
You are an expert AI Learning Assistant. Your task is to answer a user's question about their personalized learning roadmap using ONLY the provided context retrieved from their roadmap collection.

Context chunks:
{context}

Rules:
1. Base your answer strictly on the provided context. If the answer cannot be found or inferred from the context, politely state that you can only answer questions related to their roadmap.
2. Propose exactly 2 relevant follow-up questions based on the question, response, and roadmap context.
3. The response MUST be in strict JSON matching this schema:
{{
  "response": "Your answer text here...",
  "follow_up_questions": [
    "Follow-up question 1?",
    "Follow-up question 2?"
  ]
}}
4. Provide ONLY the JSON. No explanations, no markdown formatting blocks, no text before or after the JSON.
"""

@router.post("", response_model=ChatResponse)
def chat_with_roadmap(req: ChatRequest, response: Response):
    logger.info(f"Received chat request for roadmap_id: {req.roadmap_id}")
    
    # 1. Verify roadmap_id exists
    if req.roadmap_id not in roadmaps_db:
        logger.warning(f"Roadmap ID '{req.roadmap_id}' not found.")
        raise HTTPException(status_code=404, detail="Roadmap ID not found")
        
    # 2. Check semantic cache first
    try:
        from app.services.cache import check_semantic_cache, store_in_semantic_cache
        cached_response = check_semantic_cache(req.roadmap_id, req.message)
        if cached_response:
            response.headers["X-Cache-Status"] = "HIT"
            return cached_response
    except Exception as e:
        logger.error(f"Error checking semantic cache: {str(e)}")
        
    # 3. Retrieve top 3-4 chunks from ChromaDB
    retrieved_chunks = retrieve_context(req.roadmap_id, req.message, limit=4)
    context_str = "\n---\n".join(retrieved_chunks) if retrieved_chunks else "No specific roadmap context found."
    
    logger.info(f"Retrieved context length: {len(context_str)} characters.")
    
    # 4. Build system prompt with retrieved context
    system_prompt = CHAT_SYSTEM_PROMPT.format(context=context_str)
    
    user_prompt = f"User Question: {req.message}"
    
    # 5. Call Groq with JSON Mode & Retry validation
    chat_response = generate_json_response(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_schema=ChatResponse
    )
    
    # 6. Store in semantic cache for future hits
    try:
        store_in_semantic_cache(req.roadmap_id, req.message, chat_response)
    except Exception as e:
        logger.error(f"Error storing response in semantic cache: {str(e)}")
        
    response.headers["X-Cache-Status"] = "MISS"
    logger.info("Successfully generated and returned chat response.")
    return chat_response


@router.post("/ask")
def simple_chat(request: dict):
    """Simple chat endpoint for general questions without roadmap context"""
    logger.info("Received simple chat request")
    
    query = request.get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
    
    try:
        system_prompt = """You are a friendly and helpful AI Learning Assistant. 
        Provide clear, concise answers to help users with their learning journey.
        Keep responses to 2-3 sentences maximum."""
        
        user_prompt = query
        
        # Call Groq LLM with an available model
        from groq import Groq
        client = Groq()
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        answer = completion.choices[0].message.content
        logger.info(f"Generated response: {answer[:100]}...")
        
        return {
            "answer": answer,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error in simple chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")
