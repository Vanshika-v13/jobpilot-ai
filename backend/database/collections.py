import logging
from bson import ObjectId
from datetime import datetime
from typing import List, Dict, Any, Union
from database.connection import get_database

logger = logging.getLogger(__name__)

async def create_job_search(search_data: Dict[str, Any]) -> str:
    """
    Insert a record into job_searches and return the search_id.
    """
    db = get_database()
    
    # Ensure default fields are present
    search_doc = {
        "user_id": search_data.get("user_id"),
        "query": search_data.get("query", ""),
        "location": search_data.get("location", ""),
        "source": search_data.get("source", "all"),
        "filters": search_data.get("filters", {}),
        "status": search_data.get("status", "pending"),
        "job_count": search_data.get("job_count", 0),
        "created_at": search_data.get("created_at") or datetime.utcnow()
    }
    
    # Convert user_id to ObjectId if it's a valid string representation
    if search_doc["user_id"] and isinstance(search_doc["user_id"], str):
        try:
            search_doc["user_id"] = ObjectId(search_doc["user_id"])
        except Exception:
            pass  # Retain as string if conversion fails

    result = await db.job_searches.insert_one(search_doc)
    logger.info(f"Created job search with ID {result.inserted_id}")
    return str(result.inserted_id)

async def update_job_search_status(search_id: Union[str, ObjectId], status: str, job_count: int = None) -> bool:
    """
    Handle search state transitions (pending -> running -> completed/failed).
    """
    db = get_database()
    
    update_doc = {"status": status}
    if job_count is not None:
        update_doc["job_count"] = job_count
        
    try:
        query_id = ObjectId(search_id) if isinstance(search_id, str) else search_id
    except Exception as e:
        logger.error(f"Invalid search_id format: {search_id}. Error: {e}")
        return False

    result = await db.job_searches.update_one(
        {"_id": query_id},
        {"$set": update_doc}
    )
    logger.info(f"Updated job search {search_id} to status {status}")
    return result.modified_count > 0

async def insert_jobs(jobs_list: List[Dict[str, Any]]) -> List[str]:
    """
    Insert normalized jobs into the jobs collection, deduplicating by apply_link.

    For each job:
    - If a document with the same apply_link already exists, update its
      scraped_at timestamp (no new document is created).
    - If no matching document exists, insert it as a new listing.

    Returns a list of stringified _id values for all affected documents
    (both newly inserted and updated).
    """
    if not jobs_list:
        return []

    db = get_database()
    affected_ids: List[str] = []
    inserted_count = 0
    updated_count = 0

    for job in jobs_list:
        job_doc = job.copy()

        # Ensure search_id is an ObjectId if possible
        if "search_id" in job_doc and job_doc["search_id"]:
            if isinstance(job_doc["search_id"], str):
                try:
                    job_doc["search_id"] = ObjectId(job_doc["search_id"])
                except Exception:
                    pass

        # Default fields required in schema
        if "scraped_at" not in job_doc or not job_doc["scraped_at"]:
            job_doc["scraped_at"] = datetime.utcnow()

        apply_link = job_doc.get("apply_link")

        # --- Deduplication check ---
        if apply_link:
            existing = await db.jobs.find_one(
                {"apply_link": apply_link},
                {"_id": 1}
            )
            if existing:
                # Refresh scraped_at so we know it was seen in this scrape
                await db.jobs.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {"scraped_at": job_doc["scraped_at"]}}
                )
                affected_ids.append(str(existing["_id"]))
                updated_count += 1
                logger.debug(
                    f"Skipped duplicate job (apply_link already exists): {apply_link}"
                )
                continue

        # No duplicate found — insert as a new document
        result = await db.jobs.insert_one(job_doc)
        affected_ids.append(str(result.inserted_id))
        inserted_count += 1

    logger.info(
        f"insert_jobs complete: {inserted_count} new, {updated_count} duplicates refreshed"
    )
    return affected_ids
