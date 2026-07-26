import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from bson import ObjectId

from agents.llm_provider import get_llm
from database.collections import insert_jobs, update_job_search_status
from prompts.extraction_prompt import EXTRACTION_PROMPT

logger = logging.getLogger(__name__)

class ExtractedJob(BaseModel):
    company: str
    role: str
    location: str
    salary: str = "Not disclosed"
    posted_date: Optional[str] = None
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    raw_description: str
    experience_required: str = "Not disclosed"
    job_type: str = "full-time"  # 'full-time', 'part-time', 'contract', 'internship'

def extract_structured_job(raw_job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Direct Python field mapping for Unstop jobs. No LLM call.
    """
    title_lower = raw_job.get("title", "").lower()
    # Determine job type from title
    job_type = "internship" if "intern" in title_lower else "full-time"
    
    skills = raw_job.get("skills", [])
    
    mapped_job = {
        "company": raw_job.get("company") or "Not disclosed",
        "role": raw_job.get("title") or "Not disclosed",
        "location": raw_job.get("location") or "Remote",
        "salary": raw_job.get("salary") or "Not disclosed",
        "apply_link": raw_job.get("url", ""),
        "posted_date": "Not disclosed",
        "source": "unstop",
        "required_skills": skills,
        "preferred_skills": [],
        "raw_description": raw_job.get("description", "") or "",
        "experience_required": "Not disclosed",
        "job_type": job_type,
        "scraped_at": raw_job.get("scraped_at") or datetime.now(timezone.utc).isoformat()
    }
    
    return mapped_job

async def extract_html_job(raw_job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract structured job details from raw HTML/text using LangChain + LLM.
    """
    llm = get_llm()
    structured_llm = llm.with_structured_output(ExtractedJob)
    
    html_content = raw_job.get("raw_html", "")
    
    prompt = EXTRACTION_PROMPT.format(html_content=html_content)
    
    extracted: ExtractedJob = await structured_llm.ainvoke(prompt)
    
    if hasattr(extracted, "model_dump"):
        job_dict = extracted.model_dump()
    else:
        job_dict = extracted.dict()
        
    job_dict["apply_link"] = raw_job.get("url", "")
    job_dict["source"] = "internshala"
    job_dict["scraped_at"] = raw_job.get("scraped_at") or datetime.now(timezone.utc).isoformat()
    
    return job_dict

async def process_scraped_results(search_id: str, raw_results: List[Dict[str, Any]]) -> List[str]:
    """
    Orchestrates extraction from raw scraper results (structured or HTML)
    and saves the successfully normalized jobs to MongoDB under search_id.
    """
    logger.info(f"Starting process_scraped_results for search_id: {search_id}")
    await update_job_search_status(search_id, "running")
    
    normalized_jobs = []
    
    for idx, raw_job in enumerate(raw_results):
        try:
            logger.info(f"Processing job {idx + 1}/{len(raw_results)}")
            if raw_job.get("structured") is True:
                normalized = extract_structured_job(raw_job)
            else:
                normalized = await extract_html_job(raw_job)
            
            normalized["search_id"] = search_id
            normalized_jobs.append(normalized)
            
        except Exception as e:
            logger.error(f"Failed to extract job at index {idx} from raw result: {e}. Skipping this job.")
            continue
            
    inserted_ids = []
    status = "completed"
    
    try:
        if normalized_jobs:
            inserted_ids = await insert_jobs(normalized_jobs)
        else:
            logger.warning("No jobs were successfully normalized.")
    except Exception as e:
        logger.error(f"Failed to insert jobs to database: {e}")
        status = "failed"
        
    await update_job_search_status(search_id, status, len(inserted_ids))
    return inserted_ids
