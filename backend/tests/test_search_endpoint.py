import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from bson import ObjectId
from main import app
from core.auth import create_access_token

client = TestClient(app)

def get_auth_headers(user_id: str = "507f1f77bcf86cd799439012"):
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
@patch("api.v1.search.get_or_create_profile")
@patch("api.v1.search.create_job_search")
@patch("api.v1.search.update_job_search_status")
@patch("tools.internshala.scrape_internshala")
@patch("tools.unstop.scrape_unstop")
@patch("agents.extraction_agent.process_scraped_results")
@patch("database.connection.get_database")
@patch("agents.ranking_agent.get_llm")
async def test_search_endpoint_success(
    mock_get_llm,
    mock_get_database,
    mock_process_results,
    mock_scrape_unstop,
    mock_scrape_internshala,
    mock_update_status,
    mock_create_search,
    mock_get_profile
):
    # Mock profile
    mock_get_profile.return_value = {
        "_id": ObjectId("507f1f77bcf86cd799439011"),
        "user_id": ObjectId("507f1f77bcf86cd799439012"),
        "skills": ["Python", "FastAPI"],
        "experience_years": 1.0,
        "education": "B.Tech",
        "preferred_roles": ["Backend Developer"],
        "preferred_locations": ["Remote"],
        "preferred_location": "Remote",
    }
    
    # Mock search generation
    mock_create_search.return_value = "507f1f77bcf86cd799439099"
    mock_update_status.return_value = True
    
    # Mock LLM for ranking explanations
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="Matches your skills in Python.")
    mock_get_llm.return_value = mock_llm

    # Mock Scrapers
    mock_scrape_internshala.return_value = [
        {"company": "InternCorp", "title": "Backend Intern", "location": "Remote", "url": "http://intern", "structured": False}
    ]
    mock_scrape_unstop.return_value = [
        {"company": "UnstopCorp", "title": "Developer", "location": "Remote", "url": "http://unstop", "structured": True}
    ]
    
    # Mock DB query in extract_node
    mock_db = MagicMock()
    mock_cursor = AsyncMock()
    mock_get_database.return_value = mock_db
    mock_db.jobs.find.return_value = mock_cursor
    
    # These are the documents returned when graph queries DB after extraction
    mock_cursor.to_list.return_value = [
        {
            "_id": ObjectId("507f1f77bcf86cd7994390a1"),
            "search_id": ObjectId("507f1f77bcf86cd799439099"),
            "company": "InternCorp",
            "role": "Backend Intern",
            "location": "Remote",
            "salary": "₹10,000 / month",
            "apply_link": "http://intern",
            "source": "internshala",
            "required_skills": ["Python"],
            "experience_required": "0-1 years",
            "job_type": "internship",
        },
        {
            "_id": ObjectId("507f1f77bcf86cd7994390a2"),
            "search_id": ObjectId("507f1f77bcf86cd799439099"),
            "company": "UnstopCorp",
            "role": "Developer",
            "location": "Remote",
            "salary": "Not disclosed",
            "apply_link": "http://unstop",
            "source": "unstop",
            "required_skills": ["Python", "FastAPI"],
            "experience_required": "0-2 years",
            "job_type": "full-time",
        }
    ]
    
    # Request Payload
    payload = {
        "role": "Backend Developer",
        "location": "Remote",
        "experience": "0-2 years",
        "skills": ["Python", "FastAPI"],
        "source": "all"
    }
    
    response = client.post("/api/v1/search", json=payload, headers=get_auth_headers())
    assert response.status_code == 200
    
    data = response.json()
    assert data["search_id"] == "507f1f77bcf86cd799439099"
    assert len(data["jobs"]) == 2
    
    # Assert sorted descending by relevance score
    scores = [j["relevance_score"] for j in data["jobs"]]
    assert scores == sorted(scores, reverse=True)
    
    # Verify BOTH sources accumulated (the reducer guard test)
    sources = {j["source"] for j in data["jobs"]}
    assert "internshala" in sources
    assert "unstop" in sources
    
    # Scrapers both called
    mock_scrape_internshala.assert_called_once()
    mock_scrape_unstop.assert_called_once()


@pytest.mark.asyncio
@patch("api.v1.search.get_or_create_profile")
@patch("api.v1.search.create_job_search")
@patch("api.v1.search.update_job_search_status")
@patch("tools.internshala.scrape_internshala")
@patch("tools.unstop.scrape_unstop")
@patch("agents.extraction_agent.process_scraped_results")
@patch("database.connection.get_database")
async def test_search_endpoint_single_source(
    mock_get_database,
    mock_process_results,
    mock_scrape_unstop,
    mock_scrape_internshala,
    mock_update_status,
    mock_create_search,
    mock_get_profile
):
    mock_get_profile.return_value = {
        "_id": ObjectId("507f1f77bcf86cd799439011"),
        "skills": ["Python"],
        "experience_years": 1.0,
        "preferred_location": "Remote",
        "preferred_roles": ["Developer"]
    }
    mock_create_search.return_value = "507f1f77bcf86cd799439099"
    
    mock_db = MagicMock()
    mock_cursor = AsyncMock()
    mock_get_database.return_value = mock_db
    mock_db.jobs.find.return_value = mock_cursor
    mock_cursor.to_list.return_value = []

    # Call with source="internshala"
    payload = {
        "role": "Developer",
        "location": "Remote",
        "experience": "0-2 years",
        "skills": ["Python"],
        "source": "internshala"
    }
    
    response = client.post("/api/v1/search", json=payload, headers=get_auth_headers())
    assert response.status_code == 200
    
    # Verify ONLY internshala scraper was called
    mock_scrape_internshala.assert_called_once()
    mock_scrape_unstop.assert_not_called()
