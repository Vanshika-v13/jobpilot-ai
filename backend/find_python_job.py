import asyncio
import logging
from database.connection import connect_to_mongo, get_database, close_mongo_connection

logging.basicConfig(level=logging.INFO)

async def main():
    print("Connecting to MongoDB...")
    await connect_to_mongo()
    
    db = get_database()
    
    # Case-insensitive match for "Python" in the role field
    job = await db.jobs.find_one({"role": {"$regex": "Python", "$options": "i"}})
    
    if job:
        print("\n--- Python Job Found ---")
        print(f"job_id: {job['_id']}")
        print(f"company: {job.get('company')}")
        print(f"role: {job.get('role')}")
        print(f"required_skills: {job.get('required_skills')}")
        print("------------------------\n")
    else:
        print("No Python job found.")
        
    print("Closing MongoDB connection...")
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(main())
