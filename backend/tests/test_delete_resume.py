import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from bson import ObjectId
from fastapi.testclient import TestClient

from main import app
from core.auth import create_access_token
from agents.jd_analysis_agent import analyze_jd

client = TestClient(app)

# Helper for headers
def get_auth_headers(user_id: str = "507f1f77bcf86cd799439012"):
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}

# ---------------------------------------------------------------------------
# Endpoint tests (mocked DB)
# ---------------------------------------------------------------------------

@patch("api.v1.profile.clear_resume_fields_by_user_id")
def test_delete_resume_success(mock_clear):
    user_id = "507f1f77bcf86cd799439012"
    mock_clear.return_value = {
        "_id": ObjectId("507f1f77bcf86cd799439011"),
        "user_id": ObjectId(user_id),
        "skills": [],
        "experience_years": 0.0,
        "education": None,
        "preferred_roles": [],
        "preferred_locations": ["Bangalore"],
        "preferred_location": "Bangalore",
        "resume_text": None,
        "updated_at": "2026-08-02T12:00:00"
    }

    response = client.delete("/api/v1/profile/resume", headers=get_auth_headers(user_id))
    assert response.status_code == 200
    data = response.json()
    assert data["skills"] == []
    assert data["experience_years"] == 0.0
    assert data["education"] is None
    assert data["preferred_roles"] == []
    assert data["resume_text"] is None
    mock_clear.assert_called_once_with(user_id)

def test_delete_resume_unauthenticated():
    response = client.delete("/api/v1/profile/resume")
    assert response.status_code == 401

@patch("api.v1.profile.clear_resume_fields_by_user_id")
def test_delete_resume_profile_not_found(mock_clear):
    user_id = "507f1f77bcf86cd799439012"
    mock_clear.return_value = None

    response = client.delete("/api/v1/profile/resume", headers=get_auth_headers(user_id))
    assert response.status_code == 404
    assert response.json()["detail"] == "Profile not found"

@patch("api.v1.profile.clear_resume_fields_by_user_id")
def test_delete_resume_preserves_user_fields(mock_clear):
    user_id = "507f1f77bcf86cd799439012"
    mock_clear.return_value = {
        "_id": ObjectId("507f1f77bcf86cd799439011"),
        "user_id": ObjectId(user_id),
        "skills": [],
        "experience_years": 0.0,
        "education": None,
        "preferred_roles": [],
        "preferred_locations": ["Bangalore"],
        "preferred_location": "Bangalore",
        "resume_text": None,
        "updated_at": "2026-08-02T12:00:00"
    }

    response = client.delete("/api/v1/profile/resume", headers=get_auth_headers(user_id))
    assert response.status_code == 200
    data = response.json()
    assert data["preferred_locations"] == ["Bangalore"]
    assert data["preferred_location"] == "Bangalore"

@patch("api.v1.profile.clear_resume_fields_by_user_id")
def test_delete_resume_idempotent(mock_clear):
    user_id = "507f1f77bcf86cd799439012"
    mock_clear.return_value = {
        "_id": ObjectId("507f1f77bcf86cd799439011"),
        "user_id": ObjectId(user_id),
        "skills": [],
        "experience_years": 0.0,
        "education": None,
        "preferred_roles": [],
        "preferred_locations": [],
        "preferred_location": None,
        "resume_text": None,
        "updated_at": "2026-08-02T12:00:00"
    }

    response = client.delete("/api/v1/profile/resume", headers=get_auth_headers(user_id))
    assert response.status_code == 200
    data = response.json()
    assert data["skills"] == []

# ---------------------------------------------------------------------------
# Job analysis profile_has_skills tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("agents.jd_analysis_agent.get_profile_by_id")
@patch("agents.jd_analysis_agent.get_database")
async def test_analyze_response_includes_profile_has_skills_true(mock_get_db, mock_get_profile):
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db

    job_id = ObjectId()
    profile_id = ObjectId()

    # Mock cached job analysis
    mock_db.jobs.find_one = AsyncMock(return_value={
        "_id": job_id,
        "skill_match_score": 85,
        "matched_skills": ["Python"],
        "missing_skills": ["C++"],
        "learning_priority": ["C++"],
        "jd_summary": "Cached Summary",
        "experience_required": "1-3 years",
        "responsibilities": [],
        "important_keywords": [],
    })

    # Profile has skills
    mock_get_profile.return_value = {
        "_id": profile_id,
        "skills": ["Python"],
        "experience_years": 1.0,
    }

    result = await analyze_jd(str(job_id), str(profile_id))
    assert result["profile_has_skills"] is True

@pytest.mark.asyncio
@patch("agents.jd_analysis_agent.get_profile_by_id")
@patch("agents.jd_analysis_agent.get_database")
async def test_analyze_response_includes_profile_has_skills_false(mock_get_db, mock_get_profile):
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db

    job_id = ObjectId()
    profile_id = ObjectId()

    # Mock cached job analysis
    mock_db.jobs.find_one = AsyncMock(return_value={
        "_id": job_id,
        "skill_match_score": 0,
        "matched_skills": [],
        "missing_skills": ["Python", "C++"],
        "learning_priority": ["Python", "C++"],
        "jd_summary": "Cached Summary",
        "experience_required": "1-3 years",
        "responsibilities": [],
        "important_keywords": [],
    })

    # Profile has NO skills
    mock_get_profile.return_value = {
        "_id": profile_id,
        "skills": [],
        "experience_years": 0.0,
    }

    result = await analyze_jd(str(job_id), str(profile_id))
    assert result["profile_has_skills"] is False
