from fastapi import APIRouter, HTTPException, status, Depends
from schemas.profile import UserProfileCreate, UserProfileResponse
from database.user_profiles import insert_profile, get_profile_by_id
from core.auth import get_current_user

router = APIRouter()

@router.post("", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(profile_in: UserProfileCreate, user_id: str = Depends(get_current_user)):
    """
    Create a new user profile. Automatically associated with the authenticated user.
    """
    try:
        profile_dict = profile_in.model_dump(exclude_unset=True)
    except AttributeError:
        profile_dict = profile_in.dict(exclude_unset=True)

    # Override user_id from the authenticated token
    profile_dict["user_id"] = user_id
        
    profile_id = await insert_profile(profile_dict)
    
    profile = await get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve profile after creation"
        )
    return profile

@router.get("/{id}", response_model=UserProfileResponse)
async def get_profile(id: str, user_id: str = Depends(get_current_user)):
    """
    Get a user profile by ID. Requires authentication.
    """
    profile = await get_profile_by_id(id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    return profile

