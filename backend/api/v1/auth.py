from fastapi import APIRouter, HTTPException, status
from schemas.auth import SignupRequest, LoginRequest, TokenResponse
from database.users import create_user, get_user_by_email
from core.security import verify_password
from core.auth import create_access_token

router = APIRouter()

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupRequest):
    # Check if user already exists
    existing_user = await get_user_by_email(payload.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create the user
    user_id = await create_user(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name
    )
    
    # Generate access token
    access_token = create_access_token(user_id)
    return TokenResponse(access_token=access_token)

@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    # Retrieve user
    user = await get_user_by_email(payload.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Generate access token
    access_token = create_access_token(str(user["_id"]))
    return TokenResponse(access_token=access_token)
