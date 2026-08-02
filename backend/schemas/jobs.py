from typing import List, Optional
from pydantic import BaseModel, Field

class JobAnalysisRequest(BaseModel):
    pass

class JobAnalysisResponse(BaseModel):
    skill_match_score: Optional[int] = None
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    learning_priority: List[str] = Field(default_factory=list)
    jd_summary: str = ""
    experience_required: str = ""
    responsibilities: List[str] = Field(default_factory=list)
    important_keywords: List[str] = Field(default_factory=list)
    profile_has_skills: bool = False


class InterviewQuestion(BaseModel):
    question: str
    topic: str
    difficulty: str

class InterviewQuestionsResponse(BaseModel):
    interview_questions: List[InterviewQuestion] = Field(default_factory=list)

class InterviewQuestionsRequest(BaseModel):
    question_count: Optional[int] = Field(default=10, description="Number of questions to generate")

