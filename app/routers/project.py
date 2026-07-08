import logging
from fastapi import APIRouter, HTTPException
from app.models.schemas import ProjectRequest, ProjectResponse
from app.services.llm import generate_json_response
from app.services.storage import roadmaps_db

logger = logging.getLogger("app.routers.project")

router = APIRouter(prefix="/project", tags=["project"])

PROJECT_SYSTEM_PROMPT = """
You are an expert AI Project recommender. Your task is to recommend a highly relevant project for a student based on their career goal and the skills they want to practice.

The output MUST match this JSON schema exactly:
{
  "title": "Project title",
  "difficulty": "Beginner/Intermediate/Advanced",
  "estimated_hours": 20,
  "tech_stack": ["Skill1", "Skill2"],
  "features": ["Feature 1", "Feature 2"],
  "why_this_project": "Brief description of why this project helps practice the skills."
}

Rules:
1. "difficulty" must be one of "Beginner", "Intermediate", "Advanced".
2. "estimated_hours" must be a positive integer representing the estimated time to build the project.
3. Provide ONLY the JSON. No explanations, no markdown formatting blocks, no text before or after the JSON.
"""

@router.post("", response_model=ProjectResponse)
def get_project_recommendation(req: ProjectRequest):
    logger.info("Received project recommendation request.")
    
    goal_title = None
    skills = []
    
    # 1. Resolve parameters either from roadmap_id or direct request fields
    if req.roadmap_id:
        logger.info(f"Looking up roadmap_id: {req.roadmap_id} in memory storage.")
        if req.roadmap_id not in roadmaps_db:
            logger.warning(f"Roadmap ID '{req.roadmap_id}' not found.")
            raise HTTPException(status_code=404, detail="Roadmap ID not found")
        
        stored_data = roadmaps_db[req.roadmap_id]
        goal_title = stored_data.get("goal_title")
        # Use recommended skills from the generated roadmap
        skills = stored_data.get("roadmap", {}).get("skills", [])
        logger.info(f"Resolved from stored roadmap - goal: '{goal_title}', skills count: {len(skills)}")
    else:
        # Fallback validation
        if not req.goal_title or not req.skills:
            logger.warning("Invalid request: missing roadmap_id, or goal_title/skills combination.")
            raise HTTPException(
                status_code=400,
                detail="Missing parameters: you must provide either 'roadmap_id' OR both 'goal_title' and 'skills'."
            )
        goal_title = req.goal_title
        skills = req.skills
        logger.info(f"Resolved from raw parameters - goal: '{goal_title}', skills count: {len(skills)}")

    # 2. Build the LLM prompt
    user_prompt = f"""
Recommend a practice project for the following context:
- Career/Learning Goal: {goal_title}
- Skills to practice: {", ".join(skills)}

Generate the response in strict JSON format matching the schema.
"""

    # 3. Call Groq with JSON Mode & Retry validation
    project_response = generate_json_response(
        system_prompt=PROJECT_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_schema=ProjectResponse
    )
    
    logger.info(f"Successfully generated project recommendation: '{project_response.title}'")
    return project_response
