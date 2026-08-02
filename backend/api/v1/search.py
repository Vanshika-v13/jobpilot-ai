from fastapi import APIRouter, HTTPException, status, Depends
from schemas.search import SearchRequest, SearchResponse
from database.user_profiles import get_or_create_profile
from database.collections import create_job_search, update_job_search_status
from agents.graph import search_graph
from core.auth import get_current_user

router = APIRouter()

@router.post("", response_model=SearchResponse)
async def search_jobs(request: SearchRequest, user_id: str = Depends(get_current_user)):
    """
    Triggers the LangGraph search pipeline to scrape, extract, score, and rank jobs
    against a user profile. Profile is automatically resolved from the authenticated user.
    """
    # 1. Resolve user profile from authenticated user_id
    profile = await get_or_create_profile(user_id)
    
    # Format profile: convert ObjectId to string or keep it
    if "_id" in profile:
        profile["_id"] = str(profile["_id"])
    if "user_id" in profile and profile["user_id"]:
        profile["user_id"] = str(profile["user_id"])

    # 2. Create job_searches record in running state
    search_data = {
        "user_id": user_id,
        "query": request.role,
        "location": request.location,
        "source": request.source,
        "filters": {
            "experience": request.experience,
            "skills": request.skills
        },
        "status": "running"
    }
    
    search_id = await create_job_search(search_data)
    
    try:
        # 3. Assemble and invoke search graph
        initial_state = {
            "role": request.role,
            "location": request.location,
            "experience": request.experience,
            "skills": request.skills,
            "source": request.source,
            "plans": [],
            "raw_jobs": [],
            "extracted_jobs": [],
            "ranked_jobs": [],
            "profile": profile,
            "search_id": search_id
        }
        
        result_state = await search_graph.ainvoke(initial_state)
        ranked_jobs = result_state.get("ranked_jobs", [])
        
        # 4. Update job_searches status to completed
        await update_job_search_status(search_id, "completed", len(ranked_jobs))
        
        return SearchResponse(
            search_id=search_id,
            jobs=ranked_jobs,
            total=len(ranked_jobs)
        )
        
    except Exception as e:
        # Mark status as failed in case of exceptions
        await update_job_search_status(search_id, "failed", 0)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during search pipeline execution: {str(e)}"
        )

