from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class UserProfileCreate(BaseModel):
    user_id: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    experience_years: float = 0.0
    education: Optional[str] = None
    preferred_roles: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    preferred_location: Optional[str] = None
    resume_text: Optional[str] = None

class UserProfileResponse(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    experience_years: float = 0.0
    education: Optional[str] = None
    preferred_roles: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    preferred_location: Optional[str] = None
    resume_text: Optional[str] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )


class ResumeExtractedData(BaseModel):
    skills: List[str] = Field(default_factory=list)
    experience_years: float = 0.0
    education: str = ""
    preferred_roles: List[str] = Field(default_factory=list)


class ResumeUploadResponse(UserProfileResponse):
    pass


