import pytest
from fastapi.testclient import TestClient
from app.main import app
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

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_roadmap_success(client, mock_groq):
    mock_choice = MagicMock()
    mock_choice.message.content = """
    {
      "estimated_hours": 120,
      "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
      "tasks": [
        {
          "title": "Learn FastAPI",
          "estimated_hours": 12,
          "subtasks": [{ "title": "Routing" }]
        }
      ]
    }
    """
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_groq.chat.completions.create.return_value = mock_completion

    payload = {
      "goal_title": "Backend Developer",
      "experience": "Less than 1 year",
      "known_skills": ["Python", "SQL"],
      "learning_style": "Project Based",
      "weekly_hours": 15
    }
    response = client.post("/roadmap", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "roadmap_id" in data
    assert data["estimated_hours"] == 120
    assert "FastAPI" in data["skills"]
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["title"] == "Learn FastAPI"

def test_roadmap_validation_empty_skills(client):
    payload = {
      "goal_title": "Backend Developer",
      "experience": "Less than 1 year",
      "known_skills": [],
      "learning_style": "Project Based",
      "weekly_hours": 15
    }
    response = client.post("/roadmap", json=payload)
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("known_skills" in str(err.get("loc")) for err in errors)

def test_roadmap_validation_negative_hours(client):
    payload = {
      "goal_title": "Backend Developer",
      "experience": "Less than 1 year",
      "known_skills": ["Python"],
      "learning_style": "Project Based",
      "weekly_hours": -5
    }
    response = client.post("/roadmap", json=payload)
    assert response.status_code == 422

def test_global_exception_handler(client):
    with patch("app.routers.roadmap.generate_json_response", side_effect=ValueError("Simulated crash")):
        payload = {
          "goal_title": "Backend Developer",
          "experience": "Less than 1 year",
          "known_skills": ["Python"],
          "learning_style": "Project Based",
          "weekly_hours": 15
        }
        response = client.post("/roadmap", json=payload)
        assert response.status_code == 500
        assert "unexpected internal server error" in response.json()["detail"]

