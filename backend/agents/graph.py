import logging
import operator
from typing import Annotated, Any, Dict, List, TypedDict
from langgraph.graph import StateGraph, END
from agents.planner_agent import SearchPlan

logger = logging.getLogger(__name__)

class SearchState(TypedDict):
    role: str
    location: str
    experience: str
    skills: List[str]
    source: str
    plans: List[SearchPlan]
    raw_jobs: Annotated[List[Dict[str, Any]], operator.add]
    extracted_jobs: List[Dict[str, Any]]
    ranked_jobs: List[Dict[str, Any]]
    profile: Dict[str, Any]
    search_id: str

async def planner_node(state: SearchState) -> Dict[str, Any]:
    logger.info("=== START: planner_node ===")
    from agents.planner_agent import create_search_plans
    plans = create_search_plans(
        role=state.get("role", ""),
        location=state.get("location", ""),
        experience=state.get("experience", ""),
        skills=state.get("skills", []),
        source=state.get("source", "all")
    )
    logger.info(f"=== END: planner_node returned {len(plans)} plans ===")
    return {"plans": plans}

async def scrape_internshala_node(state: SearchState) -> Dict[str, Any]:
    logger.info("=== START: scrape_internshala_node ===")
    from tools.internshala import scrape_internshala
    plan = next((p for p in state.get("plans", []) if p["portal"] == "internshala"), None)
    if not plan:
        logger.info("=== END: scrape_internshala_node (No plan found) ===")
        return {"raw_jobs": []}
    
    try:
        results = await scrape_internshala(role=plan["role"], location=plan["location"])
        logger.info(f"=== END: scrape_internshala_node returned {len(results)} jobs ===")
        return {"raw_jobs": results}
    except Exception as e:
        logger.error(f"=== ERROR: scrape_internshala_node failed with exception: {e} ===", exc_info=True)
        return {"raw_jobs": []}

async def scrape_unstop_node(state: SearchState) -> Dict[str, Any]:
    logger.info("=== START: scrape_unstop_node ===")
    from tools.unstop import scrape_unstop
    plan = next((p for p in state.get("plans", []) if p["portal"] == "unstop"), None)
    if not plan:
        logger.info("=== END: scrape_unstop_node (No plan found) ===")
        return {"raw_jobs": []}
    
    try:
        results = await scrape_unstop(role=plan["role"], location=plan["location"])
        logger.info(f"=== END: scrape_unstop_node returned {len(results)} jobs ===")
        return {"raw_jobs": results}
    except Exception as e:
        logger.error(f"=== ERROR: scrape_unstop_node failed with exception: {e} ===", exc_info=True)
        return {"raw_jobs": []}

async def extract_node(state: SearchState) -> Dict[str, Any]:
    logger.info("=== START: extract_node ===")
    from agents.extraction_agent import process_scraped_results
    from database.connection import get_database
    from bson import ObjectId
    
    raw_jobs = state.get("raw_jobs", [])
    logger.info(f"extract_node processing {len(raw_jobs)} raw jobs")
    search_id = state.get("search_id")
    
    await process_scraped_results(search_id, raw_jobs)
    
    # Query database to retrieve the stored jobs under search_id
    db = get_database()
    cursor = db.jobs.find({"search_id": ObjectId(search_id)})
    extracted = await cursor.to_list(length=1000)
    
    # Standardize IDs to strings
    for job in extracted:
        job["_id"] = str(job["_id"])
        if "search_id" in job:
            job["search_id"] = str(job["search_id"])
            
    logger.info(f"=== END: extract_node returned {len(extracted)} extracted jobs ===")
    return {"extracted_jobs": extracted}

async def rank_node(state: SearchState) -> Dict[str, Any]:
    logger.info("=== START: rank_node ===")
    from agents.ranking_agent import rank_jobs
    extracted = state.get("extracted_jobs", [])
    profile = state.get("profile", {})
    ranked = rank_jobs(extracted, profile)
    logger.info(f"=== END: rank_node returned {len(ranked)} ranked jobs ===")
    return {"ranked_jobs": ranked}

def route_scrapers(state: SearchState) -> str:
    plans = state.get("plans", [])
    has_internshala = any(p["portal"] == "internshala" for p in plans)
    if has_internshala:
        return "scrape_internshala"
    
    has_unstop = any(p["portal"] == "unstop" for p in plans)
    if has_unstop:
        return "scrape_unstop"
    
    return "extract"

def route_after_internshala(state: SearchState) -> str:
    plans = state.get("plans", [])
    has_unstop = any(p["portal"] == "unstop" for p in plans)
    if has_unstop:
        return "scrape_unstop"
    return "extract"

workflow = StateGraph(SearchState)

workflow.add_node("planner", planner_node)
workflow.add_node("scrape_internshala", scrape_internshala_node)
workflow.add_node("scrape_unstop", scrape_unstop_node)
workflow.add_node("extract", extract_node)
workflow.add_node("rank", rank_node)

workflow.set_entry_point("planner")

workflow.add_conditional_edges(
    "planner",
    route_scrapers,
    {
        "scrape_internshala": "scrape_internshala",
        "scrape_unstop": "scrape_unstop",
        "extract": "extract"
    }
)

workflow.add_conditional_edges(
    "scrape_internshala",
    route_after_internshala,
    {
        "scrape_unstop": "scrape_unstop",
        "extract": "extract"
    }
)

workflow.add_edge("scrape_unstop", "extract")
workflow.add_edge("extract", "rank")
workflow.add_edge("rank", END)

search_graph = workflow.compile()
