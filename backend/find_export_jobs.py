"""
Temporary utility: find up to 3 jobs that have a non-null skill_match_score.
Prints job_id, company, and role for use in manual export testing.
"""
import asyncio
from database.connection import connect_to_mongo, get_database, close_mongo_connection


async def main():
    await connect_to_mongo()
    db = get_database()

    cursor = db.jobs.find(
        {"skill_match_score": {"$ne": None}}
    ).limit(3)

    jobs = await cursor.to_list(length=3)

    if not jobs:
        print("No jobs found with a non-null skill_match_score.")
    else:
        for i, job in enumerate(jobs):
            print(f"job_id  : {job['_id']}")
            print(f"company : {job.get('company', 'N/A')}")
            print(f"role    : {job.get('role', 'N/A')}")
            if i < len(jobs) - 1:
                print("-" * 40)

    await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(main())
