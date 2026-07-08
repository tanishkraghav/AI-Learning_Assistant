import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.storage import roadmaps_db
from app.models.schemas import ChatResponse
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

def test_chat_success(client, mock_groq):
    # Setup stored roadmap in memory DB
    roadmap_id = "test-roadmap-uuid-456"
    roadmaps_db[roadmap_id] = {
        "roadmap": {
            "roadmap_id": roadmap_id,
            "estimated_hours": 100,
            "skills": ["Python"],
            "tasks": []
        },
        "goal_title": "Python Developer",
        "experience": "Less than 1 year",
        "known_skills": ["Math"],
        "learning_style": "Visual",
        "weekly_hours": 10
    }

    # Mock ChromaDB retrieve_context
    mock_retrieved_context = [
        "Roadmap Summary for Goal: Python Developer\nRecommended Skills: Python",
        "Roadmap Task: Learn Syntax\nEstimated study hours: 10 hours\nDetails: Variables, control flow"
    ]
    
    mock_choice = MagicMock()
    mock_choice.message.content = """
    {
      "response": "Yes, you can learn basic Python syntax in 10 hours. It covers variables and control flow.",
      "follow_up_questions": [
        "Do you want to know about functions?",
        "Would you like resources for learning variables?"
      ]
    }
    """
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_groq.chat.completions.create.return_value = mock_completion

    with patch("app.routers.chat.retrieve_context", return_value=mock_retrieved_context) as mock_retrieve, \
         patch("app.services.cache.check_semantic_cache", return_value=None):
        payload = {
          "roadmap_id": roadmap_id,
          "message": "Can I learn syntax in 10 hours?"
        }
        response = client.post("/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert len(data["follow_up_questions"]) == 2
        mock_retrieve.assert_called_once_with(roadmap_id, "Can I learn syntax in 10 hours?", limit=4)

def test_chat_404_unknown_roadmap_id(client):
    payload = {
      "roadmap_id": "non-existent-roadmap",
      "message": "Hello"
    }
    response = client.post("/chat", json=payload)
    assert response.status_code == 404
    assert response.json()["detail"] == "Roadmap ID not found"

def test_chat_cache_hit_bypass_llm(client):
    roadmap_id = "test-roadmap-uuid-456"
    roadmaps_db[roadmap_id] = {
        "roadmap": {
            "roadmap_id": roadmap_id,
            "estimated_hours": 100,
            "skills": ["Python"],
            "tasks": []
        },
        "goal_title": "Python Developer",
        "experience": "Less than 1 year",
        "known_skills": ["Math"],
        "learning_style": "Visual",
        "weekly_hours": 10
    }

    mock_cached_response = ChatResponse(
        response="This is a cached response.",
        follow_up_questions=["Q1?", "Q2?"]
    )

    with patch("app.services.cache.check_semantic_cache", return_value=mock_cached_response) as mock_check, \
         patch("app.routers.chat.retrieve_context") as mock_retrieve, \
         patch("app.routers.chat.generate_json_response") as mock_gen:
        
        payload = {
          "roadmap_id": roadmap_id,
          "message": "Can I learn syntax in 10 hours?"
        }
        response = client.post("/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "This is a cached response."
        assert data["follow_up_questions"] == ["Q1?", "Q2?"]
        
        mock_check.assert_called_once_with(roadmap_id, "Can I learn syntax in 10 hours?")
        mock_retrieve.assert_not_called()
        mock_gen.assert_not_called()

def test_cache_service_thresholds():
    from app.services.cache import check_semantic_cache
    
    roadmap_id = "test-roadmap-uuid-456"
    
    # 1. Test collection not found (returns None)
    with patch("app.services.cache.chroma_client.get_collection", side_effect=Exception("not found")):
        res = check_semantic_cache(roadmap_id, "test question")
        assert res is None

    # 2. Test cache hit (distance = 0.05, which is similarity = 0.95 >= 0.92)
    mock_collection = MagicMock()
    mock_collection.count.return_value = 1
    mock_collection.query.return_value = {
        "distances": [[0.05]],
        "metadatas": [[{"answer": "cached answer", "follow_up_questions": '["Q1?", "Q2?"]'}]],
        "documents": [["cached question"]]
    }
    with patch("app.services.cache.chroma_client.get_collection", return_value=mock_collection):
        res = check_semantic_cache(roadmap_id, "test question")
        assert res is not None
        assert res.response == "cached answer"
        assert res.follow_up_questions == ["Q1?", "Q2?"]

    # 3. Test cache miss due to low similarity (distance = 0.15, similarity = 0.85 < 0.92)
    mock_collection.query.return_value = {
        "distances": [[0.15]],
        "metadatas": [[{"answer": "cached answer", "follow_up_questions": '["Q1?", "Q2?"]'}]],
        "documents": [["cached question"]]
    }
    with patch("app.services.cache.chroma_client.get_collection", return_value=mock_collection):
        res = check_semantic_cache(roadmap_id, "test question")
        assert res is None

