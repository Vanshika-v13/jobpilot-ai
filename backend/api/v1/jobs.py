from fastapi import APIRouter, HTTPException, status
from schemas.jobs import JobAnalysisRequest, JobAnalysisResponse, InterviewQuestionsRequest, InterviewQuestionsResponse
from agents.jd_analysis_agent import analyze_jd
from agents.interview_agent import generate_interview_questions

router = APIRouter()

@router.post("/{id}/analyze", response_model=JobAnalysisResponse)
async def analyze_job_description(id: str, request: JobAnalysisRequest):
    """
    Perform a deep-dive analysis of a job description against a user profile.
    """
    try:
        result = await analyze_jd(id, request.profile_id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.post("/{id}/interview-questions", response_model=InterviewQuestionsResponse)
async def get_interview_questions(id: str, request: InterviewQuestionsRequest):
    """
    Generate role-specific interview questions for a single job based on its description.
    """
    try:
        # Default to 10 if not provided or invalid
        count = request.question_count if request.question_count is not None and request.question_count > 0 else 10
        result = await generate_interview_questions(id, count)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

