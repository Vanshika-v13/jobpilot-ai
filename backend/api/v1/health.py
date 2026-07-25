from datetime import datetime
from fastapi import APIRouter
from database.connection import db

router = APIRouter()

@router.get("")
async def get_health():
    db_connected = False
    if db.client:
        try:
            # Ping the admin database to verify connectivity
            await db.client.admin.command('ping')
            db_connected = True
        except Exception:
            db_connected = False

    return {
        "status": "healthy",
        "db_connected": db_connected,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
