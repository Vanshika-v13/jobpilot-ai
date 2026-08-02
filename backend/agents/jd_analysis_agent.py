import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from bson import ObjectId

from agents.llm_provider import get_llm
from agents.extraction_agent import sanitize_description
from agents.ranking_agent import normalize_skill
from prompts.jd_analysis_prompt import JD_ANALYSIS_PROMPT
from database.connection import get_database
from database.user_profiles import get_profile_by_id

logger = logging.getLogger(__name__)

# Truncation threshold for sanitized job description to avoid context overflow / latency issues
TRUNCATION_THRESHOLD = 4000

class JDAnalysisModel(BaseModel):
    required_skills: List[str] = Field(default_factory=list, description="List of required skills")
    preferred_skills: List[str] = Field(default_factory=list, description="List of preferred skills")
    experience_required: str = Field(default="", description="Experience required (e.g., 0-2 years)")
    responsibilities: List[str] = Field(default_factory=list, description="Job responsibilities")
    important_keywords: List[str] = Field(default_factory=list, description="Important keywords")
    jd_summary: str = Field(default="", description="Short summary of the job description")


def calculate_skill_gap(
    required_skills: List[str],
    preferred_skills: List[str],
    user_skills: List[str]
) -> Dict[str, Any]:
    """
    Compare job skills against user skills using alias-aware normalized comparisons.
    Returns matched_skills, missing_skills, learning_priority, and skill_match_score.
    """
    norm_required = {normalize_skill(s) for s in required_skills if s}
    norm_preferred = {normalize_skill(s) for s in preferred_skills if s}
    norm_user = {normalize_skill(s) for s in user_skills if s}

    matched_req = [s for s in required_skills if normalize_skill(s) in norm_user]
    missing_req = [s for s in required_skills if normalize_skill(s) not in norm_user]

    matched_pref = [s for s in preferred_skills if normalize_skill(s) in norm_user]
    missing_pref = [s for s in preferred_skills if normalize_skill(s) not in norm_user]

    # Deduplicate preserving order
    matched_skills = list(dict.fromkeys(matched_req + matched_pref))
    missing_skills = list(dict.fromkeys(missing_req + missing_pref))
    learning_priority = list(dict.fromkeys(missing_req + missing_pref))

    total_req = len(norm_required)
    total_pref = len(norm_preferred)

    if total_req == 0 and total_pref == 0:
        score = 50.0
    elif total_req == 0:
        score = (len(norm_preferred & norm_user) / total_pref) * 100
    elif total_pref == 0:
        score = (len(norm_required & norm_user) / total_req) * 100
    else:
        score = (
            0.7 * (len(norm_required & norm_user) / total_req) +
            0.3 * (len(norm_preferred & norm_user) / total_pref)
        ) * 100

    return {
        "skill_match_score": int(round(score)),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "learning_priority": learning_priority,
    }


