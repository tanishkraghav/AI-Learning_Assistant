from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

class SubTask(BaseModel):
    title: str = Field(..., min_length=1, description="Title of the subtask")

class Task(BaseModel):
    title: str = Field(..., min_length=1, description="Title of the task")
    estimated_hours: int = Field(..., gt=0, description="Estimated hours to complete")
    subtasks: List[SubTask] = Field(default_factory=list, description="Subtasks list")

class RoadmapRequest(BaseModel):
    goal_title: str = Field(..., min_length=1, description="Goal to achieve")
    experience: str = Field(..., min_length=1, description="Experience level")
    known_skills: List[str] = Field(..., description="Known skills")
    learning_style: str = Field(..., min_length=1, description="Preferred learning style")
    weekly_hours: int = Field(..., gt=0, description="Weekly hours available")

    @field_validator("known_skills")
    @classmethod
    def validate_known_skills(cls, v: List[str]) -> List[str]:
        if not v or len(v) == 0:
            raise ValueError("known_skills list cannot be empty. Please provide at least one known skill (or 'None' if starting fresh) to help customize your roadmap.")
        cleaned = [s.strip() for s in v if s.strip()]
        if not cleaned:
            raise ValueError("known_skills list cannot contain only empty strings.")
        return cleaned

class RoadmapResponse(BaseModel):
    roadmap_id: str = Field(..., description="Unique UUID for this roadmap")
    estimated_hours: int = Field(..., gt=0, description="Total estimated hours")
    skills: List[str] = Field(..., description="Recommended skills list")
    tasks: List[Task] = Field(..., description="Roadmap tasks")

# Stage 3 Models
class ProjectRequest(BaseModel):
    roadmap_id: Optional[str] = Field(None, description="UUID of stored roadmap")
    goal_title: Optional[str] = Field(None, description="Goal title (fallback if roadmap_id not provided)")
    skills: Optional[List[str]] = Field(None, description="Skills list (fallback if roadmap_id not provided)")

    @field_validator("skills")
    @classmethod
    def validate_skills(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            cleaned = [s.strip() for s in v if s.strip()]
            return cleaned
        return v

class ProjectResponse(BaseModel):
    title: str = Field(..., min_length=1, description="Project title")
    difficulty: str = Field(..., min_length=1, description="Project difficulty level")
    estimated_hours: int = Field(..., gt=0, description="Estimated hours to complete")
    tech_stack: List[str] = Field(..., description="Required tech stack")
    features: List[str] = Field(..., description="List of project features to build")
    why_this_project: str = Field(..., min_length=1, description="Explanation of why this project is recommended")

# Stage 4 Models
class ChatRequest(BaseModel):
    roadmap_id: str = Field(..., description="UUID of stored roadmap")
    message: str = Field(..., min_length=1, description="Incoming chat message")

class ChatResponse(BaseModel):
    response: str = Field(..., description="LLM response back to the user")
    follow_up_questions: List[str] = Field(..., description="Two relevant follow-up questions")
