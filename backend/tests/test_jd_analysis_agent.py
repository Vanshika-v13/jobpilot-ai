import pytest  # type: ignore # pylint: disable=import-error
from unittest.mock import AsyncMock, MagicMock, patch
from bson.objectid import ObjectId  # type: ignore # pylint: disable=import-error


from agents.jd_analysis_agent import (
    calculate_skill_gap,
    analyze_jd,
    JDAnalysisModel,
    TRUNCATION_THRESHOLD,
)

# ---------------------------------------------------------------------------
# calculate_skill_gap Unit Tests
# ---------------------------------------------------------------------------

def test_calculate_skill_gap_standard():
    required = ["Python", "FastAPI", "React"]
    preferred = ["Docker", "AWS"]
    user = ["python", "react", "docker"]  # Lowercase to test normalization

    results = calculate_skill_gap(required, preferred, user)

    # Required: Python, React matched (2/3) -> 0.7 * (2/3) = 0.4667
    # Preferred: Docker matched (1/2) -> 0.3 * (1/2) = 0.15
    # Total Score: (0.4667 + 0.15) * 100 = 61.67 -> Rounded to 62
    assert results["skill_match_score"] == 62
    assert "Python" in results["matched_skills"]
    assert "React" in results["matched_skills"]
    assert "Docker" in results["matched_skills"]
    assert "FastAPI" in results["missing_skills"]
    assert "AWS" in results["missing_skills"]
    assert results["learning_priority"] == ["FastAPI", "AWS"]


def test_calculate_skill_gap_only_required():
    required = ["Python", "Django"]
    preferred = []
    user = ["python"]

    results = calculate_skill_gap(required, preferred, user)

    # 1/2 required matched -> 50%
    assert results["skill_match_score"] == 50
    assert results["matched_skills"] == ["Python"]
    assert results["missing_skills"] == ["Django"]


def test_calculate_skill_gap_only_preferred():
    required = []
    preferred = ["TypeScript", "Next.js"]
    user = ["typescript"]

    results = calculate_skill_gap(required, preferred, user)

    # 1/2 preferred matched -> 50%
    assert results["skill_match_score"] == 50
    assert results["matched_skills"] == ["TypeScript"]
    assert results["missing_skills"] == ["Next.js"]


def test_calculate_skill_gap_no_skills_neutral_score():
    required = []
    preferred = []
    user = ["Python"]

    results = calculate_skill_gap(required, preferred, user)

    # Decision 2: Should default to exactly 50
    assert results["skill_match_score"] == 50
    assert results["matched_skills"] == []
    assert results["missing_skills"] == []
    assert results["learning_priority"] == []


# ---------------------------------------------------------------------------
# analyze_jd Agent Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("agents.jd_analysis_agent.get_llm")
@patch("database.user_profiles.get_database")
@patch("agents.jd_analysis_agent.get_database")
async def test_analyze_jd_caching(mock_get_database_agent, mock_get_database_profiles, mock_get_llm):
    # Mock Database
    mock_db = MagicMock()
    mock_get_database_agent.return_value = mock_db
    mock_get_database_profiles.return_value = mock_db
    
    job_id = ObjectId()
    profile_id = ObjectId()

    # Mock job document with already cached analysis
    mock_db.jobs.find_one = AsyncMock(return_value={
        "_id": job_id,
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
        "_id": profile_id,
        "skills": ["Python"],
    })

    result = await analyze_jd(str(job_id), str(profile_id))

    # Assert database queries
    mock_db.jobs.find_one.assert_called_once_with({"_id": job_id})
    mock_db.user_profiles.find_one.assert_called_once_with({"_id": profile_id})
    
    # Assert returning cached fields and get_llm is NOT called
    assert result["skill_match_score"] == 85
    assert result["jd_summary"] == "Cached Summary"
    mock_get_llm.assert_not_called()


