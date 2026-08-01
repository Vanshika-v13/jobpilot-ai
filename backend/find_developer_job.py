import asyncio
import logging
from bson import ObjectId
from database.connection import (
    connect_to_mongo,
    get_database,
    close_mongo_connection,
)

logging.basicConfig(level=logging.INFO)

async def main():
    print("Connecting to MongoDB...")
    await connect_to_mongo()

    db = get_database()

    job = await db.jobs.find_one(
        {
            "role": {"$regex": "Developer", "$options": "i"},
            "_id": {"$ne": ObjectId("6a65e0a0e320daa4ae812db5")},
        }
    )

    if job:
        print("\n--- Developer Job Found ---")
        print("job_id:", job["_id"])
        print("company:", job.get("company"))
        print("role:", job.get("role"))
        print("required_skills:", job.get("required_skills"))
        print("---------------------------")
    else:
        print("No other developer job found.")

    print("\nClosing MongoDB connection...")
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(main())
