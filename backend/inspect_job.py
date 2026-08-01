import asyncio
from database.connection import connect_to_mongo, close_mongo_connection, get_database
from bson import ObjectId

async def main():
    await connect_to_mongo()
    db = get_database()
    job = await db.jobs.find_one({"_id": ObjectId("6a65e0a0e320daa4ae812db5")})
    
    desc = job.get("description", "")
    raw_desc = job.get("raw_description", "")
    
    print(f"=== description field ===")
    print(f"Type: {type(desc)}, Length: {len(desc) if desc else 0}")
    print(f"First 500 chars: {repr(desc[:500]) if desc else 'EMPTY/NONE'}")
    print()
    print(f"=== raw_description field ===")
    print(f"Type: {type(raw_desc)}, Length: {len(raw_desc) if raw_desc else 0}")
    print(f"First 500 chars: {repr(raw_desc[:500]) if raw_desc else 'EMPTY/NONE'}")
    print()
    print(f"=== All top-level keys ===")
    print([k for k in job.keys()])
    
    await close_mongo_connection()

asyncio.run(main())