@pytest.mark.asyncio
@patch("agents.jd_analysis_agent.get_llm")
@patch("database.user_profiles.get_database")
@patch("agents.jd_analysis_agent.get_database")
async def test_analyze_jd_truncation(mock_get_database_agent, mock_get_database_profiles, mock_get_llm):
    # Mock Database
    mock_db = MagicMock()
    mock_get_database_agent.return_value = mock_db
    mock_get_database_profiles.return_value = mock_db
    
    job_id = ObjectId()
    profile_id = ObjectId()

    # Create description longer than truncation threshold (4000 chars)
    long_description = "Requirements: " + "a" * (TRUNCATION_THRESHOLD + 100)
    
    mock_db.jobs.find_one = AsyncMock(return_value={
        "_id": job_id,
        "description": long_description,
        "skill_match_score": None,  # Force analysis
    })
    
    mock_db.user_profiles.find_one = AsyncMock(return_value={
        "_id": profile_id,
        "skills": ["Python"],
    })

    # Mock LLM structure wrapper
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock()
    mock_get_llm.return_value = mock_llm
    
    # Mock structured return value using patch on PydanticOutputParser
    mock_analysis = JDAnalysisModel(
        required_skills=["Python"],
        preferred_skills=["Docker"],
        experience_required="1-3 years",
        responsibilities=["Maintain API"],
        important_keywords=["Python", "Docker"],
        jd_summary="Truncated Job Summary",
    )
    
    mock_db.jobs.update_one = AsyncMock()

    with patch("agents.jd_analysis_agent.PydanticOutputParser") as mock_parser_class:
        mock_parser_instance = MagicMock()
        mock_parser_class.return_value = mock_parser_instance
        mock_parser_instance.get_format_instructions.return_value = "format instructions"
        mock_parser_instance.invoke.return_value = mock_analysis
        
        result = await analyze_jd(str(job_id), str(profile_id))

    # Verify LLM was called and prompt is truncated
    assert mock_llm.ainvoke.called
    call_args = mock_llm.ainvoke.call_args[0][0]
    
    # Check that description in the LLM call does not exceed the truncation threshold limit
    # The prompt consists of "Job Description:\n" + truncated description.
    # Therefore, the long description text inside should be truncated to exactly TRUNCATION_THRESHOLD.
    assert len(long_description) > TRUNCATION_THRESHOLD
    assert "Requirements: " + "a" * (TRUNCATION_THRESHOLD - len("Requirements: ")) in call_args
    assert "a" * (TRUNCATION_THRESHOLD + 50) not in call_args

    # Verify returning valid response
    assert result["skill_match_score"] == 70  # Python matched (70%), Docker not matched
    assert result["jd_summary"] == "Truncated Job Summary"
    
    # Verify cached results update
    mock_db.jobs.update_one.assert_called_once()
    set_fields = mock_db.jobs.update_one.call_args[0][1]["$set"]
    assert set_fields["skill_match_score"] == 70


@pytest.mark.asyncio
@patch("agents.jd_analysis_agent.get_llm")
@patch("database.user_profiles.get_database")
@patch("agents.jd_analysis_agent.get_database")
async def test_analyze_jd_llm_failure_fallback(mock_get_database_agent, mock_get_database_profiles, mock_get_llm):
    # Mock Database
    mock_db = MagicMock()
    mock_get_database_agent.return_value = mock_db
    mock_get_database_profiles.return_value = mock_db
    
    job_id = ObjectId()
    profile_id = ObjectId()

    # Mock job document with some basic skills from Phase 3
    mock_db.jobs.find_one = AsyncMock(return_value={
        "_id": job_id,
        "description": "Short Job Description",
        "required_skills": ["SQL", "Java"],
        "preferred_skills": ["Rust"],
        "skill_match_score": None,  # Force analysis
    })
    
    mock_db.user_profiles.find_one = AsyncMock(return_value={
        "_id": profile_id,
        "skills": ["SQL"],
    })

    # Mock LLM structure wrapper
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock()
    # Simulate LLM throwing an exception
    mock_llm.ainvoke.side_effect = Exception("Ollama connection refused")
    mock_get_llm.return_value = mock_llm

    mock_db.jobs.update_one = AsyncMock()

    with patch("agents.jd_analysis_agent.PydanticOutputParser") as mock_parser_class:
        mock_parser_instance = MagicMock()
        mock_parser_class.return_value = mock_parser_instance
        mock_parser_instance.get_format_instructions.return_value = "format instructions"
        
        result = await analyze_jd(str(job_id), str(profile_id))

    # LLM should have been called (and failed), resulting in fallback logic.
    # The agent retries once, so ainvoke should be called 2 times.
    assert mock_llm.ainvoke.call_count == 2
    
    # Assert that it returns partial results instead of crashing
    assert result["skill_match_score"] is None  # Should remain null, not cached
    assert result["matched_skills"] == ["SQL"]
    assert result["missing_skills"] == ["Java", "Rust"]
    assert result["jd_summary"] == "Detailed analysis unavailable — showing basic skill comparison."
    
    # Assert database update/cache was NOT called (we do not cache failed/partial results)
    mock_db.jobs.update_one.assert_not_called()
