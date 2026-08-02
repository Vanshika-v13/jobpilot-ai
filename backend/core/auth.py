import jwt
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.config import settings

logger = logging.getLogger(__name__)

security = HTTPBearer()

def create_access_token(user_id: str) -> str:
    """
    Generate a JWT access token with a 7-day expiration.
    """
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(days=7),
        "iat": datetime.utcnow()
    }
    encoded_jwt = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt

def verify_access_token(token: str) -> Optional[str]:
    """
    Decode and verify a JWT access token.
    Returns the user_id (sub) if valid, or None if invalid/expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        user_id = payload.get("sub")
        if not user_id:
            return None
        return user_id
    except jwt.ExpiredSignatureError:
        logger.info("JWT verification failed: Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.info(f"JWT verification failed: {e}")
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    FastAPI dependency to extract and validate the user_id from the Authorization header.
    Raises HTTP 401 on missing, invalid, or expired tokens.
    """
    token = credentials.credentials
    user_id = verify_access_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id
