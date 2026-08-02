from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File
from schemas.profile import ResumeUploadResponse, UserProfileResponse
from database.user_profiles import get_or_create_profile, update_profile_by_user_id, clear_resume_fields_by_user_id
from core.auth import get_current_user
from services.resume_service import validate_pdf, extract_text_from_pdf, parse_resume_with_llm

router = APIRouter()

@router.post("/upload-resume", response_model=ResumeUploadResponse)
async def upload_resume(file: UploadFile = File(...), user_id: str = Depends(get_current_user)):
    """
    Upload a PDF resume, extract details using LLM, and update user profile.
    """
    file_bytes = await file.read()
    
    try:
        validate_pdf(file_bytes)
    except ValueError as e:
        status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE if "large" in str(e).lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(e))
        
    try:
        resume_text = extract_text_from_pdf(file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        
    try:
        extracted_data = await parse_resume_with_llm(resume_text)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
        
    await get_or_create_profile(user_id)
    
    update_fields = {
        "resume_text": resume_text,
        "skills": extracted_data.get("skills", []),
        "experience_years": extracted_data.get("experience_years", 0.0),
        "education": extracted_data.get("education", ""),
        "preferred_roles": extracted_data.get("preferred_roles", [])
    }
    
    updated_profile = await update_profile_by_user_id(user_id, update_fields)
    if not updated_profile:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile with resume data"
        )
        
    updated_profile['_id'] = str(updated_profile['_id'])
    updated_profile['user_id'] = str(updated_profile['user_id'])
    return updated_profile


@router.delete("/resume", response_model=UserProfileResponse)
async def delete_resume(user_id: str = Depends(get_current_user)):
    """
    Clear all resume-derived fields on the authenticated user's profile.
    """
    updated_profile = await clear_resume_fields_by_user_id(user_id)
    if not updated_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    updated_profile['_id'] = str(updated_profile['_id'])
    updated_profile['user_id'] = str(updated_profile['user_id'])
    return updated_profile

