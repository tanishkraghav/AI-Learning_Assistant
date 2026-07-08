import logging
import uuid
from fastapi import APIRouter, HTTPException
from app.models.schemas import RoadmapRequest, RoadmapResponse, Task
from app.services.llm import generate_json_response
from app.services.storage import roadmaps_db
from pydantic import BaseModel, Field
from typing import List

logger = logging.getLogger("app.routers.roadmap")

router = APIRouter(prefix="/roadmap", tags=["roadmap"])

# Internal Pydantic schema for parsing LLM's response without roadmap_id
class RoadmapLLMOutput(BaseModel):
    estimated_hours: int = Field(..., gt=0)
    skills: List[str] = Field(...)
    tasks: List[Task] = Field(...)

ROADMAP_SYSTEM_PROMPT = """
You are an expert AI Learning Assistant. Your goal is to generate a highly personalized, structured learning roadmap in strict JSON format based on the user's career/learning goal, experience level, known skills, learning style, and available weekly hours.

The output MUST match this JSON schema exactly:
{
  "estimated_hours": 120,
  "skills": ["Skill1", "Skill2"],
  "tasks": [
    {
      "title": "Task title",
      "estimated_hours": 12,
      "subtasks": [
        { "title": "Subtask title" }
      ]
    }
  ]
}

Rules:
1. "estimated_hours" of the overall roadmap must be a positive integer representing the total time needed.
2. "skills" list must contain the main recommended skills to learn.
3. Each task must have a title, estimated_hours (positive integer), and a list of subtasks.
4. Keep tasks actionable, sequential, and appropriate for the user's experience and weekly hours.
5. Provide ONLY the JSON. No explanations, no markdown formatting blocks, no text before or after the JSON.
"""

@router.post("", response_model=RoadmapResponse)
def create_roadmap(req: RoadmapRequest):
    logger.info(f"Received roadmap generation request for goal: '{req.goal_title}'")
    
    user_prompt = f"""
Create a personalized learning roadmap for:
- Goal: {req.goal_title}
- Experience Level: {req.experience}
- Known Skills: {", ".join(req.known_skills)}
- Learning Style: {req.learning_style}
- Weekly Hours: {req.weekly_hours} hours/week

Generate the response in strict JSON format matching the schema.
"""
    
    # Call the LLM with retry mechanism
    llm_output = generate_json_response(
        system_prompt=ROADMAP_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_schema=RoadmapLLMOutput
    )
    
    # Generate UUID and package into RoadmapResponse
    roadmap_id = str(uuid.uuid4())
    roadmap_data = RoadmapResponse(
        roadmap_id=roadmap_id,
        estimated_hours=llm_output.estimated_hours,
        skills=llm_output.skills,
        tasks=llm_output.tasks
    )
    
    # Save to our in-memory database
    roadmaps_db[roadmap_id] = {
        "roadmap": roadmap_data.model_dump(),
        "goal_title": req.goal_title,
        "experience": req.experience,
        "known_skills": req.known_skills,
        "learning_style": req.learning_style,
        "weekly_hours": req.weekly_hours
    }
    logger.info(f"Successfully stored roadmap with ID: {roadmap_id} in memory.")
    
    # Chunk and store in ChromaDB for RAG
    try:
        from app.services.rag import chunk_roadmap, store_roadmap_chunks
        chunks = chunk_roadmap(roadmap_data.model_dump(), req.goal_title)
        store_roadmap_chunks(roadmap_id, chunks)
    except Exception as e:
        logger.error(f"Error storing roadmap chunks in ChromaDB: {str(e)}")
        # In this assignment, we want to know if this fails but not fail the endpoint if it is a transient error.
        # Actually, let's keep it as log error.
        pass

    return roadmap_data
