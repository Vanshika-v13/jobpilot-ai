import logging
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from bson import ObjectId

from agents.llm_provider import get_llm
from database.collections import insert_jobs, update_job_search_status
from prompts.extraction_prompt import EXTRACTION_PROMPT

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# HTML sanitisation – strip AI-chat / widget artifacts from descriptions
# ---------------------------------------------------------------------------

# Markers that indicate AI-chat widget HTML (e.g. ChatGPT conversation pasted
# by a job poster).  If *any* of these appear in the raw HTML, the description
# is sent through the sanitiser.
_CHAT_MARKERS = (
    "data-message-author-role",
    "data-message-model-slug",
    "data-turn-id",
    "data-testid=\"conversation-turn",
    "convSearchResultHighlightRoot",
    "text-token-text-primary",
)

# CSS class substrings that betray chatbot wrapper elements.
_CHAT_CLASS_FRAGMENTS = (
    "text-token-text-primary",
    "thread-content",
    "agent-turn",
    "text-message",
    "markdown prose",
    "convSearchResultHighlightRoot",
    "threadScrollVars",
    "writing-block",
)


def sanitize_description(html: str) -> str:
    """Remove AI-chat widget artefacts from a job description.

    Some Unstop job posters paste content straight from ChatGPT, which
    embeds deeply-nested ``<div>``/``<section>`` wrappers with chat-specific
    data-attributes and CSS classes.  This function:

    1. Detects whether the HTML contains chat-widget markers.
    2. Strips **all** ``data-*`` attributes from every tag.
    3. Strips ``tabindex`` and ``dir`` attributes.
    4. Removes ``class`` attributes whose value contains chat-specific
       fragments (keeps ``class`` on tags where it looks benign).
    5. Unwraps non-semantic ``<div>`` and ``<section>`` containers,
       keeping only their inner content.
    6. Collapses excess blank lines.

    If no chat markers are detected the HTML is returned unchanged.
    """
    if not html:
        return html

    # Fast-path: nothing to clean
    if not any(marker in html for marker in _CHAT_MARKERS):
        return html

    logger.info("Sanitising AI-chat artefacts from job description")

    # 1. Strip data-* attributes
    html = re.sub(
        r'\s+data-[a-z0-9_-]+=(?:"[^"]*"|\x27[^\x27]*\x27|[^\s>]+)',
        "", html, flags=re.IGNORECASE,
    )

    # 2. Strip tabindex / dir attributes
    html = re.sub(
        r'\s+(?:tabindex|dir)=(?:"[^"]*"|\x27[^\x27]*\x27|[^\s>]+)',
        "", html, flags=re.IGNORECASE,
    )

    # 3. Remove class attributes that contain chat-specific fragments
    def _strip_chat_class(m: re.Match) -> str:
        value = m.group(1) or m.group(2) or m.group(3)
        if any(frag in value for frag in _CHAT_CLASS_FRAGMENTS):
            return ""  # drop entire class attribute
        return m.group(0)  # keep innocent class

    html = re.sub(
        r'\s+class=(?:"([^"]*)"|\x27([^\x27]*)\x27|(\S+))',
        _strip_chat_class, html, flags=re.IGNORECASE,
    )

    # 4. Unwrap <div …> and <section …> (open + close tags), keep content
    html = re.sub(r"</?(?:div|section)(?:\s[^>]*)?>", "", html, flags=re.IGNORECASE)

    # 5. Collapse blank lines
    html = re.sub(r"\n\s*\n+", "\n", html).strip()

    return html

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
        "raw_description": sanitize_description(raw_job.get("description", "") or ""),
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
    # Safety net: sanitise in case scraped HTML carried AI-chat artifacts
    job_dict["raw_description"] = sanitize_description(job_dict.get("raw_description", ""))
    
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