async def analyze_jd(job_id: str, profile_id: str) -> Dict[str, Any]:
    """
    Analyze a job description against a user profile.
    Orchestrates cached retrieval, HTML sanitization, text truncation,
    LLM structured extraction, fallback logic on LLM failures, and caching.
    """
    db = get_database()
    
    # Fetch job
    try:
        job_oid = ObjectId(job_id) if isinstance(job_id, str) else job_id
        job = await db.jobs.find_one({"_id": job_oid})
    except Exception as e:
        logger.error(f"Invalid job ID: {job_id}. Error: {e}")
        job = None

    if not job:
        raise ValueError(f"Job not found: {job_id}")

    # Fetch user profile
    try:
        profile = await get_profile_by_id(profile_id)
    except Exception as e:
        logger.error(f"Error fetching profile {profile_id}: {e}")
        profile = None

    if not profile:
        raise ValueError(f"Profile not found: {profile_id}")

    user_skills = profile.get("skills", [])
    profile_has_skills = len(user_skills) > 0

    # Check read-through cache (only if skill_match_score is present/not null)
    if job.get("skill_match_score") is not None:
        logger.info(f"Returning cached analysis for job {job_id}")
        return {
            "skill_match_score": job.get("skill_match_score"),
            "matched_skills": job.get("matched_skills", []),
            "missing_skills": job.get("missing_skills", []),
            "learning_priority": job.get("learning_priority", []),
            "jd_summary": job.get("jd_summary", ""),
            "experience_required": job.get("experience_required", ""),
            "responsibilities": job.get("responsibilities", []),
            "important_keywords": job.get("important_keywords", []),
            "profile_has_skills": profile_has_skills,
        }

    # Prepare job description
    raw_desc = job.get("description") or job.get("raw_description") or ""
    sanitized = sanitize_description(raw_desc)
    
    # Truncate if description is longer than the threshold
    if len(sanitized) > TRUNCATION_THRESHOLD:
        logger.info(f"Job description of length {len(sanitized)} exceeds {TRUNCATION_THRESHOLD} characters. Truncating.")
        truncated_desc = sanitized[:TRUNCATION_THRESHOLD]
    else:
        truncated_desc = sanitized

    llm_failed = False
    analysis_data = None

    # LLM Structured Extraction with Json Parsing & Retries
    parser = PydanticOutputParser(pydantic_object=JDAnalysisModel)
    
    try:
        llm = get_llm()
        
        logger.info(f"[DIAGNOSTIC] Truncated description length: {len(truncated_desc)}. First 300 chars: {truncated_desc[:300]!r}")
        prompt = JD_ANALYSIS_PROMPT.format(
            job_description=truncated_desc,
            format_instructions=parser.get_format_instructions()
        )
        
        response = await llm.ainvoke(prompt)
        analysis_data = parser.invoke(response)
        logger.info(f"[DIAGNOSTIC] Raw analysis_data returned: {repr(analysis_data)}")
        
        # Check if all core fields are empty (indicates a total parsing failure with defaults)
        if (not analysis_data.required_skills and 
            not analysis_data.preferred_skills and 
            not analysis_data.responsibilities and 
            not analysis_data.jd_summary):
            raise ValueError("All core fields returned empty. Likely a parsing failure.")
            
    except Exception as e:
        logger.warning(f"Initial LLM analysis failed for job {job_id}: {e}. Retrying once...")
        try:
            # Retry with a stricter reminder
            retry_prompt = prompt + "\n\nCRITICAL: Respond with valid JSON ONLY. Do not wrap in markdown code blocks."
            response = await llm.ainvoke(retry_prompt)
            analysis_data = parser.invoke(response)
            logger.info(f"[DIAGNOSTIC] Retry Raw analysis_data returned: {repr(analysis_data)}")
            
            if (not analysis_data.required_skills and 
                not analysis_data.preferred_skills and 
                not analysis_data.responsibilities and 
                not analysis_data.jd_summary):
                raise ValueError("All core fields returned empty on retry.")
        except Exception as retry_e:
            logger.error(f"Retry LLM analysis failed for job {job_id}: {retry_e}", exc_info=True)
            llm_failed = True
 
    # Handle LLM failure or empty response
    if llm_failed or not analysis_data:
        # Graceful fallback: return partial result using existing job fields if present
        fallback_required = job.get("required_skills") or []
        fallback_preferred = job.get("preferred_skills") or []
        
        gap_results = calculate_skill_gap(fallback_required, fallback_preferred, user_skills)
        
        result = {
            "skill_match_score": None,  # leave as null so future requests retry the full analysis
            "matched_skills": gap_results["matched_skills"],
            "missing_skills": gap_results["missing_skills"],
            "learning_priority": gap_results["learning_priority"],
            "jd_summary": "Detailed analysis unavailable — showing basic skill comparison.",
            "experience_required": job.get("experience_required", ""),
            "responsibilities": job.get("responsibilities") or [],
            "important_keywords": job.get("important_keywords") or [],
            "profile_has_skills": profile_has_skills,
        }
        return result
 
    # Success path: calculate skill gap and update MongoDB cache
    gap_results = calculate_skill_gap(
        analysis_data.required_skills,
        analysis_data.preferred_skills,
        user_skills
    )
 
    result = {
        "skill_match_score": gap_results["skill_match_score"],
        "matched_skills": gap_results["matched_skills"],
        "missing_skills": gap_results["missing_skills"],
        "learning_priority": gap_results["learning_priority"],
        "jd_summary": analysis_data.jd_summary,
        "experience_required": analysis_data.experience_required,
        "responsibilities": analysis_data.responsibilities,
        "important_keywords": analysis_data.important_keywords,
        "profile_has_skills": profile_has_skills,
    }
 
    # Cache successful results (skill_match_score is not null)
    try:
        await db.jobs.update_one(
            {"_id": job_oid},
            {"$set": {
                "skill_match_score": result["skill_match_score"],
                "matched_skills": result["matched_skills"],
                "missing_skills": result["missing_skills"],
                "learning_priority": result["learning_priority"],
                "jd_summary": result["jd_summary"],
                "experience_required": result["experience_required"],
                "responsibilities": result["responsibilities"],
                "important_keywords": result["important_keywords"],
            }}
        )
    except Exception as e:
        logger.error(f"Failed to cache analysis for job {job_id}: {e}")
 
    return result

