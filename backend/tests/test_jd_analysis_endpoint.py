import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from bson import ObjectId
from main import app
from agents.jd_analysis_agent import JDAnalysisModel
from core.auth import create_access_token

client = TestClient(app)

def get_auth_headers(user_id: str = "507f1f77bcf86cd799439012"):
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
@patch("agents.jd_analysis_agent.get_llm")
@patch("database.user_profiles.get_database")
@patch("agents.jd_analysis_agent.get_database")
async def test_analyze_endpoint_cached(mock_agent_db, mock_profile_db, mock_get_llm):
    mock_db = MagicMock()
    mock_agent_db.return_value = mock_db
    mock_profile_db.return_value = mock_db

    job_id = str(ObjectId())
    user_id = "507f1f77bcf86cd799439012"

    # Mock job document with already cached analysis
    mock_db.jobs.find_one = AsyncMock(return_value={
        "_id": ObjectId(job_id),
        "skill_match_score": 85,
        "matched_skills": ["Python"],
        "missing_skills": ["C++"],
        "learning_priority": ["C++"],
        "jd_summary": "Cached Summary",
        "experience_required": "2 years",
        "responsibilities": ["Coding"],
        "important_keywords": ["Developer"],
    })
    
    mock_db.user_profiles.find_one = AsyncMock(return_value={
        "_id": ObjectId("507f1f77bcf86cd799439011"),
        "user_id": ObjectId(user_id),
        "skills": ["Python"],
    })

    response = client.post(f"/api/v1/jobs/{job_id}/analyze", headers=get_auth_headers(user_id))
    
    assert response.status_code == 200
    data = response.json()
    assert data["skill_match_score"] == 85
    assert data["jd_summary"] == "Cached Summary"
    mock_get_llm.assert_not_called()


@pytest.mark.asyncio
@patch("agents.jd_analysis_agent.get_llm")
@patch("database.user_profiles.get_database")
@patch("agents.jd_analysis_agent.get_database")
async def test_analyze_endpoint_uncached(mock_agent_db, mock_profile_db, mock_get_llm):
    mock_db = MagicMock()
    mock_agent_db.return_value = mock_db
    mock_profile_db.return_value = mock_db

    job_id = str(ObjectId())
    user_id = "507f1f77bcf86cd799439012"

    # Mock job document without cached analysis
    mock_db.jobs.find_one = AsyncMock(return_value={
        "_id": ObjectId(job_id),
        "description": "We need a Python developer with Docker skills.",
        "skill_match_score": None,
    })
    
    mock_db.user_profiles.find_one = AsyncMock(return_value={
        "_id": ObjectId("507f1f77bcf86cd799439011"),
        "user_id": ObjectId(user_id),
        "skills": ["Python"],
    })

    # Mock LLM structure wrapper
    mock_llm = AsyncMock()
    mock_get_llm.return_value = mock_llm

    # Mock structured return value
    mock_analysis_json = """{
        "required_skills": ["Python"],
        "preferred_skills": ["Docker"],
        "experience_required": "1-3 years",
        "responsibilities": ["Maintain API"],
        "important_keywords": ["Python", "Docker"],
        "jd_summary": "Truncated Job Summary"
    }"""
    mock_llm.ainvoke.return_value = mock_analysis_json

    mock_db.jobs.update_one = AsyncMock()

    response = client.post(f"/api/v1/jobs/{job_id}/analyze", headers=get_auth_headers(user_id))
    
    assert response.status_code == 200
    data = response.json()
    assert data["skill_match_score"] == 70  # Python (70% required) matched, Docker (30% preferred) not matched
    assert data["jd_summary"] == "Truncated Job Summary"
    
    mock_db.jobs.update_one.assert_called_once()


@pytest.mark.asyncio
@patch("database.user_profiles.get_database")
@patch("agents.jd_analysis_agent.get_database")
async def test_analyze_endpoint_job_not_found(mock_agent_db, mock_profile_db):
    mock_db = MagicMock()
    mock_agent_db.return_value = mock_db
    mock_profile_db.return_value = mock_db

    job_id = str(ObjectId())
    user_id = "507f1f77bcf86cd799439012"

    # Mock job not found
    mock_db.jobs.find_one = AsyncMock(return_value=None)
    
    # Mock user profile lookup to prevent crash
    mock_db.user_profiles.find_one = AsyncMock(return_value={
        "_id": ObjectId("507f1f77bcf86cd799439011"),
        "user_id": ObjectId(user_id),
        "skills": [],
    })
    
    response = client.post(f"/api/v1/jobs/{job_id}/analyze", headers=get_auth_headers(user_id))
    
    assert response.status_code == 404
    assert "Job not found" in response.json()["detail"]


@pytest.mark.asyncio
@patch("agents.jd_analysis_agent.get_llm")
@patch("database.user_profiles.get_database")
@patch("agents.jd_analysis_agent.get_database")
async def test_analyze_endpoint_llm_failure_fallback(mock_agent_db, mock_profile_db, mock_get_llm):
    mock_db = MagicMock()
    mock_agent_db.return_value = mock_db
    mock_profile_db.return_value = mock_db

    job_id = str(ObjectId())
    user_id = "507f1f77bcf86cd799439012"

    # Mock job document with existing Phase 3 skills
    mock_db.jobs.find_one = AsyncMock(return_value={
        "_id": ObjectId(job_id),
        "description": "Python job",
        "required_skills": ["Python"],
        "preferred_skills": ["Git"],
        "skill_match_score": None,
    })
    
    mock_db.user_profiles.find_one = AsyncMock(return_value={
        "_id": ObjectId("507f1f77bcf86cd799439011"),
        "user_id": ObjectId(user_id),
        "skills": ["Python"],
    })

    # Mock LLM to fail
    mock_llm = AsyncMock()
    mock_get_llm.return_value = mock_llm
    mock_llm.ainvoke.side_effect = Exception("Ollama offline")

    mock_db.jobs.update_one = AsyncMock()

    response = client.post(f"/api/v1/jobs/{job_id}/analyze", headers=get_auth_headers(user_id))
    
    assert response.status_code == 200
    data = response.json()
    assert data["skill_match_score"] is None  # Should remain null / None
    assert data["jd_summary"] == "Detailed analysis unavailable — showing basic skill comparison."
    
    # Assert database update/cache was NOT called
    mock_db.jobs.update_one.assert_not_called()
