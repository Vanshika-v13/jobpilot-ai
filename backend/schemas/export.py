from typing import List
from pydantic import BaseModel, Field

class ExportRequest(BaseModel):
    job_ids: List[str] = Field(..., description="List of MongoDB job IDs to export")
    format: str = Field(..., description="Export format: 'excel' or 'pdf'")

class ExportResponse(BaseModel):
    file_url: str = Field(..., description="URL to download the generated file")
    format: str = Field(..., description="The format exported ('excel' or 'pdf')")
    job_count: int = Field(..., description="Number of successfully exported jobs")
