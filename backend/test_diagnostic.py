"""Direct call to analyze_jd with full logging capture."""
import asyncio
import logging
import sys

# Route ALL logging to stdout so we capture [DIAGNOSTIC] lines
logging.basicConfig(
    level=logging.DEBUG,
    format="%(name)s %(levelname)s %(message)s",
    stream=sys.stdout,
    force=True,
)

from database.connection import connect_to_mongo, close_mongo_connection, get_database
from agents.jd_analysis_agent import analyze_jd

async def main():
    await connect_to_mongo()
    db = get_database()
    try:
        # Find a Python job
        job = await db.jobs.find_one({"role": {"$regex": "Python", "$options": "i"}})
        if not job:
            job = await db.jobs.find_one({"description": {"$regex": "Python", "$options": "i"}})
            
        if not job:
            print("No Python job found.")
            return
            
        job_id = job["_id"]
        print(f"Found Python Job ID: {job_id}")
        
        # Clear cache for this job
        await db.jobs.update_one(
            {"_id": job_id},
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
        print("Cleared cache for job.")
        
        # Run analysis
        result = await analyze_jd(str(job_id), "6a65eb09d3d35654c5b604e1")
        print(f"\n=== FINAL RESULT ===\n{result}")
    except Exception as e:
        print(f"\n=== EXCEPTION ===\n{e}", flush=True)
        import traceback; traceback.print_exc()
    finally:
        await close_mongo_connection()

asyncio.run(main())
