import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId

from agents.interview_agent import generate_interview_questions

@pytest.mark.asyncio
@patch("agents.interview_agent.get_llm")
@patch("agents.interview_agent.get_database")
async def test_generate_interview_questions_cache_hit(mock_get_db, mock_get_llm):
    # Setup database mock
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db
    
    job_id = ObjectId()
    cached_questions = [
        {"question": "What is Python?", "topic": "Python", "difficulty": "easy"},
        {"question": "Explain FastAPI dependency injection.", "topic": "FastAPI", "difficulty": "medium"}
    ]
    
    mock_db.jobs.find_one = AsyncMock(return_value={
        "_id": job_id,
        "interview_questions": cached_questions
    })
    
    # Call the agent
    result = await generate_interview_questions(str(job_id), question_count=10)
    
    # Assert
    assert result == {"interview_questions": cached_questions}
    mock_get_llm.assert_not_called()


@pytest.mark.asyncio
@patch("agents.interview_agent.get_llm")
@patch("agents.interview_agent.get_database")
async def test_generate_interview_questions_success(mock_get_db, mock_get_llm):
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db
    
    job_id = ObjectId()
    job_doc = {
        "_id": job_id,
        "required_skills": ["Python", "FastAPI"],
        "preferred_skills": ["Docker"],
        "raw_description": "We need a Python developer who knows FastAPI.",
        "interview_questions": None
    }
    mock_db.jobs.find_one = AsyncMock(return_value=job_doc)
    mock_db.jobs.update_one = AsyncMock()

    # Mock LangChain LLM
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm
    
    # Expected output matching InterviewQuestionsListModel schema
    json_output = """{
        "interview_questions": [
            {"question": "Explain GIL in Python.", "topic": "Python", "difficulty": "hard"},
            {"question": "How to create a route in FastAPI?", "topic": "FastAPI", "difficulty": "easy"}
        ]
    }"""
    mock_llm.ainvoke = AsyncMock(return_value=json_output)

    # Run agent
    result = await generate_interview_questions(str(job_id), question_count=2)

    # Verification
    assert len(result["interview_questions"]) == 2
    assert result["interview_questions"][0]["topic"] == "Python"
    assert result["interview_questions"][1]["topic"] == "FastAPI"
    
    # Ensure it updated the database cache
    mock_db.jobs.update_one.assert_called_once()
    call_args = mock_db.jobs.update_one.call_args[0]
    assert call_args[0] == {"_id": job_id}
    assert "interview_questions" in call_args[1]["$set"]


@pytest.mark.asyncio
@patch("agents.interview_agent.get_llm")
@patch("agents.interview_agent.get_database")
async def test_generate_interview_questions_retry_success(mock_get_db, mock_get_llm):
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db
    
    job_id = ObjectId()
    job_doc = {
        "_id": job_id,
        "required_skills": ["Python"],
        "raw_description": "Python dev",
        "interview_questions": []
    }
    mock_db.jobs.find_one = AsyncMock(return_value=job_doc)
    mock_db.jobs.update_one = AsyncMock()

    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm
    
    # First invoke fails or returns empty/invalid JSON. Second works.
    mock_llm.ainvoke = AsyncMock()
    mock_llm.ainvoke.side_effect = [
        "INVALID JSON CONTENT",
        """{"interview_questions": [{"question": "Python Q?", "topic": "Python", "difficulty": "easy"}]}"""
    ]

    result = await generate_interview_questions(str(job_id), question_count=1)

    assert len(result["interview_questions"]) == 1
    assert result["interview_questions"][0]["question"] == "Python Q?"
    assert mock_llm.ainvoke.call_count == 2
    mock_db.jobs.update_one.assert_called_once()


@pytest.mark.asyncio
@patch("agents.interview_agent.get_llm")
@patch("agents.interview_agent.get_database")
async def test_generate_interview_questions_fallback(mock_get_db, mock_get_llm):
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db
    
    job_id = ObjectId()
    job_doc = {
        "_id": job_id,
        "required_skills": ["Python"],
        "raw_description": "Python dev"
    }
    mock_db.jobs.find_one = AsyncMock(return_value=job_doc)
    mock_db.jobs.update_one = AsyncMock()

    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm
    
    # Both fail
    mock_llm.ainvoke = AsyncMock(side_effect=Exception("LLM Down"))

    result = await generate_interview_questions(str(job_id), question_count=1)

    # Should fallback gracefully to empty list without caching
    assert result == {"interview_questions": []}
    mock_db.jobs.update_one.assert_not_called()
