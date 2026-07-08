import logging
from typing import Type, TypeVar
from pydantic import BaseModel, ValidationError
from groq import Groq
from app.core.config import settings
from fastapi import HTTPException

logger = logging.getLogger("app.services.llm")

T = TypeVar("T", bound=BaseModel)

def get_groq_client() -> Groq:
    if not settings.GROQ_API_KEY or "placeholder" in settings.GROQ_API_KEY.lower():
        # In a real setup or test environment, checking the API key is essential.
        # If it's missing or a placeholder, we log a warning but still attempt to create client
        # so tests or direct execution can fail naturally or use mocked clients.
        logger.warning("GROQ_API_KEY is not configured or is a placeholder.")
    return Groq(api_key=settings.GROQ_API_KEY)

def generate_json_response(
    system_prompt: str,
    user_prompt: str,
    response_schema: Type[T],
    max_retries: int = 2
) -> T:
    """
    Sends prompts to Groq API using JSON mode, parses results using response_schema.
    Retries up to max_retries if validation fails, appending the error details to LLM's context.
    """
    client = get_groq_client()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    attempts = 0
    while attempts <= max_retries:
        try:
            logger.info(f"Calling Groq API (Attempt {attempts + 1}/{max_retries + 1}) using model {settings.LLM_MODEL}")
            
            completion = client.chat.completions.create(
                messages=messages,
                model=settings.LLM_MODEL,
                response_format={"type": "json_object"},
                temperature=0.2
            )
            raw_response = completion.choices[0].message.content
            logger.info(f"Received raw response from Groq on attempt {attempts + 1}.")
            
            try:
                # Attempt to validate with the schema
                parsed = response_schema.model_validate_json(raw_response)
                logger.info("Successfully validated JSON response with schema.")
                return parsed
            except ValidationError as ve:
                logger.warning(f"Pydantic Validation failed on attempt {attempts + 1}: {str(ve)}")
                error_msg = f"Your last response was not valid according to the required schema: {str(ve)}. Return only JSON matching the schema, no markdown fences."
                messages.append({"role": "assistant", "content": raw_response})
                messages.append({"role": "user", "content": error_msg})
            except Exception as pe:
                logger.warning(f"JSON Parsing failed on attempt {attempts + 1}: {str(pe)}")
                error_msg = "Your last response was not valid JSON. Return only JSON, no markdown fences."
                messages.append({"role": "assistant", "content": raw_response})
                messages.append({"role": "user", "content": error_msg})
                
        except Exception as e:
            logger.error(f"Groq API call connection/request error on attempt {attempts + 1}: {str(e)}")
            if attempts == max_retries:
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to communicate with LLM provider. Details: {str(e)}"
                )
            
        attempts += 1
        
    raise HTTPException(
        status_code=502,
        detail=f"LLM failed to output a valid response matching the Pydantic schema after {max_retries + 1} attempts."
    )
