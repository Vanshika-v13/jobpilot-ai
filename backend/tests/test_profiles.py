import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@patch("api.v1.profiles.insert_profile")
@patch("api.v1.profiles.get_profile_by_id")
def test_create_profile(mock_get_profile, mock_insert_profile):
    mock_insert_profile.return_value = "507f1f77bcf86cd799439011"
    mock_get_profile.return_value = {
        "_id": "507f1f77bcf86cd799439011",
        "user_id": "507f1f77bcf86cd799439012",
        "skills": ["Python", "FastAPI"],
        "experience_years": 2.0,
        "education": "B.Tech",
        "preferred_roles": ["Backend Developer"],
        "preferred_locations": ["Remote"],
        "preferred_location": "Remote",
        "resume_text": "Sample resume content",
        "updated_at": "2026-07-26T12:00:00"
    }

    payload = {
        "user_id": "507f1f77bcf86cd799439012",
        "skills": ["Python", "FastAPI"],
        "experience_years": 2.0,
        "education": "B.Tech",
        "preferred_roles": ["Backend Developer"],
        "preferred_locations": ["Remote"],
        "preferred_location": "Remote",
        "resume_text": "Sample resume content"
    }

    response = client.post("/api/v1/profiles", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert (data.get("_id") or data.get("id")) == "507f1f77bcf86cd799439011"
    assert data["skills"] == ["Python", "FastAPI"]
    mock_insert_profile.assert_called_once()
    mock_get_profile.assert_called_once_with("507f1f77bcf86cd799439011")


@patch("api.v1.profiles.get_profile_by_id")
def test_get_profile_success(mock_get_profile):
    profile_id = "507f1f77bcf86cd799439011"
    mock_get_profile.return_value = {
        "_id": profile_id,
        "user_id": "507f1f77bcf86cd799439012",
        "skills": ["Python", "FastAPI"],
        "experience_years": 2.0,
        "education": "B.Tech",
        "preferred_roles": ["Backend Developer"],
        "preferred_locations": ["Remote"],
        "preferred_location": "Remote",
        "resume_text": "Sample resume content",
        "updated_at": "2026-07-26T12:00:00"
    }

    response = client.get(f"/api/v1/profiles/{profile_id}")
    assert response.status_code == 200
    data = response.json()
    assert (data.get("_id") or data.get("id")) == profile_id
    assert data["skills"] == ["Python", "FastAPI"]
    mock_get_profile.assert_called_once_with(profile_id)


@patch("api.v1.profiles.get_profile_by_id")
def test_get_profile_not_found(mock_get_profile):
    mock_get_profile.return_value = None
    response = client.get("/api/v1/profiles/507f1f77bcf86cd799439011")
    assert response.status_code == 404
    assert response.json()["detail"] == "Profile not found"
