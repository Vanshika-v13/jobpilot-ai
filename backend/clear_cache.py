import asyncio
from database.connection import connect_to_mongo, close_mongo_connection, get_database
from bson.objectid import ObjectId  # type: ignore # pylint: disable=import-error


async def main():
    await connect_to_mongo()
    db = get_database()
    result = await db.jobs.update_one(
        {"_id": ObjectId("6a65eed49099e7179a3a6a4c")},
        {"$unset": {
            "skill_match_score": "",
            "matched_skills": "",
            "missing_skills": "",
            "learning_priority": "",
            "jd_summary": "",
            "experience_required": "",
            "responsibilities": "",
            "important_keywords": "",
        }}
    )
    print(f"Matched: {result.matched_count}, Modified: {result.modified_count}")
    await close_mongo_connection()

asyncio.run(main())
