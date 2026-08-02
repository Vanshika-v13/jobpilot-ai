import io
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from langchain_core.messages import AIMessage
from main import app
from core.auth import create_access_token
from services.resume_service import validate_pdf, extract_text_from_pdf, parse_resume_with_llm
from schemas.profile import ResumeExtractedData

client = TestClient(app)

# Helper for headers
def get_auth_headers(user_id: str = "507f1f77bcf86cd799439012"):
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}

# Read sample PDF content
def get_sample_pdf_bytes():
    with open("tests/fixtures/resume_sample.pdf", "rb") as f:
        return f.read()

# ---------------------------------------------------------------------------
# Validation Tests
# ---------------------------------------------------------------------------

def test_validate_pdf_valid():
    pdf_bytes = get_sample_pdf_bytes()
    # Should not raise any exception
    validate_pdf(pdf_bytes)

def test_validate_pdf_too_large():
    large_bytes = b"%PDF-" + b"0" * (5 * 1024 * 1024 + 1)
    with pytest.raises(ValueError) as exc:
        validate_pdf(large_bytes)
    assert "File too large" in str(exc.value)

def test_validate_pdf_invalid_magic_bytes():
    invalid_bytes = b"NOTAPDF" + b"0" * 100
    with pytest.raises(ValueError) as exc:
        validate_pdf(invalid_bytes)
    assert "Only PDF files are accepted" in str(exc.value)

# ---------------------------------------------------------------------------
# Text Extraction Tests
# ---------------------------------------------------------------------------

def test_extract_text_from_pdf_success():
    pdf_bytes = get_sample_pdf_bytes()
    text = extract_text_from_pdf(pdf_bytes)
    assert "Hello World from PDF!" in text
    assert "Python" in text
    assert len(text) >= 50

def test_extract_text_from_pdf_empty_or_image_only():
    # A PDF structure with no content stream or empty pages
    empty_pdf = b"%PDF-1.4\n" + b"0" * 100
    with pytest.raises(ValueError) as exc:
        extract_text_from_pdf(empty_pdf)
    assert "Could not extract text" in str(exc.value) or "No readable text" in str(exc.value)

def test_extract_text_from_pdf_truncation():
    # Mock pdfplumber to return a very large string
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "A" * 10000
    
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]
    
    with patch("pdfplumber.open") as mock_open:
        mock_open.return_value.__enter__.return_value = mock_pdf
        text = extract_text_from_pdf(b"%PDF-1.4")
        assert len(text) == 8000
        assert text == "A" * 8000

# ---------------------------------------------------------------------------
# LLM Parsing Tests (Mocked)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("services.resume_service.get_llm")
async def test_parse_resume_with_llm_success(mock_get_llm):
    # Set up mock LLM response
    mock_llm = AsyncMock()
    mock_get_llm.return_value = mock_llm
    
    mock_response = AIMessage(content='{"skills": ["Python", "FastAPI"], "experience_years": 3.5, "education": "B.S. in CS", "preferred_roles": ["Backend Engineer"]}')
    mock_llm.ainvoke.return_value = mock_response
    
    result = await parse_resume_with_llm("Resume text content...")
    assert result["skills"] == ["Python", "FastAPI"]
    assert result["experience_years"] == 3.5
    assert result["education"] == "B.S. in CS"
    assert result["preferred_roles"] == ["Backend Engineer"]
    assert mock_llm.ainvoke.call_count == 1

@pytest.mark.asyncio
@patch("services.resume_service.get_llm")
async def test_parse_resume_with_llm_retry_success(mock_get_llm):
    mock_llm = AsyncMock()
    mock_get_llm.return_value = mock_llm
    
    # First response fails to parse, second response succeeds
    mock_response_1 = AIMessage(content='Invalid response')
    mock_response_2 = AIMessage(content='{"skills": ["Python"], "experience_years": 2.0, "education": "BS", "preferred_roles": []}')
    
    mock_llm.ainvoke.side_effect = [mock_response_1, mock_response_2]
    
    result = await parse_resume_with_llm("Resume text content...")
    assert result["skills"] == ["Python"]
    assert mock_llm.ainvoke.call_count == 2

@pytest.mark.asyncio
@patch("services.resume_service.get_llm")
async def test_parse_resume_with_llm_failure(mock_get_llm):
    mock_llm = AsyncMock()
    mock_get_llm.return_value = mock_llm
    
    # Both fail
    mock_response = AIMessage(content='Invalid response')
    mock_llm.ainvoke.return_value = mock_response
    
    with pytest.raises(RuntimeError) as exc:
        await parse_resume_with_llm("Resume text content...")
    assert "Failed to extract profile data" in str(exc.value)
    assert mock_llm.ainvoke.call_count == 2


# ---------------------------------------------------------------------------
# Endpoint Integration Tests
# ---------------------------------------------------------------------------

@patch("api.v1.profile.validate_pdf")
@patch("api.v1.profile.extract_text_from_pdf")
@patch("api.v1.profile.parse_resume_with_llm")
@patch("api.v1.profile.get_or_create_profile")
@patch("api.v1.profile.update_profile_by_user_id")
def test_upload_resume_endpoint_success(
    mock_update, mock_get_or_create, mock_parse, mock_extract, mock_validate
):
    mock_extract.return_value = "Extracted resume text..."
    mock_parse.return_value = {
        "skills": ["Python", "FastAPI"],
        "experience_years": 2.0,
        "education": "B.Tech",
        "preferred_roles": ["Developer"]
    }
    mock_get_or_create.return_value = {"user_id": "507f1f77bcf86cd799439012"}
    mock_update.return_value = {
        "_id": "507f1f77bcf86cd799439011",
        "user_id": "507f1f77bcf86cd799439012",
        "skills": ["Python", "FastAPI"],
        "experience_years": 2.0,
        "education": "B.Tech",
        "preferred_roles": ["Developer"],
        "resume_text": "Extracted resume text...",
        "updated_at": "2026-08-02T12:00:00"
    }

    files = {"file": ("resume.pdf", io.BytesIO(b"%PDF-1.4..."), "application/pdf")}
    response = client.post("/api/v1/profile/upload-resume", files=files, headers=get_auth_headers())
    
    assert response.status_code == 200
    data = response.json()
    assert data["skills"] == ["Python", "FastAPI"]
    assert data["experience_years"] == 2.0
    
    mock_validate.assert_called_once()
    mock_extract.assert_called_once()
    mock_parse.assert_called_once()
    mock_get_or_create.assert_called_once_with("507f1f77bcf86cd799439012")
    mock_update.assert_called_once()

def test_upload_resume_endpoint_unauthenticated():
    files = {"file": ("resume.pdf", io.BytesIO(b"%PDF-1.4..."), "application/pdf")}
    response = client.post("/api/v1/profile/upload-resume", files=files)
    assert response.status_code == 401
