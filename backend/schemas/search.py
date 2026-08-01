from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class SearchRequest(BaseModel):
    role: str
    location: str
    experience: str
    skills: List[str]
    source: str = "all"
    profile_id: str

class RankedJob(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    search_id: Optional[str] = None
    company: str
    role: str
    location: str
    salary: str = "Not disclosed"
    apply_link: str = ""
    posted_date: str = "Not disclosed"
    source: str
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    raw_description: str = ""
    experience_required: str = "Not disclosed"
    job_type: str = "full-time"
    relevance_score: int
    explanation: str

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

class SearchResponse(BaseModel):
    search_id: str
    jobs: List[RankedJob]
    total: int

