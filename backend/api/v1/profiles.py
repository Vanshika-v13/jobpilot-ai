from fastapi import APIRouter, HTTPException, status
from schemas.profile import UserProfileCreate, UserProfileResponse
from database.user_profiles import insert_profile, get_profile_by_id

router = APIRouter()

@router.post("", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(profile_in: UserProfileCreate):
    """
    Create a new user profile.
    """
    try:
        profile_dict = profile_in.model_dump(exclude_unset=True)
    except AttributeError:
        profile_dict = profile_in.dict(exclude_unset=True)
        
    profile_id = await insert_profile(profile_dict)
    
    profile = await get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve profile after creation"
        )
    return profile

@router.get("/{id}", response_model=UserProfileResponse)
async def get_profile(id: str):
    """
    Get a user profile by ID.
    """
    profile = await get_profile_by_id(id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    return profile
