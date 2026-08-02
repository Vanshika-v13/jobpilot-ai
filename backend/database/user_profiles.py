import logging
from bson import ObjectId
from datetime import datetime
from typing import Optional, Dict, Any
from database.connection import get_database

logger = logging.getLogger(__name__)

async def insert_profile(profile: Dict[str, Any]) -> str:
    """
    Insert a user profile into user_profiles collection and return its ID.
    """
    db = get_database()
    profile_doc = profile.copy()
    
    # Ensure updated_at is set
    profile_doc["updated_at"] = datetime.utcnow()
    
    # Convert user_id to ObjectId if it's a valid string representation
    if "user_id" in profile_doc and profile_doc["user_id"] and isinstance(profile_doc["user_id"], str):
        try:
            profile_doc["user_id"] = ObjectId(profile_doc["user_id"])
        except Exception:
            pass

    # Ensure preferred_location is synchronized with preferred_locations
    if "preferred_location" in profile_doc and profile_doc["preferred_location"]:
        if "preferred_locations" not in profile_doc or not profile_doc["preferred_locations"]:
            profile_doc["preferred_locations"] = [profile_doc["preferred_location"]]
    elif "preferred_locations" in profile_doc and profile_doc["preferred_locations"]:
        profile_doc["preferred_location"] = profile_doc["preferred_locations"][0]

    result = await db.user_profiles.insert_one(profile_doc)
    logger.info(f"Created user profile with ID {result.inserted_id}")
    return str(result.inserted_id)

async def get_profile_by_id(profile_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a user profile by its ID.
    """
    db = get_database()
    try:
        query_id = ObjectId(profile_id) if isinstance(profile_id, str) else profile_id
    except Exception as e:
        logger.error(f"Invalid profile_id format: {profile_id}. Error: {e}")
        return None
        
    doc = await db.user_profiles.find_one({"_id": query_id})
    return doc

async def get_profile_by_user_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches a profile matching a specific user_id.
    """
    db = get_database()
    try:
        query_id = ObjectId(user_id) if isinstance(user_id, str) else user_id
    except Exception as e:
        logger.error(f"Invalid user_id format: {user_id}. Error: {e}")
        return None
    return await db.user_profiles.find_one({"user_id": query_id})

async def get_or_create_profile(user_id: str) -> Dict[str, Any]:
    """
    Retrieves a profile by user_id, or inserts a new empty/default profile if none exists.
    """
    profile = await get_profile_by_user_id(user_id)
    if profile is None:
        db = get_database()
        try:
            uid = ObjectId(user_id) if isinstance(user_id, str) else user_id
        except Exception:
            uid = user_id
            
        default_profile = {
            "user_id": uid,
            "skills": [],
            "experience_years": 0.0,
            "education": None,
            "preferred_roles": [],
            "preferred_locations": [],
            "preferred_location": None,
            "resume_text": None,
            "updated_at": datetime.utcnow()
        }
        await db.user_profiles.insert_one(default_profile)
        profile = default_profile
    return profile
