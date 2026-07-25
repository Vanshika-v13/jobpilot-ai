import logging
from motor.motor_asyncio import AsyncIOMotorClient
from core.config import settings

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None

db = Database()

async def connect_to_mongo():
    logger.info("Connecting to MongoDB...")
    try:
        db.client = AsyncIOMotorClient(settings.mongodb_uri)
        # Ping the admin database to verify connectivity
        await db.client.admin.command('ping')
        logger.info("Connected to MongoDB successfully!")
    except Exception as e:
        logger.error(f"Could not connect to MongoDB: {e}")
        # Note: We do not set db.client to None if it failed to ping,
        # but let's keep it initialized so health check can ping it and report db_connected: False.
        # However, let's check if the client itself failed to create.
        # Actually, let's keep client instance so that it can retry or check connection.

async def close_mongo_connection():
    logger.info("Closing MongoDB connection...")
    if db.client:
        db.client.close()
        db.client = None
        logger.info("MongoDB connection closed.")

def get_database():
    if db.client is None:
        raise ConnectionError("Database client is not initialized.")
    db_name = settings.mongodb_uri.split("/")[-1] if "/" in settings.mongodb_uri else "jobpilot"
    if "?" in db_name:
        db_name = db_name.split("?")[0]
    if not db_name:
        db_name = "jobpilot"
    return db.client[db_name]
