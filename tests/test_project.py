import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.storage import roadmaps_db
from unittest.mock import MagicMock, patch

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_groq():
    with patch("app.services.llm.Groq") as mock_groq_class:
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        yield mock_client

def test_project_raw_input_success(client, mock_groq):
    mock_choice = MagicMock()
    mock_choice.message.content = """
    {
      "title": "Task Management API",
      "difficulty": "Intermediate",
      "estimated_hours": 20,
      "tech_stack": ["FastAPI", "PostgreSQL", "Docker"],
      "features": ["JWT Authentication", "CRUD APIs", "Pagination"],
      "why_this_project": "Helps practice REST API development."
    }
    """
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_groq.chat.completions.create.return_value = mock_completion

    payload = {
      "goal_title": "Backend Developer",
      "skills": ["FastAPI", "PostgreSQL", "Docker"]
    }
    response = client.post("/project", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Task Management API"
    assert data["difficulty"] == "Intermediate"
    assert "FastAPI" in data["tech_stack"]

def test_project_roadmap_id_success(client, mock_groq):
    # Setup stored roadmap in memory DB
    roadmap_id = "test-roadmap-uuid-123"
    roadmaps_db[roadmap_id] = {
        "roadmap": {
            "roadmap_id": roadmap_id,
            "estimated_hours": 100,
            "skills": ["FastAPI", "PostgreSQL", "Docker"],
            "tasks": []
        },
        "goal_title": "Backend Developer",
        "experience": "Less than 1 year",
        "known_skills": ["Python"],
        "learning_style": "Project Based",
        "weekly_hours": 15
    }

    mock_choice = MagicMock()
    mock_choice.message.content = """
    {
      "title": "Task Management API",
      "difficulty": "Intermediate",
      "estimated_hours": 20,
      "tech_stack": ["FastAPI", "PostgreSQL", "Docker"],
      "features": ["JWT Authentication", "CRUD APIs", "Pagination"],
      "why_this_project": "Helps practice REST API development."
    }
    """
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_groq.chat.completions.create.return_value = mock_completion

    payload = {
      "roadmap_id": roadmap_id
    }
    response = client.post("/project", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Task Management API"
    assert data["difficulty"] == "Intermediate"

def test_project_404_unknown_roadmap_id(client):
    payload = {
      "roadmap_id": "non-existent-uuid"
    }
    response = client.post("/project", json=payload)
    assert response.status_code == 404
    assert response.json()["detail"] == "Roadmap ID not found"

def test_project_400_missing_parameters(client):
    # No roadmap_id, and missing goal_title or skills
    payload = {
      "goal_title": "Backend Developer"
    }
    response = client.post("/project", json=payload)
    assert response.status_code == 400
    assert "Missing parameters" in response.json()["detail"]
