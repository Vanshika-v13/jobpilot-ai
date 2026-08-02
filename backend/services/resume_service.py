import io
import logging
from typing import Dict, Any

import pdfplumber
from langchain_core.output_parsers import PydanticOutputParser

from agents.llm_provider import get_llm
from prompts.resume_prompt import RESUME_EXTRACTION_PROMPT
from schemas.profile import ResumeExtractedData

logger = logging.getLogger(__name__)

def validate_pdf(file_bytes: bytes) -> None:
    """
    Validate that file size does not exceed 5 MB and starts with PDF magic bytes.
    """
    if len(file_bytes) > 5 * 1024 * 1024:
        raise ValueError("File too large. Maximum size is 5 MB.")
    if len(file_bytes) < 5 or file_bytes[:5] != b"%PDF-":
        raise ValueError("Invalid file type. Only PDF files are accepted.")

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract raw text from PDF bytes using pdfplumber.
    """
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            text_pages = []
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_pages.append(page_text)
            
            extracted_text = "\n".join(text_pages).strip()
            
            if len(extracted_text) < 50:
                raise ValueError("No readable text found in PDF. The file may be image-based or empty.")
            
            # Truncate to 8,000 characters max
            return extracted_text[:8000]
    except ValueError as ve:
        raise ve
    except Exception as e:
        logger.error(f"pdfplumber text extraction failed: {e}")
        raise ValueError("Could not extract text from PDF. The file may be corrupt or image-based.")

async def parse_resume_with_llm(resume_text: str) -> dict:
    """
    Use LLM to extract structured fields from raw resume text.
    """
    parser = PydanticOutputParser(pydantic_object=ResumeExtractedData)
    llm = get_llm()
    
    prompt = RESUME_EXTRACTION_PROMPT.format(
        resume_text=resume_text,
        format_instructions=parser.get_format_instructions()
    )
    
    try:
        response = await llm.ainvoke(prompt)
        extracted: ResumeExtractedData = parser.invoke(response)
        
        if not extracted.skills and not extracted.education:
            raise ValueError("All core fields empty. Likely a parsing failure.")
            
    except Exception as e:
        logger.warning(f"Initial LLM resume extraction failed: {e}. Retrying once...")
        try:
            retry_prompt = prompt + "\n\nCRITICAL: Respond with valid JSON ONLY. Do not wrap in markdown code blocks."
            response = await llm.ainvoke(retry_prompt)
            extracted: ResumeExtractedData = parser.invoke(response)
            
            if not extracted.skills and not extracted.education:
                raise ValueError("All core fields empty on retry.")
        except Exception as retry_e:
            logger.error(f"Retry LLM resume extraction failed: {retry_e}")
            raise RuntimeError("Failed to extract profile data from resume.")
            
    if hasattr(extracted, "model_dump"):
        return extracted.model_dump()
    return extracted.dict()
