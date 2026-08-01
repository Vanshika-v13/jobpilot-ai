import os
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from bson import ObjectId

from main import app

@pytest.mark.asyncio
@patch("api.v1.export.get_jobs_by_ids")
async def test_export_endpoint_excel_success(mock_get_jobs):
    job_id = str(ObjectId())
    mock_get_jobs.return_value = [
        {
            "_id": job_id,
            "company": "Company A",
            "role": "Role A",
            "location": "Loc A",
            "salary": "Sal A",
            "relevance_score": 95,
            "skill_match_score": 80,
            "matched_skills": ["Python"],
            "missing_skills": [],
            "apply_link": "http://linka.com"
        }
    ]
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/export/",
            json={"job_ids": [job_id], "format": "excel"}
        )
        
    assert response.status_code == 200
    data = response.json()
    assert "file_url" in data
    assert data["format"] == "excel"
    assert data["job_count"] == 1
    assert data["file_url"].endswith(".xlsx")
    
    # Check that the file was actually written to the static exports directory
    filename = data["file_url"].split("/")[-1]
    expected_path = os.path.join("static", "exports", filename)
    assert os.path.exists(expected_path)
    
    # Cleanup generated file
    if os.path.exists(expected_path):
        os.remove(expected_path)

@pytest.mark.asyncio
@patch("api.v1.export.get_jobs_by_ids")
async def test_export_endpoint_pdf_success(mock_get_jobs):
    job_id = str(ObjectId())
    mock_get_jobs.return_value = [
        {
            "_id": job_id,
            "company": "Company A",
            "role": "Role A",
            "location": "Loc A",
            "salary": "Sal A",
            "relevance_score": 95,
            "skill_match_score": 80,
            "matched_skills": ["Python"],
            "missing_skills": [],
            "apply_link": "http://linka.com"
        }
    ]
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/export/",
            json={"job_ids": [job_id], "format": "pdf"}
        )
        
    assert response.status_code == 200
    data = response.json()
    assert "file_url" in data
    assert data["format"] == "pdf"
    assert data["job_count"] == 1
    assert data["file_url"].endswith(".pdf")
    
    # Check that the file was actually written to the static exports directory
    filename = data["file_url"].split("/")[-1]
    expected_path = os.path.join("static", "exports", filename)
    assert os.path.exists(expected_path)
    
    # Cleanup generated file
    if os.path.exists(expected_path):
        os.remove(expected_path)

@pytest.mark.asyncio
async def test_export_endpoint_invalid_format():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/export/",
            json={"job_ids": [str(ObjectId())], "format": "csv"}
        )
    assert response.status_code == 400
    assert "Unsupported format" in response.json()["detail"]

@pytest.mark.asyncio
@patch("api.v1.export.get_jobs_by_ids")
async def test_export_endpoint_jobs_not_found(mock_get_jobs):
    mock_get_jobs.return_value = []
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/export/",
            json={"job_ids": [str(ObjectId())], "format": "excel"}
        )
    assert response.status_code == 404
    assert "No valid jobs found" in response.json()["detail"]
