from pathlib import Path
import pytest
from tools.internshala import scrape_internshala, build_internshala_url

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "internshala_sample.html"

def test_build_internshala_url():
    url = build_internshala_url("Software Developer", "Bangalore")
    assert "keywords-software-developer-in-bangalore" in url

    url_role_only = build_internshala_url("Frontend Developer", "")
    assert "keywords-frontend-developer" in url_role_only

def test_internshala_fixture_parsing():
    assert FIXTURE_PATH.exists()
    content = FIXTURE_PATH.read_text(encoding="utf-8")
    assert "individual_internship" in content
    assert "Software Development Engineering Intern" in content
    assert "TechCorp Solutions" in content

@pytest.mark.integration
@pytest.mark.live
@pytest.mark.asyncio
async def test_scrape_internshala_live():
    results = await scrape_internshala(role="developer", location="bangalore", max_results=3)
    assert isinstance(results, list)
    if results:
        first = results[0]
        assert first["source"] == "internshala"
        assert "raw_html" in first
        assert "url" in first
        assert "scraped_at" in first
