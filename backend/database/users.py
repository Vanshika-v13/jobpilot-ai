import logging
from bson import ObjectId
from datetime import datetime
from typing import Optional, Dict, Any
from database.connection import get_database
from core.security import hash_password

logger = logging.getLogger(__name__)

async def create_user(email: str, password: str, full_name: str) -> str:
    """
    Hashes password using bcrypt, inserts user, returns user_id string.
    """
    db = get_database()
    
    # Normalize email to lowercase
    normalized_email = email.lower().strip()
    
    user_doc = {
        "email": normalized_email,
        "password_hash": hash_password(password),
        "full_name": full_name.strip(),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await db.users.insert_one(user_doc)
    logger.info(f"Created user with ID {result.inserted_id}")
    return str(result.inserted_id)

async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a user by unique email.
    """
    db = get_database()
    normalized_email = email.lower().strip()
    return await db.users.find_one({"email": normalized_email})

async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves user details by their ID.
    """
    db = get_database()
    try:
        query_id = ObjectId(user_id) if isinstance(user_id, str) else user_id
    except Exception as e:
        logger.error(f"Invalid user_id format: {user_id}. Error: {e}")
        return None
        
    return await db.users.find_one({"_id": query_id})
