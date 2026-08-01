from typing import List, Optional
from pydantic import BaseModel, Field

class JobAnalysisRequest(BaseModel):
    profile_id: str

class JobAnalysisResponse(BaseModel):
    skill_match_score: Optional[int] = None
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    learning_priority: List[str] = Field(default_factory=list)
    jd_summary: str = ""
    experience_required: str = ""
    responsibilities: List[str] = Field(default_factory=list)
    important_keywords: List[str] = Field(default_factory=list)
