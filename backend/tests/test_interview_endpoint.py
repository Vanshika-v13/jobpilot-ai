import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from bson import ObjectId
from main import app
from core.auth import create_access_token

def get_auth_headers(user_id: str = "507f1f77bcf86cd799439012"):
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
@patch("api.v1.jobs.generate_interview_questions")
async def test_endpoint_generate_questions_success(mock_generate):
    job_id = str(ObjectId())
    expected_response = {
        "interview_questions": [
            {"question": "What is Python?", "topic": "Python", "difficulty": "easy"}
        ]
    }
    mock_generate.return_value = expected_response

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/jobs/{job_id}/interview-questions",
            json={"question_count": 5},
            headers=get_auth_headers()
        )

    assert response.status_code == 200
    assert response.json() == expected_response
    mock_generate.assert_called_once_with(job_id, 5)


@pytest.mark.asyncio
@patch("api.v1.jobs.generate_interview_questions")
async def test_endpoint_generate_questions_default_count(mock_generate):
    job_id = str(ObjectId())
    expected_response = {"interview_questions": []}
    mock_generate.return_value = expected_response

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/jobs/{job_id}/interview-questions",
            json={},
            headers=get_auth_headers()
        )

    assert response.status_code == 200
    mock_generate.assert_called_once_with(job_id, 10)


@pytest.mark.asyncio
@patch("api.v1.jobs.generate_interview_questions")
async def test_endpoint_job_not_found(mock_generate):
    job_id = str(ObjectId())
    mock_generate.side_effect = ValueError(f"Job not found: {job_id}")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/jobs/{job_id}/interview-questions",
            json={"question_count": 3},
            headers=get_auth_headers()
        )

    assert response.status_code == 404
    assert "Job not found" in response.json()["detail"]

