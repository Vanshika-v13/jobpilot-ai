import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from bson import ObjectId
from agents.extraction_agent import (
    ExtractedJob,
    extract_structured_job,
    extract_html_job,
    process_scraped_results,
)

def test_extract_structured_job():
    raw_job = {
        "source": "unstop",
        "structured": True,
        "title": "Junior Backend Developer Intern",
        "company": "FastTech Solutions",
        "location": "Bangalore, India",
        "salary": "₹30,000 / month",
        "skills": ["Python", "FastAPI", "PostgreSQL"],
        "description": "<p>Learn backend development...</p>",
        "url": "https://unstop.com/jobs/junior-backend-developer-intern-999",
        "scraped_at": "2026-07-25T18:00:00Z",
    }
    
    normalized = extract_structured_job(raw_job)
    
    assert normalized["company"] == "FastTech Solutions"
    assert normalized["role"] == "Junior Backend Developer Intern"
    assert normalized["location"] == "Bangalore, India"
    assert normalized["salary"] == "₹30,000 / month"
    assert normalized["apply_link"] == "https://unstop.com/jobs/junior-backend-developer-intern-999"
    assert normalized["source"] == "unstop"
    assert normalized["required_skills"] == ["Python", "FastAPI", "PostgreSQL"]
    assert normalized["preferred_skills"] == []
    assert "Learn backend development" in normalized["raw_description"]
    assert normalized["job_type"] == "internship"  # Determined from title containing 'intern'
    assert normalized["scraped_at"] == "2026-07-25T18:00:00Z"

@pytest.mark.asyncio
@patch("agents.extraction_agent.get_llm")
async def test_extract_html_job(mock_get_llm):
    # Mock LLM and structured output
    mock_llm = MagicMock()
    mock_structured_llm = AsyncMock()
    mock_get_llm.return_value = mock_llm
    mock_llm.with_structured_output.return_value = mock_structured_llm
    
    # Mock returned pydantic model
    mock_job_model = ExtractedJob(
        company="TechCorp Solutions",
        role="Frontend Engineer",
        location="Pune",
        salary="₹40,000 / month",
        posted_date="2026-07-24",
        required_skills=["React", "TypeScript"],
        preferred_skills=["Next.js"],
        raw_description="Build modern web UIs...",
        experience_required="0-2 years",
        job_type="full-time",
    )
    mock_structured_llm.ainvoke.return_value = mock_job_model
    
    raw_job = {
        "source": "internshala",
        "raw_html": "<div>TechCorp Solutions - Frontend Engineer</div>",
        "url": "https://internshala.com/internship/detail/frontend-eng-111",
        "scraped_at": "2026-07-25T18:30:00Z",
    }
    
    normalized = await extract_html_job(raw_job)
    
    assert normalized["company"] == "TechCorp Solutions"
    assert normalized["role"] == "Frontend Engineer"
    assert normalized["location"] == "Pune"
    assert normalized["salary"] == "₹40,000 / month"
    assert normalized["apply_link"] == "https://internshala.com/internship/detail/frontend-eng-111"
    assert normalized["source"] == "internshala"
    assert normalized["required_skills"] == ["React", "TypeScript"]
    assert normalized["preferred_skills"] == ["Next.js"]
    assert normalized["raw_description"] == "Build modern web UIs..."
    assert normalized["experience_required"] == "0-2 years"
    assert normalized["job_type"] == "full-time"
    assert normalized["scraped_at"] == "2026-07-25T18:30:00Z"
    
    mock_llm.with_structured_output.assert_called_once_with(ExtractedJob)
    mock_structured_llm.ainvoke.assert_called_once()

@pytest.mark.asyncio
@patch("agents.extraction_agent.update_job_search_status")
@patch("agents.extraction_agent.insert_jobs")
@patch("agents.extraction_agent.extract_html_job")
async def test_process_scraped_results_mixed_and_graceful_failures(
    mock_extract_html, mock_insert_jobs, mock_update_status,
):
    search_id = "665f19003c4d5e6f7a8b9c01"
    
    # 1. Unstop (structured) job
    unstop_raw = {
        "source": "unstop",
        "structured": True,
        "title": "ML Engineer",
        "company": "AI Labs",
        "location": "Remote",
        "salary": "Not disclosed",
        "skills": ["Python"],
        "description": "ML stuff",
        "url": "https://unstop.com/jobs/ml-1",
        "scraped_at": "2026-07-25T18:00:00Z",
    }
    
    # 2. Internshala job (successful HTML extract)
    internshala_raw = {
        "source": "internshala",
        "raw_html": "<div>Internshala Job</div>",
        "url": "https://internshala.com/detail/1",
        "scraped_at": "2026-07-25T18:00:00Z",
    }
    mock_extract_html.return_value = {
        "company": "Zeta Industries",
        "role": "QA Intern",
        "location": "Mumbai",
        "salary": "₹15,000 / month",
        "apply_link": "https://internshala.com/detail/1",
        "source": "internshala",
        "required_skills": ["Selenium"],
        "preferred_skills": [],
        "raw_description": "Test automation...",
        "experience_required": "0-1 years",
        "job_type": "internship",
        "scraped_at": "2026-07-25T18:00:00Z",
    }
    
    # 3. Failing job (should be skipped, continuing the batch)
    failing_raw = {
        "source": "internshala",
        "raw_html": "<div>Failing Job</div>",
        "url": "https://internshala.com/detail/fail",
        "scraped_at": "2026-07-25T18:00:00Z",
    }
    
    # We configure mock_extract_html to throw an exception on the second call
    mock_extract_html.side_effect = [
        mock_extract_html.return_value,
        Exception("Extraction API Timeout or Rate Limit Failure"),
    ]
    
    # Mock insert_jobs return value
    mock_insert_jobs.return_value = ["job_id_1", "job_id_2"]
    
    raw_results = [unstop_raw, internshala_raw, failing_raw]
    
    inserted_ids = await process_scraped_results(search_id, raw_results)
    
    assert len(inserted_ids) == 2
    assert inserted_ids == ["job_id_1", "job_id_2"]
    
    # Check database calls
    mock_update_status.assert_any_call(search_id, "running")
    mock_update_status.assert_any_call(search_id, "completed", 2)
    mock_insert_jobs.assert_called_once()
    
    # Verify the contents inserted contains search_id
    inserted_jobs_list = mock_insert_jobs.call_args[0][0]
    assert len(inserted_jobs_list) == 2
    assert inserted_jobs_list[0]["search_id"] == search_id
    assert inserted_jobs_list[0]["company"] == "AI Labs"
    assert inserted_jobs_list[1]["search_id"] == search_id
    assert inserted_jobs_list[1]["company"] == "Zeta Industries"
