import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from bson import ObjectId

from agents.llm_provider import get_llm
from agents.extraction_agent import sanitize_description
from prompts.interview_prompt import INTERVIEW_PROMPT
from database.connection import get_database

logger = logging.getLogger(__name__)

TRUNCATION_THRESHOLD = 4000

class InterviewQuestionModel(BaseModel):
    question: str = Field(description="The interview question text")
    topic: str = Field(description="The specific topic or skill tested by the question")
    difficulty: str = Field(description="Strictly one of 'easy', 'medium', or 'hard'")

class InterviewQuestionsListModel(BaseModel):
    interview_questions: List[InterviewQuestionModel] = Field(default_factory=list, description="List of generated interview questions")

async def generate_interview_questions(job_id: str, question_count: int = 10) -> Dict[str, Any]:
    """
    Generate role-specific interview questions based on job description.
    Checks cache first.
    """
    db = get_database()
    
    # 1. Fetch job
    try:
        job_oid = ObjectId(job_id) if isinstance(job_id, str) else job_id
        job = await db.jobs.find_one({"_id": job_oid})
    except Exception as e:
        logger.error(f"Invalid job ID: {job_id}. Error: {e}")
        job = None

    if not job:
        raise ValueError(f"Job not found: {job_id}")

    # 2. Check read-through cache
    cached_questions = job.get("interview_questions")
    if cached_questions is not None and isinstance(cached_questions, list) and len(cached_questions) > 0:
        logger.info(f"Returning cached interview questions for job {job_id}")
        return {"interview_questions": cached_questions}

    # 3. Prepare job description & details
    raw_desc = job.get("description") or job.get("raw_description") or ""
    sanitized = sanitize_description(raw_desc)
    
    if len(sanitized) > TRUNCATION_THRESHOLD:
        logger.info(f"Job description of length {len(sanitized)} exceeds threshold. Truncating.")
        truncated_desc = sanitized[:TRUNCATION_THRESHOLD]
    else:
        truncated_desc = sanitized

    required_skills = job.get("required_skills") or []
    preferred_skills = job.get("preferred_skills") or []

    # 4. Compute 70/30 split
    technical_count = int(round(question_count * 0.7))
    hr_count = max(0, question_count - technical_count)

    # 5. LLM Structured Extraction with Json Parsing & Retries
    parser = PydanticOutputParser(pydantic_object=InterviewQuestionsListModel)
    llm_failed = False
    generated_data = None

    try:
        llm = get_llm()
        prompt = INTERVIEW_PROMPT.format(
            question_count=question_count,
            technical_count=technical_count,
            hr_count=hr_count,
            required_skills=", ".join(required_skills) if required_skills else "None specified",
            preferred_skills=", ".join(preferred_skills) if preferred_skills else "None specified",
            job_description=truncated_desc,
            format_instructions=parser.get_format_instructions()
        )
        
        response = await llm.ainvoke(prompt)
        generated_data = parser.invoke(response)
        
        if not generated_data.interview_questions:
            raise ValueError("Empty interview questions returned. Likely a parsing failure.")
            
    except Exception as e:
        logger.warning(f"Initial LLM interview question generation failed for job {job_id}: {e}. Retrying once...")
        try:
            retry_prompt = prompt + "\n\nCRITICAL: Respond with valid JSON ONLY. Do not wrap in markdown code blocks."
            response = await llm.ainvoke(retry_prompt)
            generated_data = parser.invoke(response)
            
            if not generated_data.interview_questions:
                raise ValueError("Empty interview questions returned on retry.")
        except Exception as retry_e:
            logger.error(f"Retry LLM interview generation failed for job {job_id}: {retry_e}", exc_info=True)
            llm_failed = True

    # 6. Fallback or return/cache
    if llm_failed or not generated_data:
        # Graceful fallback: return empty response, do not cache so it can be retried later
        return {"interview_questions": []}

    # Convert Pydantic models back to dictionaries
    questions_list = [q.model_dump() for q in generated_data.interview_questions]

    # Cache successful results in the jobs collection
    try:
        await db.jobs.update_one(
            {"_id": job_oid},
            {"$set": {"interview_questions": questions_list}}
        )
        logger.info(f"Successfully cached {len(questions_list)} interview questions for job {job_id}")
    except Exception as e:
        logger.error(f"Failed to cache interview questions for job {job_id}: {e}")

    return {"interview_questions": questions_list}
