import json
from pathlib import Path
import pytest
from tools.unstop import scrape_unstop, build_unstop_url, _build_api_params, _extract_listing


def test_build_unstop_url():
    url = build_unstop_url("Data Scientist", "Delhi")
    assert "unstop.com/jobs" in url
    assert "searchTerm=Data%20Scientist" in url
    assert "location=Delhi" in url


def test_build_unstop_url_empty():
    url = build_unstop_url("", "")
    assert url == "https://unstop.com/jobs"


def test_build_api_params():
    params = _build_api_params("backend developer", "bangalore", per_page=5)
    assert params["opportunity"] == "jobs"
    assert params["oppstatus"] == "open"
    assert params["searchTerm"] == "backend developer"
    assert params["city"] == "bangalore"
    assert params["per_page"] == 5


def test_build_api_params_empty_location():
    params = _build_api_params("developer", "", per_page=10)
    assert "searchTerm" in params
    assert "city" not in params


def test_extract_listing():
    item = {
        "title": "Test Job",
        "seo_url": "https://unstop.com/jobs/test-job-123",
        "organisation": {"name": "TestCorp"},
        "jobDetail": {"locations": ["Mumbai"]},
    }
    result = _extract_listing(item, "https://unstop.com/jobs")
    assert result["source"] == "unstop"
    assert result["url"] == "https://unstop.com/jobs/test-job-123"
    assert "scraped_at" in result
    parsed = json.loads(result["raw_html"])
    assert parsed["title"] == "Test Job"


def test_extract_listing_structured_flag_and_fields():
    """Verify that Unstop listings carry the structured flag and pre-extracted fields."""
    item = {
        "title": "ML Engineer",
        "seo_url": "https://unstop.com/jobs/ml-eng-789",
        "organisation": {"name": "DeepTech Inc"},
        "jobDetail": {
            "locations": ["Hyderabad", "Remote"],
            "show_salary": True,
            "min_salary": 50000,
            "max_salary": 80000,
            "currency": "rupee",
            "pay_in": "monthly",
        },
        "required_skills": [
            {"skill_name": "Python"},
            {"skill_name": "TensorFlow"},
        ],
        "details": "<p>Build production ML pipelines...</p>",
    }
    result = _extract_listing(item, "https://unstop.com/jobs")

    # Structured flag — lets Extraction Agent skip LLM parsing
    assert result["structured"] is True

    # Pre-extracted top-level fields
    assert result["title"] == "ML Engineer"
    assert result["company"] == "DeepTech Inc"
    assert result["location"] == "Hyderabad, Remote"
    assert result["salary"] is not None and "50000" in result["salary"]
    assert result["skills"] == ["Python", "TensorFlow"]
    assert "ML pipelines" in result["description"]

    # Consistency fields still present
    assert result["source"] == "unstop"
    assert "scraped_at" in result
    assert result["url"] == "https://unstop.com/jobs/ml-eng-789"


def test_extract_listing_fallback_url():
    item = {"title": "No URL Job", "public_url": "jobs/no-url-456"}
    result = _extract_listing(item, "https://unstop.com/jobs")
    assert result["url"] == "https://unstop.com/jobs/no-url-456"


@pytest.mark.integration
@pytest.mark.live
@pytest.mark.asyncio
async def test_scrape_unstop_live():
    results = await scrape_unstop(role="data scientist", location="delhi", max_results=3)
    assert isinstance(results, list)
    assert len(results) >= 1, "Expected at least 1 result from live API"
    for r in results:
        assert r["source"] == "unstop"
        assert r["structured"] is True
        assert isinstance(r["title"], str) and r["title"]
        assert isinstance(r["company"], str)
        assert isinstance(r["skills"], list)
        assert "raw_html" in r
        assert "url" in r
        assert "scraped_at" in r
        # Verify raw_html is valid JSON with expected fields
        item = json.loads(r["raw_html"])
        assert "title" in item
        assert "organisation" in item
